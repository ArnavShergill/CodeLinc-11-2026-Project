"""Real account persistence, password verification and session regressions."""
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import auth_accounts as accounts
from api_server import LifeMapAPIHandler, _requests


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / 'accounts.sqlite3'
        self.environment = patch.dict(os.environ, {'DATABASE_URL': '', 'POSTGRES_URL': '', 'VERCEL': '',
            'LIFEMAP_AUTH_REQUIRE_POSTGRES': '', 'LIFEMAP_AUTH_DB_PATH': str(self.path)})
        self.environment.start()
        _requests.clear()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()
        _requests.clear()

    def register(self, **changes):
        return accounts.account_request({'action': 'register', 'fullName': 'Jordan Taylor',
            'email': 'jordan@example.test', 'password': 'Synthetic-long-password-123', **changes})

    def login(self, **changes):
        return accounts.account_request({'action': 'login', 'email': 'jordan@example.test',
            'password': 'Synthetic-long-password-123', **changes})

    def test_signup_session_and_separate_login_use_persisted_account(self):
        registration = self.register(email=' JORDAN@EXAMPLE.TEST ')
        login = self.login()
        self.assertEqual(registration['user'], login['user'])
        self.assertNotEqual(registration['access_token'], login['access_token'])
        self.assertEqual(accounts.account_request({'action': 'session'}, 'Bearer ' + login['access_token']), {'user': login['user']})
        self.assertEqual(login['user']['email'], 'jordan@example.test')
        self.assertEqual(login['user']['user_metadata']['full_name'], 'Jordan Taylor')
        self.assertTrue(self.path.exists())

    def test_passwords_and_tokens_are_hashed_not_stored_raw_or_exposed(self):
        result = self.register()
        with accounts.account_store() as store:
            password_hash = store.execute('SELECT password_hash FROM lifemap_users').fetchone()[0]
            token_hash = store.execute('SELECT token_hash FROM lifemap_sessions').fetchone()[0]
        self.assertNotIn('Synthetic-long-password-123', self.path.read_bytes().decode(errors='ignore'))
        self.assertNotIn(result['access_token'], self.path.read_bytes().decode(errors='ignore'))
        self.assertTrue(password_hash.startswith('pbkdf2_sha256$600000$'))
        self.assertEqual(len(token_hash), 64)
        self.assertTrue(accounts.verify_password('Synthetic-long-password-123', password_hash))
        self.assertNotIn('password', json.dumps(result))

    def test_same_password_has_distinct_salts(self):
        first = self.register()
        self.register(email='second@example.test')
        with accounts.account_store() as store:
            hashes = [row[0] for row in store.execute('SELECT password_hash FROM lifemap_users').fetchall()]
        self.assertNotEqual(hashes[0], hashes[1])

    def test_duplicate_email_is_not_overwritten(self):
        first = self.register()
        with self.assertRaises(accounts.AccountError) as error:
            self.register(email='JORDAN@example.test', password='Another-long-password-456')
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.login()['user']['id'], first['user']['id'])

    def test_invalid_signup_data_does_not_create_account(self):
        cases = [{'fullName': ''}, {'fullName': 'a'*121}, {'email': 'invalid'}, {'password': 'short'},
                 {'password': ' '*12}, {'password': 'a'*129}, {'email': True}, {'fullName': 'Name\x00'}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(accounts.AccountError):
                self.register(**changes)
        self.assertFalse(self.path.exists())

    def test_wrong_password_and_unknown_account_have_same_error(self):
        self.register()
        messages = []
        for changes in ({'password': 'wrong-password'}, {'email': 'unknown@example.test'}):
            with self.assertRaises(accounts.AccountError) as error:
                self.login(**changes)
            self.assertEqual(error.exception.status, 401)
            messages.append(str(error.exception))
        self.assertEqual(messages[0], messages[1])

    def test_lockout_is_persistent_and_expires(self):
        self.register()
        for _ in range(5):
            with self.assertRaises(accounts.AccountError):
                self.login(password='wrong-password')
        with self.assertRaises(accounts.AccountError):
            self.login()
        with patch('auth_accounts.time.time', return_value=time.time() + accounts.LOGIN_WINDOW_SECONDS + 1):
            self.assertIn('access_token', self.login())

    def test_logout_revokes_only_current_session(self):
        first = self.register(); second = self.login()
        authorization = 'Bearer ' + first['access_token']
        self.assertEqual(accounts.account_request({'action': 'logout'}, authorization), {'ok': True})
        with self.assertRaises(accounts.AccountError):
            accounts.account_request({'action': 'session'}, authorization)
        self.assertEqual(accounts.account_request({'action': 'session'}, 'Bearer ' + second['access_token'])['user'], second['user'])

    def test_expired_invalid_and_missing_tokens_are_rejected(self):
        result = self.register()
        for authorization in (None, 'Bearer forged', 'Bearer ' + 'a'*43):
            with self.assertRaises(accounts.AccountError):
                accounts.account_request({'action': 'session'}, authorization)
        with patch('auth_accounts.time.time', return_value=time.time() + accounts.SESSION_SECONDS + 1):
            with self.assertRaises(accounts.AccountError):
                accounts.account_request({'action': 'session'}, 'Bearer ' + result['access_token'])

    def test_serverless_without_postgres_fails_instead_of_losing_accounts(self):
        with patch.dict(os.environ, {'VERCEL': '1'}), self.assertRaises(accounts.AccountError) as error:
            self.register()
        self.assertEqual(error.exception.status, 503)
        self.assertFalse(self.path.exists())

    def test_sql_parameters_do_not_execute_user_input(self):
        result = self.register(fullName="Jordan'); DROP TABLE lifemap_users;--")
        self.assertEqual(self.login()['user'], result['user'])

    def test_account_endpoint_and_origin_validation(self):
        def request(payload, authorization=None, origin=None):
            raw = json.dumps(payload).encode(); handler = object.__new__(LifeMapAPIHandler)
            handler.path = '/api/auth'; handler.headers = {'Content-Length': str(len(raw))}
            if authorization: handler.headers['Authorization'] = authorization
            if origin: handler.headers['Origin'] = origin
            handler.client_address = ('auth-test', 1); handler.rfile = io.BytesIO(raw)
            output = []; handler._send_json = lambda status, data: output.append((status, data))
            handler.do_POST(); return output[0]
        status, result = request({'action': 'register', 'fullName': 'Jordan Taylor',
            'email': 'jordan@example.test', 'password': 'Synthetic-long-password-123'})
        self.assertEqual(status, 200)
        self.assertEqual(request({'action': 'session'}, 'Bearer ' + result['access_token'])[0], 200)
        self.assertEqual(request({'action': 'session'}, origin='https://untrusted.example')[0], 403)
        self.assertEqual(request({'action': 'session'})[0], 401)


@unittest.skipUnless(os.environ.get('AUTH_TEST_POSTGRES_URL'), 'Optional isolated Postgres fixture not configured')
class PostgresAccountTests(AccountTests):
    """Run identical account regressions against a disposable real Postgres DB."""
    def setUp(self):
        super().setUp()
        url = os.environ['AUTH_TEST_POSTGRES_URL']
        from urllib.parse import urlparse
        if not urlparse(url).path.startswith('/lifemap_auth_test'):
            raise RuntimeError('The disposable test database must start with lifemap_auth_test.')
        os.environ['DATABASE_URL'] = url
        with accounts.account_store() as store:
            store.execute('DELETE FROM lifemap_sessions')
            store.execute('DELETE FROM lifemap_users')
            store.execute('DELETE FROM lifemap_login_attempts')

    def test_invalid_signup_data_does_not_create_account(self):
        for changes in ({'fullName': ''}, {'email': 'invalid'}, {'password': 'short'}):
            with self.assertRaises(accounts.AccountError):
                self.register(**changes)
        with accounts.account_store() as store:
            self.assertEqual(store.execute('SELECT COUNT(*) FROM lifemap_users').fetchone()[0], 0)

    def test_serverless_without_postgres_fails_instead_of_losing_accounts(self):
        with patch.dict(os.environ, {'DATABASE_URL': '', 'POSTGRES_URL': '', 'VERCEL': '1'}), self.assertRaises(accounts.AccountError) as error:
            self.register()
        self.assertEqual(error.exception.status, 503)

    def test_passwords_and_tokens_are_hashed_not_stored_raw_or_exposed(self):
        result = self.register()
        with accounts.account_store() as store:
            password_hash = store.execute('SELECT password_hash FROM lifemap_users').fetchone()[0]
            token_hash = store.execute('SELECT token_hash FROM lifemap_sessions').fetchone()[0]
        self.assertNotIn('Synthetic-long-password-123', password_hash)
        self.assertNotEqual(token_hash, result['access_token'])
        self.assertTrue(accounts.verify_password('Synthetic-long-password-123', password_hash))
        self.assertNotIn('password', json.dumps(result))

    def test_signup_session_and_separate_login_use_persisted_account(self):
        registration = self.register(email=' JORDAN@EXAMPLE.TEST ')
        login = self.login()
        self.assertEqual(registration['user'], login['user'])
        self.assertEqual(accounts.account_request({'action': 'session'}, 'Bearer ' + login['access_token']), {'user': login['user']})
