# LifeMap AI

[Shared website](https://arnavshergill.github.io/CodeLinc-11-2026-Project/) · [Vercel website and AI backend](https://lifemap-ai-live.vercel.app)

LifeMap collects confirmed planning details through conversational intake and provides contextual educational answers. Planning and scenario screens use the existing team reference calculator in `back_end.py`, adapted by `calculator_bridge.py`. They respond to confirmed inputs. This is not Lincoln’s proprietary calculator; the teammate’s Lincoln integration can replace the calculator at that boundary. No competing insurance-needs formula is implemented in the frontend or AI layer.

## What works

- Profiles start empty. Intake extracts stated facts, including multiple fields and corrections, and proposes them for explicit confirmation before saving.
- AI-generated mini-lessons cover protection, needs, term/permanent tradeoffs, future changes, and next steps. Each includes an example, a comprehension check, and personalized follow-up with the tutor. Users can learn before sharing details and switch into planning at any time.
- The simulator starts with the calculated profile and reruns the same calculator for explicit life-event changes. It models proposed additional coverage over a chosen duration, compares remaining need, and lists assumptions. It does not treat a death benefit as income received when coverage starts.
- All 14 fields in the existing shared contract are supported. Missing fields are asked one at a time. Review allows manual corrections; a complete synthetic sample is available as a separate shortcut.
- Ask LifeMap receives the confirmed profile, recent conversation, calculator result, and its source. The team reference calculator is identified accurately, and an example profile is labeled when used.
- Requests have a timeout, duplicate-send protection, progress indicators, and retry without adding the same message twice.
- A short informational notice explains AI processing; chat sends immediately without a checkbox. Clear my details removes the in-tab profile and conversation. Reload also resets the session. No localStorage or account persistence is used.
- Server validation limits message length, conversation size, profile values, and request-body size. Provider errors and visitor addresses are excluded from application logs. Per-instance limits allow up to 20 requests per minute per client and four concurrent model requests. Distributed rate limiting is not provided by this in-memory guard; configure a hosting-edge rule before relying on a global limit.

## Local development

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm run dev
```

In a second terminal, run `.venv/bin/python api_server.py`. Open http://127.0.0.1:5173. The local model defaults to Ollama at http://127.0.0.1:11434/api/chat with `gemma3:latest`. Set `LIFEMAP_OLLAMA_MODEL`, `LIFEMAP_OLLAMA_URL`, and optionally `OLLAMA_API_KEY` to use another running Ollama service. Browser configuration is in `lifemap-ai-main/config.js`; for fully local development set `chatApiUrl` to `http://127.0.0.1:8000/api/chat`.

## Hosting

The shared repository's `.github/workflows/pages.yml` tests and publishes `lifemap-ai-main` to GitHub Pages. GitHub Pages must use **GitHub Actions** as its source. Relative asset paths and hash routes support the repository subpath. Its browser configuration points to the working Vercel API.

The Vercel deployment currently uses `Amos-Isaya/lifemap-ai-live`, a separate repository. Backend changes must reach that repository to deploy; pushing to the shared repository alone does not redeploy its AI service.

[Deploy a new combined website/API to Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FArnavShergill%2FCodeLinc-11-2026-Project&env=OLLAMA_API_KEY&envLink=https%3A%2F%2Follama.com%2Fsettings%2Fkeys&project-name=lifemap-ai&repository-name=lifemap-ai). The root `vercel.json` and `scripts/build_vercel.py` build the static website with a same-origin `/api/chat` connection. Vercel defaults to Ollama Cloud and `gemma4:31b`. Enter only `OLLAMA_API_KEY` in Vercel; never commit it or place it in browser configuration. Model and service URL variables remain optional overrides. Production endpoints must be publicly accessible for GitHub Pages to call them.

Endpoints:

- `POST /api/chat`: `{message, conversation, context: {profile, result?, resultSource}}` → `{reply}`.
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

This serves local assets at the Pages origin and mocks API responses to check lessons, quizzes, confirmation, correction, retry, privacy, context, calculator input changes, scenario context, clearing, and all eight routes at desktop/tablet/mobile widths. It does not replace a live deployment smoke test.
