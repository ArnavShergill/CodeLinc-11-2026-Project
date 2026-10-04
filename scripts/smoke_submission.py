"""Judge-style HTTP smoke test. Standard library only; synthetic data only."""
import json
from http.client import RemoteDisconnected
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def wait_for_health(probe, attempts=30):
    """Docker may publish its port before Python finishes importing modules."""
    for attempt in range(attempts):
        try:
            assert probe()['status'] == 'ok'
            return
        except (URLError, OSError, RemoteDisconnected):
            if attempt == attempts - 1:
                raise
            time.sleep(1)


def verify(base, account_file=None):
    base = base.rstrip('/')

    def request(path, payload=None, token=None):
        headers = {'Origin': base}
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = Request(base + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        with urlopen(req, timeout=20) as response:
            return response.read().decode(), response.headers

    wait_for_health(lambda: json.loads(request('/api/health')[0]))
    html, _ = request('/')
    assert 'LifeMap AI' in html
    for asset in re.findall(r'(?:src|href)="([^"#]+)"', html):
        if not asset.startswith(('data:', 'http')):
            request('/' + asset)
    for asset in ('src/services/authService.js', 'src/services/planService.js', 'src/types/contracts.js',
                  'src/data/mockProfile.js', 'src/assets/protection-illustration.svg'):
        request('/' + asset)
    config, _ = request('/config.js')
    assert 'window.location.origin' in config and 'authApiUrl' in config
    assert 'lifemap-ai-live.vercel.app' not in config
    profile = {'annualIncome': 75000, 'spouseAnnualIncome': 45000, 'numberOfDependents': 3,
               'childrenAges': [7, 11], 'mortgageBalance': 180000, 'otherDebt': 25000, 'finalExpenses': 15000,
               'desiredAnnualIncome': 50000, 'incomeReplacementYears': 10, 'collegeFundingNeed': 80000,
               'existingLifeInsurance': 100000, 'availableAssets': 50000, 'inflationRate': .02, 'investmentReturnRate': .05}
    body, _ = request('/api/calculate', {'profile': profile})
    original = json.loads(body)['result']
    assert original['additionalCoverageNeeded'] == 590375.55
    for scenario, changes, expected in (
        ('child', {'collegeFundingNeed': 100000, 'numberOfDependents': 4, 'desiredAnnualIncome': 55000}, 654413.10),
        ('home', {'mortgageBalance': 250000}, 660375.55),
        ('income', {'annualIncome': 100000, 'desiredAnnualIncome': 60000}, 678450.66),
        ('debt', {'otherDebt': 0}, 565375.55),
        ('married', {'spouseAnnualIncome': 60000, 'desiredAnnualIncome': 55000}, 634413.10)):
        body, _ = request('/api/scenario', {'profile': profile, 'scenario': scenario, 'changes': changes})
        projection = json.loads(body)
        assert projection['result']['additionalCoverageNeeded'] == expected
        assert projection['baseResult'] == original
        assert len(projection['timeline']) == 5
    body, _ = request('/api/chat', {'message': 'hello', 'context': {}})
    assert json.loads(body)['reply']
    body, _ = request('/api/intake', {'message': '2.5', 'field': 'inflationRate', 'context': {'profile': {}}})
    assert json.loads(body)['updates']['inflationRate'] == .025
    fixture_path = Path(account_file) if account_file else None
    if fixture_path and fixture_path.exists():
        fixture = json.loads(fixture_path.read_text())
        credentials, original_user = fixture['credentials'], fixture['user']
    else:
        email = 'smoke-' + secrets.token_hex(6) + '@example.test'
        credentials = {'email': email, 'password': 'Synthetic-long-password-123'}
        body, headers = request('/api/auth', {'action': 'register', 'fullName': 'Test Visitor', **credentials})
        registered = json.loads(body)
        original_user = registered['user']
        assert headers['Cache-Control'] == 'no-store'
        if fixture_path:
            fixture_path.write_text(json.dumps({'credentials': credentials, 'user': original_user}))
            fixture_path.chmod(0o600)
        body, _ = request('/api/auth', {'action': 'logout'}, registered['access_token'])
        assert json.loads(body)['ok']
    body, _ = request('/api/auth', {'action': 'login', **credentials})
    logged_in = json.loads(body)
    assert logged_in['user'] == original_user
    request('/api/auth', {'action': 'session'}, logged_in['access_token'])
    request('/api/auth', {'action': 'logout'}, logged_in['access_token'])
    for path in ('/.env.local', '/.lifemap-data/accounts.sqlite3', '/src/../.env.local'):
        try:
            request(path)
            raise AssertionError('Private file unexpectedly accessible')
        except HTTPError as error:
            assert error.code == 404
            error.close()
    print('PASS: landing/assets, same-origin config, API health, calculator, all five scenarios, chat greeting, percentage intake, real signup/login/logout, private-file protection.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('base', nargs='?', default='http://127.0.0.1:5173')
    parser.add_argument('--account-file', help='Private synthetic fixture for checking restart persistence')
    arguments = parser.parse_args()
    verify(arguments.base, arguments.account_file)
