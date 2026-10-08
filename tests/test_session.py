import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import pytest


from ekzexport.session import Session


@dataclass
class CapturedRequest:
    method: str
    path: str
    query_params: Dict[str, List[str]]
    headers: Dict[str, str]
    body: bytes

    @property
    def json(self) -> Any:
        return json.loads(self.body.decode('utf-8')) if self.body else None


@dataclass
class ResponseRule:
    predicate: Callable[[str, str], bool]
    status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b''


class LoopbackServer:
    def __init__(self, host: str = '127.0.0.1', port: int = 0):
        self.host = host
        self.port = port
        self.requests: List[CapturedRequest] = []
        self._rules: List[ResponseRule] = []
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def add_rule(
        self,
        method: str,
        path: str,
        status: int = 200,
        json_data: Any = None,
        body: bytes = b'',
        headers: Optional[Dict[str, str]] = None,
        times: Optional[int] = None,
    ):
        """Answer `method path` with this response; only the first `times` requests if given.

        Rules are tried in the order they were added, so a limited rule followed by an
        unlimited one for the same path describes a response that changes over time."""
        resp_headers = headers.copy() if headers else {}
        if json_data is not None:
            body = json.dumps(json_data).encode('utf-8')
            resp_headers.setdefault('Content-Type', 'application/json')

        remaining = [times]

        def predicate(m: str, p: str) -> bool:
            if m != method or p != path or remaining[0] == 0:
                return False
            if remaining[0] is not None:
                remaining[0] -= 1
            return True

        self._rules.append(
            ResponseRule(
                predicate=predicate,
                status=status,
                headers=resp_headers,
                body=body,
            )
        )

    def start(self):
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def handle_all(self, method: str):
                parsed = urlparse(self.path)
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length) if length > 0 else b''

                captured = CapturedRequest(
                    method=method,
                    path=parsed.path,
                    query_params=parse_qs(parsed.query),
                    headers=dict(self.headers),
                    body=body,
                )
                parent.requests.append(captured)

                # Match the first matching rule
                matched = next(
                    (r for r in parent._rules if r.predicate(method, parsed.path)),
                    None,
                )

                if matched:
                    self.send_response(matched.status)
                    for k, v in matched.headers.items():
                        self.send_header(k, v)
                    self.send_header('Content-Length', str(len(matched.body)))
                    self.end_headers()
                    self.wfile.write(matched.body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_GET(self):
                self.handle_all('GET')

            def do_POST(self):
                self.handle_all('POST')

            def log_message(self, *args):
                # Suppress standard HTTP server logging to stderr in test output
                pass

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()


@pytest.fixture
def mock_server():
    server = LoopbackServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def session(mock_server):
    return Session(
        username="testuser",
        password="secretpassword",
        base_url=f"http://127.0.0.1:{mock_server.port}",
    )


def test_send_leg_invites(session, mock_server):
    mock_server.add_rule(
        method='GET',
        path='/api/portal-services/csrf/v1/token',
        status=200,
        json_data={'token': 'csrf-xyz-123'},
    )
    mock_server.add_rule(
        method='POST',
        path='/api/portal-services/leg-manager-dashboard/v1/invitation/submit',
        status=200,
        json_data={'status': 'success'},
    )

    session.send_leg_invites(
        leg_id='leg-101',
        emails=['  user1@example.ch ', 'user2@example.ch  '],
        subject='LEG Invitation',
        body='Hello!\nJoin our energy community',
    )

    assert len(mock_server.requests) == 2
    csrf_req, post_req = mock_server.requests

    # Verify CSRF token request
    assert csrf_req.method == 'GET'
    assert csrf_req.path == '/api/portal-services/csrf/v1/token'
    assert csrf_req.headers['Accept'] == 'application/json, text/plain, */*'
    assert csrf_req.headers['User-Agent'] == 'ekzexport'

    # Verify POST invite payload and headers
    assert post_req.method == 'POST'
    assert post_req.path == '/api/portal-services/leg-manager-dashboard/v1/invitation/submit'
    assert post_req.headers['Accept'] == 'application/json, text/plain, */*'
    assert post_req.headers['Content-Type'] == 'application/json'
    assert post_req.headers['X-CSRF-TOKEN'] == 'csrf-xyz-123'
    assert post_req.headers['User-Agent'] == 'ekzexport'

    expected_payload = {
        'legId': 'leg-101',
        'emailAddresses': 'user1@example.ch; user2@example.ch',
        'subject': 'LEG Invitation',
        'body': 'Hello!\nJoin our energy community',
    }
    assert post_req.json == expected_payload


LEG_HEADERS = '/api/portal-services/leg-manager-dashboard/v1/leg-headers'


def add_login_flow(mock_server):
    """The login as myEKZ does it, reduced to username and password: /nutzerdaten/ shows
    the login form until the credentials were posted, and is itself afterwards."""
    base = f'http://127.0.0.1:{mock_server.port}'
    mock_server.add_rule(
        method='GET', path='/nutzerdaten/', times=1,
        body=f'<form id="kc-form-login" action="{base}/auth/login"></form>'.encode('utf-8'),
        headers={'Content-Type': 'text/html'},
    )
    mock_server.add_rule(method='GET', path='/nutzerdaten/', body=b'<html></html>',
                         headers={'Content-Type': 'text/html'})
    mock_server.add_rule(method='POST', path='/auth/login', status=302,
                         headers={'Location': f'{base}/nutzerdaten/'})


def test_api_call_without_session_logs_in_and_retries(session, mock_server):
    # What myEKZ does for an API call without a valid session, be it the first call of a
    # new one or one that expired: a redirect to the login form, not an error status.
    mock_server.add_rule(method='GET', path=LEG_HEADERS, status=302, times=1,
                         headers={'Location': '/newlogin'})
    mock_server.add_rule(method='GET', path=LEG_HEADERS, json_data={'legHeaders': [{'legId': 'leg-101'}]})
    add_login_flow(mock_server)

    assert session.get_legs() == [{'legId': 'leg-101'}]

    assert [(r.method, r.path) for r in mock_server.requests] == [
        ('GET', LEG_HEADERS),
        ('GET', '/nutzerdaten/'),
        ('POST', '/auth/login'),
        ('GET', '/nutzerdaten/'),
        ('GET', LEG_HEADERS),
    ]
    assert parse_qs(mock_server.requests[2].body.decode('utf-8')) == {
        'username': ['testuser'], 'password': ['secretpassword'],
    }


def test_api_call_with_valid_session_does_not_log_in(session, mock_server):
    mock_server.add_rule(method='GET', path=LEG_HEADERS, json_data={'legHeaders': []})

    assert session.get_legs() == []

    assert [(r.method, r.path) for r in mock_server.requests] == [('GET', LEG_HEADERS)]


def test_login_redirect_after_logging_in_is_an_error(session, mock_server):
    mock_server.add_rule(method='GET', path=LEG_HEADERS, status=302, headers={'Location': '/newlogin'})
    add_login_flow(mock_server)

    with pytest.raises(Exception, match='still asks for a login'):
        session.get_legs()

    # Logged in once and retried once: no loop.
    assert [r.path for r in mock_server.requests].count(LEG_HEADERS) == 2
    assert [r.path for r in mock_server.requests].count('/auth/login') == 1


def test_other_redirect_is_not_followed(session, mock_server):
    mock_server.add_rule(method='GET', path=LEG_HEADERS, status=302, headers={'Location': '/wartung'})
    mock_server.add_rule(method='GET', path='/wartung', body=b'<html>Systemunterbruch</html>')

    with pytest.raises(Exception, match='Unexpected redirect'):
        session.get_legs()

    assert [r.path for r in mock_server.requests] == [LEG_HEADERS]


def test_html_instead_of_json_names_what_came_back(session, mock_server):
    mock_server.add_rule(method='GET', path=LEG_HEADERS, body=b'<html>Anmeldung</html>',
                         headers={'Content-Type': 'text/html'})

    with pytest.raises(Exception, match=r"Expected JSON .* got 'text/html'"):
        session.get_legs()
