"""LifeMap accounts: persistent users, hashed passwords and revocable sessions.

Local development uses an ignored SQLite file. Serverless deployments require
a persistent Postgres DATABASE_URL; they never fall back to temporary storage.
No account credentials are passed to the AI or written to application logs.
"""
from contextlib import contextmanager
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlparse
import uuid

PASSWORD_ITERATIONS = 600_000
SESSION_SECONDS = 8 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
MAX_LOGIN_FAILURES = 5


class AccountError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class Store:
    def __init__(self, connection, postgres=False):
        self.connection = connection
        self.postgres = postgres

    def execute(self, sql, parameters=()):
        return self.connection.execute(sql.replace('?', '%s') if self.postgres else sql, parameters)


@contextmanager
def account_store():
    url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
    if url:
        if urlparse(url).scheme not in ('postgres', 'postgresql'):
            raise AccountError('The account database needs a Postgres connection.', 503)
        try:
            import psycopg
            connection = psycopg.connect(url, sslmode='require', connect_timeout=10)
        except Exception:
            raise AccountError('Accounts are temporarily unavailable. Please try again.', 503) from None
        postgres = True
    else:
        if os.environ.get('VERCEL') or os.environ.get('LIFEMAP_AUTH_REQUIRE_POSTGRES') == '1':
            raise AccountError('Account registration is awaiting the hosted database connection.', 503)
        path = Path(os.environ.get('LIFEMAP_AUTH_DB_PATH') or Path(__file__).resolve().parent / '.lifemap-data' / 'accounts.sqlite3')
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = sqlite3.connect(path, timeout=10)
        os.chmod(path, 0o600)
        connection.execute('PRAGMA foreign_keys = ON')
        # Serialize local writes, including the persisted failed-login counter.
        connection.execute('BEGIN IMMEDIATE')
        postgres = False
    store = Store(connection, postgres)
    try:
        if postgres:
            # Serialize first-time schema creation across serverless instances.
            store.execute('SELECT pg_advisory_xact_lock(1961442011)')
        store.execute('''CREATE TABLE IF NOT EXISTS lifemap_users (
            id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL, password_hash TEXT NOT NULL, created_at BIGINT NOT NULL)''')
        store.execute('''CREATE TABLE IF NOT EXISTS lifemap_sessions (
            token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES lifemap_users(id) ON DELETE CASCADE,
            expires_at BIGINT NOT NULL, created_at BIGINT NOT NULL)''')
        store.execute('''CREATE TABLE IF NOT EXISTS lifemap_login_attempts (
            email_hash TEXT PRIMARY KEY, failures INTEGER NOT NULL,
            window_started BIGINT NOT NULL, locked_until BIGINT NOT NULL)''')
        store.execute('CREATE INDEX IF NOT EXISTS lifemap_session_user ON lifemap_sessions(user_id)')
        store.execute('CREATE INDEX IF NOT EXISTS lifemap_session_expiry ON lifemap_sessions(expires_at)')
        if postgres:
            # Release the schema lock before account/password operations.
            connection.commit()
        yield store
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _email(value):
    if not isinstance(value, str):
        raise AccountError('Please enter a valid email address.')
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r'[^@\s\x00-\x1f]+@[^@\s\x00-\x1f]+\.[^@\s\x00-\x1f]+', value):
        raise AccountError('Please enter a valid email address.')
    return value


def _password(value, signup=False):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise AccountError('Please enter a password of 12 to 128 characters.' if signup else 'Please enter your password.')
    if signup and (len(value) < 12 or not value.strip()):
        raise AccountError('Please use a password of at least 12 characters.')
    return value


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), PASSWORD_ITERATIONS).hex()
    return f'pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}'


def verify_password(password, stored):
    # The dummy hash costs the same work for unknown users.
    stored = stored or f'pbkdf2_sha256${PASSWORD_ITERATIONS}$' + '0' * 32 + '$' + '0' * 64
    try:
        algorithm, iterations, salt, expected = stored.split('$')
        if algorithm != 'pbkdf2_sha256' or int(iterations) != PASSWORD_ITERATIONS:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(iterations)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _user(row):
    return {'id': row[0], 'email': row[1], 'user_metadata': {'full_name': row[2]}}


