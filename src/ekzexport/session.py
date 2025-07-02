from functools import cached_property

import requests
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
    def __init__(self, username: str, password: str, login_immediately=False):
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': 'ekzexport'})
        self._username = username
        self._password = password
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
        r = self._session.get('https://my.ekz.ch/verbrauch/', headers=HTML_HEADERS)
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
        self._logged_in = True

    def get_csrf_token(self):
        self._ensure_logged_in()
        r = self._session.get('https://my.ekz.ch/api/portal-services/csrf/v1/token', headers=JSON_HEADERS)
        r.raise_for_status()
        return r.json()['token']

    @cached_property
    def installation_selection_data(self) -> InstallationSelectionData:
        self._ensure_logged_in()
        r = self._session.get('https://my.ekz.ch/api/portal-services/consumption-view/v1/installation-selection-data'
                              '?installationVariant=CONSUMPTION', headers=JSON_HEADERS)
        r.raise_for_status()
        return r.json()

    def get_installation_data(self, installation_id: str) -> InstallationData:
        self._ensure_logged_in()
        r = self._session.get('https://my.ekz.ch/api/portal-services/consumption-view/v1/installation-data'
                              '?installationId=' + installation_id, headers=JSON_HEADERS)
        r.raise_for_status()
        return r.json()

    def get_consumption_data(self, installation_id: str, data_type: str,
                             date_from: str, date_to: str) -> ConsumptionData:
        self._ensure_logged_in()
        r = self._session.get(f'https://my.ekz.ch/api/portal-services/consumption-view/v1/consumption-data'
                              f'?installationId={installation_id}&from={date_from}&to={date_to}&type={data_type}',
                              headers=JSON_HEADERS)
        r.raise_for_status()
        return r.json()
