# LifeMap real accounts

LifeMap now has its own account backend. Supabase is not required. The existing full-name, email and password form calls `/api/auth`; successful registration signs the user in immediately. Login restores the same stored identity. These are real database records, not a browser-only mock.

## Local use

Open http://localhost:5180/ and select Get Started. Enter your full name, email and a password of at least 12 characters. The running preview routes account requests to the Python backend.

Local accounts persist in `.lifemap-data/accounts.sqlite3`, outside the static frontend. Restarting the server does not delete them. The directory and database are gitignored and excluded from builds. To use another local file, set `LIFEMAP_AUTH_DB_PATH` on the backend; this is a server setting, not browser configuration.

## Hosted use on Vercel

The hosted application requires a persistent Postgres database. It deliberately refuses account creation without a database connection on Vercel. Local SQLite storage cannot persist reliably in serverless functions.

1. In the Vercel project, open Storage and connect a Postgres database through the Marketplace, such as Neon. Follow the provider's connection flow.
2. Ensure the project has a server-side `DATABASE_URL` (or `POSTGRES_URL`) containing its Postgres connection string. Prefer the provider's pooled connection string for serverless hosting. Never put this value in `config.js`, commit it, or send it to the AI.
3. Deploy the account changes to the Vercel project's repository. Tables and indexes are created automatically on first use; the database role must be able to create them. Connections require TLS.
4. Test registration, logout, login and a reload against the actual hosted deployment. Until this step passes, production accounts are not certified.

The Vercel build sets `authApiUrl` to the deployment's own `/api/auth`. The shared GitHub Pages frontend can point at the Vercel account endpoint, with its existing allowed-origin configuration. An explicitly configured Supabase deployment remains supported for compatibility when `authApiUrl` is omitted.

## Security and scope

- Passwords use randomly salted PBKDF2-HMAC-SHA256 with 600,000 iterations. Only hashes are stored; passwords are not recoverable from account records.
- Sessions use randomly generated opaque tokens, with only their SHA256 hashes stored in the database. Sessions expire after eight hours, and logout revokes the current token on the server.
- The browser keeps the token in sessionStorage, validates it with the backend on reload, and clears it on logout or rejection. Browser storage does not contain passwords. Tokens are bearer credentials, so preventing script injection remains important; this is not an HttpOnly-cookie session.
- Failed login counts persist in the database. Five failures for an email temporarily lock login for fifteen minutes. Unknown email and wrong password have the same error. Request bursts and concurrent hashing are also limited per backend instance.
- Account responses are not cacheable. Only the account endpoint receives passwords; account details are not included in AI context or financial profiles. Account data is not logged unnecessarily.
- Email ownership is not verified, and self-service password reset/email delivery is not implemented. Signup proves possession of the chosen password, not ownership of the email address. Add verification and recovery before a broad public launch.
- Accounts establish identity and personalized greetings. Financial plans remain in the tab and reset on reload; this change does not add saved financial plans or authorization to the public education/calculation endpoints.

## Verification

Automated Python tests exercise local persistence and the same account behavior against an optional disposable TLS Postgres database. Browser tests use a real local HTTP server and isolated account database, covering signup, session validation, login, wrong password, duplicate email, logout revocation, forged tokens and absence of stored passwords.

Latest verification: 77 Python tests passed with the isolated TLS Postgres fixture enabled (including 12 account tests for each database backend); 9 JavaScript tests passed; all three browser suites passed; build, secret scan and whitespace checks passed. Without `AUTH_TEST_POSTGRES_URL`, the 12 optional Postgres tests are skipped and the other 65 run.

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/lifemap-vercel-qa/bin/python -m unittest discover -s tests
AUDIT_PYTHON=/private/tmp/lifemap-vercel-qa/bin/python PLAYWRIGHT_MODULE_PATH=/private/tmp/lifemap-pages-qa/node_modules/playwright node lifemap-ai-main/tests/auth-browser.cjs
```

References: [Vercel storage](https://vercel.com/docs/storage), [SQLite on Vercel](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel), [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
