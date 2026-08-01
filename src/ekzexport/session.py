from functools import cached_property

import requests
import pyotp
from bs4 import BeautifulSoup

from .apitypes import *

HTML_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml'
}
JSON_HEADERS = {
    'Accept': 'application/json, text/plain, */*'
}


class Session:
    """Represents a session with the EKZ API."""
    def __init__(self, username: str, password: str, token='', login_immediately=False):
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': 'ekzexport'})
        self._username = username
        self._password = password
        self._token = token.strip().replace(' ', '')
        self._login_immediately = login_immediately
        self._logged_in = False

    def __enter__(self):
        if self._login_immediately:
            self._ensure_logged_in()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._logged_in:
            r = self._session.post('https://my.ekz.ch/logout', headers=HTML_HEADERS,
                                   data={'_csrf': self.get_csrf_token()})
            r.raise_for_status()

    def _ensure_logged_in(self):
        if self._logged_in:
            return
        # We need to use a page that works for everyone and is reasonably fast to load.
        # /startseite appears to be really slow for some accounts, so that is not a good choice.
        # /verbrauch used to be what we used but for pure LEG managers without a metering point that returns 403
        # so /nutzerdaten it is, even if we don't actually care about the user data.
        r = self._session.get('https://my.ekz.ch/nutzerdaten/', headers=HTML_HEADERS)
        r.raise_for_status()

        # Find the login form and get the action URL, so we can submit credentials.
        soup = BeautifulSoup(r.text, 'html.parser')
        loginform = soup.select('form[id=kc-form-login]')
        if not loginform:
            if 'Es tut uns leid' in r.text or 'Systemunterbruch' in r.text:
                raise Exception('myEKZ appears to be offline for maintenance')
            else:
                raise Exception('Login form not found on page')
        authurl = loginform[0]['action']

        r = self._session.post(authurl, data={'username': self._username, 'password': self._password})
        r.raise_for_status()

        # There are a few options what can happen at this point:
        # - If 2FA is enabled, we will have been redirected to a page which will ask for the second factor
        # - If 2FA is disabled, every once in a while myEKZ will ask for our mobile number on:
        #   https://login.ekz.ch/auth/realms/myEKZ/login-actions/required-action?
        #     execution=ensu_mobile_number_config&client_id=cos-myekz-webapp&tab_id=<alnum>
        #   To skip, mobile_number=&cancel=Sp%C3%A4ter+einrichten is POSTed to
        #   https://login.ekz.ch/auth/realms/myEKZ/login-actions/required-action?
        #     session_code=<alnum>&execution=ensu_mobile_number_config&client_id=cos-myekz-webapp&tab_id=<alnum>

        if 'ensu_mobile_number_config' in r.url:
            # Just get the form action and submit the cancellation to skip...
            soup = BeautifulSoup(r.text, 'html.parser')
            mobileform = soup.select('form')
            if not mobileform:
                raise Exception('Didn\'t find mobile phone number entry on: ' + r.url)
            mobileurl = mobileform[0]['action']
            if 'ensu_mobile_number_config' not in mobileurl:
                raise Exception('Unexpected mobile phone number entry URL: ' + mobileurl)
            r = self._session.post(mobileurl, data={'mobile_number': '', 'cancel': 'Später einrichten'})
            r.raise_for_status()

        elif 'auth/realms/myEKZ/login-actions/authenticate' in r.url:
            # If we did not get redirected away now, we're being asked for
            # a second factor, either SMS code or OTP.
            soup = BeautifulSoup(r.text, 'html.parser')
            smsform = soup.select('form[id=kc-sms-code-login-form]')
            otpform = soup.select('form[id=kc-otp-login-form]')
            if smsform:
                authurl = smsform[0]['action']
                code = input('Enter 2FA code (wait for SMS): ')
                r = self._session.post(authurl, data={'code': code})
                r.raise_for_status()
            elif otpform:
                if not self._token:
                    raise Exception('OTP is enabled but no token was provided')
                authurl = otpform[0]['action']
                r = self._session.post(authurl, data={'otp': pyotp.TOTP(self._token).now()})
                r.raise_for_status()
            elif 'Es tut uns leid' in r.text or 'Systemunterbruch' in r.text:
                raise Exception('myEKZ appears to be offline for maintenance')
            else:
                raise Exception('myEKZ auth expects something we can\'t handle.')

        # Finally, if we're successfully logged in, we should be back at the original URL we requested
        if r.url != 'https://my.ekz.ch/nutzerdaten/':
            raise Exception('Unable to login. Ended up at ' + r.url + ' instead of https://my.ekz.ch/nutzerdaten/')
        
        self._logged_in = True

    def _get_portal_services_json(self, suffix: str):
        self._ensure_logged_in()
        r = self._session.get(f'https://my.ekz.ch/api/portal-services/{suffix}', headers=JSON_HEADERS)
        r.raise_for_status()
        return r.json()

    def get_csrf_token(self):
        return self._get_portal_services_json('csrf/v1/token')['token']

    @cached_property
    def installation_selection_data(self) -> InstallationSelectionData:
        return self._get_portal_services_json(
            'consumption-view/v1/installation-selection-data'
            '?installationVariant=CONSUMPTION')

    def get_installation_data(self, installation_id: str) -> InstallationData:
        return self._get_portal_services_json(
            f'consumption-view/v1/installation-data'
            f'?installationId={installation_id}')

    def get_consumption_data(self, installation_id: str, data_type: str,
                             date_from: str, date_to: str) -> ConsumptionData:
        return self._get_portal_services_json(
            f'consumption-view/v1/consumption-data'
            f'?installationId={installation_id}&from={date_from}&to={date_to}&type={data_type}'
        )

    def get_legs(self) -> List[LegHeader]:
        return self._get_portal_services_json('leg-manager-dashboard/v1/leg-headers')['legHeaders']

    def get_leg_detail(self, leg_id: str) -> LegDetails:
        return self._get_portal_services_json(f'leg-manager-dashboard/v1/leg-details/{leg_id}')['legDetails']