def _session(store, user, now):
    token = secrets.token_urlsafe(32)
    store.execute('DELETE FROM lifemap_sessions WHERE expires_at <= ?', (now,))
    store.execute('INSERT INTO lifemap_sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)',
                  (hashlib.sha256(token.encode()).hexdigest(), user['id'], now + SESSION_SECONDS, now))
    return {'user': user, 'access_token': token, 'expires_in': SESSION_SECONDS}


def _token_hash(authorization):
    if not isinstance(authorization, str) or not authorization.startswith('Bearer '):
        raise AccountError('Please log in to continue.', 401)
    token = authorization[7:]
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise AccountError('Please log in to continue.', 401)
    return hashlib.sha256(token.encode()).hexdigest()


def account_request(payload, authorization=None):
    """Return only public user/session information. Passwords never leave here."""
    if not isinstance(payload, dict):
        raise AccountError('Invalid account request.')
    action = payload.get('action')
    now = int(time.time())
    if action == 'register':
        email = _email(payload.get('email'))
        password = _password(payload.get('password'), signup=True)
        name = payload.get('fullName')
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120 or any(ord(c) < 32 for c in name):
            raise AccountError('Please enter your full name, using at most 120 characters.')
        password_hash = hash_password(password)
        with account_store() as store:
            user_id = str(uuid.uuid4())
            # The unique constraint also handles simultaneous registrations.
            inserted = store.execute('''INSERT INTO lifemap_users (id, email, full_name, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT (email) DO NOTHING''',
                (user_id, email, name.strip(), password_hash, now))
            if inserted.rowcount != 1:
                raise AccountError('This email cannot be registered. Try logging in instead.', 409)
            user = _user((user_id, email, name.strip()))
            return _session(store, user, now)
    if action == 'login':
        email = _email(payload.get('email'))
        password = _password(payload.get('password'))
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        failure = 'Email or password is incorrect, or sign-in is temporarily locked. Please try again later.'
        # Commit failed-attempt counters before returning a login error.
        result = None
        with account_store() as store:
            store.execute('''INSERT INTO lifemap_login_attempts (email_hash, failures, window_started, locked_until)
                VALUES (?, 0, ?, 0) ON CONFLICT (email_hash) DO NOTHING''', (email_hash, now))
            lock = ' FOR UPDATE' if store.postgres else ''
            attempts = store.execute('SELECT failures, window_started, locked_until FROM lifemap_login_attempts WHERE email_hash = ?' + lock, (email_hash,)).fetchone()
            if attempts[2] <= now:
                failures = attempts[0] if attempts[1] > now - LOGIN_WINDOW_SECONDS else 0
                row = store.execute('SELECT id, email, full_name, password_hash FROM lifemap_users WHERE email = ?', (email,)).fetchone()
                if verify_password(password, row[3] if row else None) and row:
                    store.execute('DELETE FROM lifemap_login_attempts WHERE email_hash = ?', (email_hash,))
                    result = _session(store, _user(row), now)
                else:
                    failures += 1
                    store.execute('UPDATE lifemap_login_attempts SET failures = ?, window_started = ?, locked_until = ? WHERE email_hash = ?',
                                  (failures, attempts[1] if failures > 1 else now,
                                   now + LOGIN_WINDOW_SECONDS if failures >= MAX_LOGIN_FAILURES else 0, email_hash))
        if result is None:
            raise AccountError(failure, 401)
        return result
    if action in ('session', 'logout'):
        token_hash = _token_hash(authorization)
        with account_store() as store:
            if action == 'logout':
                store.execute('DELETE FROM lifemap_sessions WHERE token_hash = ?', (token_hash,))
                return {'ok': True}
            row = store.execute('''SELECT u.id, u.email, u.full_name FROM lifemap_sessions s
                JOIN lifemap_users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?''',
                (token_hash, now)).fetchone()
            if row is None:
                raise AccountError('Your session has expired. Please log in again.', 401)
            return {'user': _user(row)}
    raise AccountError('Unknown account action.')
