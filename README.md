# LifeMap AI

[Shared website](https://arnavshergill.github.io/CodeLinc-11-2026-Project/) · [Vercel website and AI backend](https://lifemap-ai-live.vercel.app)

LifeMap collects confirmed planning details through conversational intake and provides contextual educational answers. Planning and scenario screens use the existing team reference calculator in `back_end.py`, adapted by `calculator_bridge.py`. They respond to confirmed inputs. This is not Lincoln’s proprietary calculator; the teammate’s Lincoln integration can replace the calculator at that boundary. No competing insurance-needs formula is implemented in the frontend or AI layer.

## What works

- Get Started opens the dashboard directly. Registration and login have been removed; no name, email, password, or account database is required. Financial planning details remain in the tab and reset on reload.

- Profiles start empty. Intake extracts stated facts, including multiple fields and corrections, and proposes them for explicit confirmation before saving.
- AI-generated mini-lessons cover protection, needs, term/permanent tradeoffs, future changes, and next steps. Each includes an example, a comprehension check, and personalized follow-up with the tutor. Users can learn before sharing details and switch into planning at any time.
- The simulator starts with the calculated profile and reruns the same calculator for explicit life-event changes. It models proposed additional coverage over a chosen duration, compares remaining need, and lists assumptions. It does not treat a death benefit as income received when coverage starts.
- All 14 fields in the existing shared contract are supported. Missing fields are asked one at a time. Review allows manual corrections; a complete synthetic sample is available as a separate shortcut.
- Ask LifeMap receives the confirmed profile, recent conversation, calculator result, and its source. The team reference calculator is identified accurately, and an example profile is labeled when used.
- Requests have a timeout, duplicate-send protection, progress indicators, and retry without adding the same message twice.
- A short informational notice explains AI processing; chat sends immediately without a checkbox. Clear my details removes the in-tab profile and conversation. Reload resets financial planning details. End session clears the in-tab planning session.
- Server validation limits message length, conversation size, profile values, and request-body size. Review and scenarios require the same eight calculator inputs; optional context can remain blank, with omitted rates using the existing 2% inflation / 5% return defaults. Provider errors and visitor addresses are excluded from application logs. Per-instance limits allow up to 20 requests per minute per client and four concurrent model requests. Distributed rate limiting is not provided by this in-memory guard; configure a hosting-edge rule before relying on a global limit.

## Local development

Requires Python 3.12 or newer. From a fresh clone:

```sh
git clone https://github.com/ArnavShergill/CodeLinc-11-2026-Project.git
cd CodeLinc-11-2026-Project
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app_server.py
```

Open http://127.0.0.1:5173. One process serves the landing page, dashboard, calculator and AI routes, with dynamically generated same-origin browser configuration. No editing of `config.js`, Node installation, or second server is required. On Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

The calculator works without an AI key. Live AI lessons and natural-language extraction require a running Ollama model or an Ollama Cloud key. Set `OLLAMA_API_KEY` in an ignored `.env.local` file or the server environment to select Ollama Cloud automatically. Without a cloud key, the default is Ollama at http://127.0.0.1:11434/api/chat with `gemma3:latest`; install and start that model separately. Explicit `LIFEMAP_OLLAMA_URL` and `LIFEMAP_OLLAMA_MODEL` override the defaults. Never commit an actual key.

## Docker / judge submission

In the submission form choose **Dockerfile** and set its path to **`Dockerfile`**. Remove the old prose from the command box. The application listens on **port 5173**. See [submission checklist](docs/docker-submission.md).

```sh
docker build -t lifemap-ai -f Dockerfile .
docker run --rm -p 5173:5173 lifemap-ai
```

Open http://localhost:5173. Add `-e OLLAMA_API_KEY` to the run command if the key is already exported in your shell; secrets must be runtime settings, not image contents. A Linux host running Ollama can use `--add-host=host.docker.internal:host-gateway` with `-e LIFEMAP_OLLAMA_URL=http://host.docker.internal:11434/api/chat` and the desired model. Node is needed only for JavaScript tests, not to run the application.

`.github/workflows/submission.yml` builds this Dockerfile, starts the actual container, verifies the website/API/calculator/scenarios, restarts it, and verifies the API again.

## Hosting

The shared repository's `.github/workflows/pages.yml` tests and publishes `lifemap-ai-main` to GitHub Pages. GitHub Pages must use **GitHub Actions** as its source. Relative asset paths and hash routes support the repository subpath. Its browser configuration points to the working Vercel API.

The Vercel deployment currently uses `Amos-Isaya/lifemap-ai-live`, a separate repository. Backend changes must reach that repository to deploy; pushing to the shared repository alone does not redeploy its AI service.

[Deploy a new combined website/API to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FArnavShergill%2FCodeLinc-11-2026-Project&env=OLLAMA_API_KEY&envLink=https%3A%2F%2Follama.com%2Fsettings%2Fkeys&project-name=lifemap-ai&repository-name=lifemap-ai). The root `vercel.json` and `scripts/build_vercel.py` build the static website with same-origin API connections. Vercel defaults to Ollama Cloud and `gemma4:31b`. Set `OLLAMA_API_KEY` for AI; never commit these values or place them in browser configuration. Model and service URL variables remain optional overrides. Production endpoints must be publicly accessible for GitHub Pages to call them.

Endpoints:

- `POST /api/chat`: `{message, conversation, context: {profile, result?, resultSource, assessment?}}` → `{reply, profile, assessment, mode, missingFields?, result?}`. Carry assessment state into the next request; see [assessment flow](docs/assessment-chat.md).
- `POST /api/intake`: same body plus `field` (a contract field or null) → `{updates, reply}`. These updates are proposals; the browser commits them only after confirmation.
- `POST /api/calculate`: `{profile}` → `{result}` from the team reference calculator.
- `POST /api/scenario`: `{profile, scenario?, changes?, proposedCoverage?, policyYears?}` → calculator result, baseline, explicit changes, five timeline points and assumptions.
- `POST /api/lesson`: `{topic, context}` → a validated AI-generated lesson with a comprehension question.
- `GET /api/health`: server liveness only, not model readiness.

The GitHub Pages origin and local preview origins are allowed. Add other origins through comma-separated `LIFEMAP_ALLOWED_ORIGINS`. `PORT` or `LIFEMAP_API_PORT` controls the local bridge port.

## Lincoln calculator handoff

Keep the existing `back_end.py` and the team's Lincoln calculator work as the calculation owner. The frontend does not change their formulas or select a Lincoln calculator.

The checked-in browser configuration now points to the live team-reference endpoints. Override these URLs when the Lincoln integration is ready:

```js
window.LIFEMAP_CONFIG = {
  chatApiUrl: 'https://lifemap-ai-live.vercel.app/api/chat',
  calculateApiUrl: 'https://YOUR-BACKEND/api/calculate',
  scenarioApiUrl: 'https://YOUR-BACKEND/api/scenario'
};
```

`calculateApiUrl` accepts `POST {profile}`. `scenarioApiUrl` accepts `POST {profile, scenario, changes}`; changes are explicit field overrides, while the confirmed base profile remains unchanged. Scenario IDs are `child`, `home`, `income`, `debt`, and `married`. Both return `{result: LifeNeedsResult}`. The endpoints must support the calling frontend's origin. Confirm the teammate's endpoint, auth requirements, and result shape before setting these URLs.

`LifeNeedsResult` uses finite non-negative numbers for `immediateNeeds`, `longTermNeeds`, `totalNeeds`, `availableResources`, and `additionalCoverageNeeded`, plus `breakdown: [{label, amount}]` and `assumptions: string[]`. The breakdown convention still needs agreement with the backend owner. Map the Lincoln response at that API boundary rather than making AI infer financial numbers.

With `calculateApiUrl` configured, the review screen calls that endpoint, validates the response, and marks it `backend`. AI explanations then use those exact calculator numbers. With `scenarioApiUrl` configured, the simulator exposes explicit scenario inputs and displays the returned result. The current `calculator_bridge.py` maps the team reference output to this contract without altering `back_end.py`. Its future view reruns that calculator with fewer remaining income-support years, holds other amounts constant unless changed explicitly, and models the proposed additional coverage as zero after the chosen duration. It does not model premium pricing, underwriting, cash value, investment growth, or actual products. The Vercel build keeps extra configuration keys while replacing only `chatApiUrl` with its same-origin URL.

## Verification

```sh
npm test
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

Frontend tests cover empty profiles, proposed extraction, invalid-value rejection, context/history, retry errors, fixture boundaries, and calculator/scenario adapters. Python tests cover extraction validation, source context, HTTP request validation, burst limits, and sanitized failures.

Browser QA requires Playwright and Chrome:

```sh
PLAYWRIGHT_MODULE_PATH=/path/to/playwright QA_STATIC_ROOT="$PWD/lifemap-ai-main" node lifemap-ai-main/tests/browser-check.cjs
```

This serves local assets at the Pages origin and mocks API responses to check lessons, quizzes, confirmation, correction, retry, privacy, context, calculator input changes, scenario context, clearing, and all nine routes at desktop/tablet/mobile widths. It does not replace a live deployment smoke test.


## Pre-submission audit

See [the audit report](docs/pre-submission-audit.md) for formula traces, confirmed bugs, verification commands, and unresolved submission risks. Run the offline real-calculator browser audit with `AUDIT_PYTHON=/path/to/python PLAYWRIGHT_MODULE_PATH=/path/to/playwright node lifemap-ai-main/tests/audit-browser.cjs`. It starts an isolated Python HTTP server, uses synthetic profiles, and stubs only model generation. `python scripts/audit_secrets.py` checks the current local key against tracked files, built output, and reachable Git history without printing it.
