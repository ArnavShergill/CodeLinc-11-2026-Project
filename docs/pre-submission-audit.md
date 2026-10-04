# Pre-submission audit — October 4, 2026

Historical audit snapshot: account signup/login was subsequently implemented, then removed completely at the user’s request. The current application requires no account or database. The findings below describe the original audit, not the current account-free flow.

Changes are local, not committed, pushed, or deployed. No interface redesign or calculation methodology change was made. Financial integration tests use synthetic profiles and stubbed model responses, with actual local Python calculation endpoints.

## Results

| Area | Result | Evidence / limitation |
| --- | --- | --- |
| Deterministic calculations | PASS | Independent formula checks, field mapping, defaults, rounding, repeated identical results, no input mutation |
| Requested $756,950 test case | FAIL — verification incomplete | Displayed subtraction reconciles; original income-support inputs unavailable |
| Five Future Simulator scenarios | PASS after fixes | Actual HTTP calculations, profile changes, chart, comparison, explanation context, original plan preservation |
| Main planning journey | PASS after fixes | Intake, confirmation, review, calculate, breakdown, simulator, explanations, edit/recalculate and retries |
| All interactive controls | PARTIAL | Main journey and responsive routes checked; not a claim that every decorative/landing control was exhaustively tested |
| Automated regressions | PASS | 47 Python tests, 9 JavaScript tests, two browser suites |
| Validation and secret handling | PASS within stated scope | Invalid/nonfinite inputs rejected; current saved key absent from tracked files, build output and checked history |
| Account creation / login readiness | FAIL — configuration missing | Supabase URL and publishable key are empty; real signup cannot work until configured |
| Formula preservation | PASS | Team-reference methodology retained; official Lincoln integration remains pending |

## Financial trace and methodology

Intake extracts values into `LifeNeedsProfile`; confirmed values enter frontend profile state. Review edits validate that state. `/api/calculate` validates the profile, calls `calculator_bridge.calculate`, which calls `back_end.calculate_life_needs`. The bridge returns the existing result contract. Results and Coverage Breakdown consume that response; `/api/scenario` calculates a separate merged profile and retains `baseResult`.

| Profile input | Calculation | API / display |
| --- | --- | --- |
| `mortgageBalance` | Full balance added once | Immediate needs, mortgage breakdown |
| `otherDebt` | Full balance added once | Immediate needs, debt breakdown |
| `finalExpenses` | Added once | Immediate needs, final-expense breakdown |
| `desiredAnnualIncome`, `incomeReplacementYears` | Discounted annual support below | Long-term needs, income-support breakdown |
| `collegeFundingNeed` | Entered lump sum added once | Long-term needs, education breakdown |
| `existingLifeInsurance` | Resource subtracted once | Available resources, insurance line |
| `availableAssets` | Resource subtracted once | Available resources, assets line |
| `inflationRate`, `investmentReturnRate` | Decimal rates in support formula | Assumptions and editable percentages |
| Annual/spouse income, dependents, ages | Context; no automatic inferred support or education amount | Profile and assessment context |

Income support = annual support × sum of `((1 + inflation) / (1 + investment return))^t`, for `t = 0 … years − 1`. The first payment occurs at year zero. Omitted rates retain the existing defaults: 2% inflation and 5% investment return.

Immediate needs = mortgage + other debt + final expenses. Long-term needs = income support + education. Total needs = immediate + long-term. Resources = insurance + assets. Additional coverage = max(0, total needs − resources).

Backend response amounts round to cents; normal UI amounts display whole dollars. Components and aggregates round independently, so displayed component sums can differ slightly through rounding. Editable percentage values preserve fractional percentages such as 2.75%; axes use approximate thousands. No formula was altered to fit a screenshot.

The AI extracts and explains. Authoritative coverage comes from the deterministic backend. Result/projection explanations insert backend amounts; optional model commentary is restricted to qualitative text. Regression tests reject invented numeric recommendations. This is an application guard, not a guarantee about arbitrary educational model output.

## Requested completed case

The supplied values reconcile: $756,950 − $50,000 − $100,000 = $606,950. An income-support component of $621,950 leaves $135,000 for all other needs combined.

Exact reproduction of $621,950 remains unverified. Required evidence is the original annual support, support years, inflation and investment return, plus the other needs to reconcile the total. These details are held in the application's tab and were not available in the repository. A clarification was requested. Do not submit this component as independently certified until those inputs are provided.

The checked-in synthetic fixture does independently reconcile: income support $440,375.55; immediate needs $220,000; education $80,000; total needs $740,375.55; resources $150,000; additional coverage $590,375.55.

## Simulator reproduction and fixes

Before the fix, Apply rejected a valid eight-required-field profile because frontend validation required all fourteen fields. No scenario request was sent; the page showed an input-review error. Additional confirmed defects reset applied inputs to baseline and discarded changes on retry.

Validation now matches the existing eight-field assessment contract. Applied scenario values remain in the form, retries retain the exact failed changes, and edits invalidate stale projections. Each successful Apply sends one request and updates the scenario profile, calculated result, chart, comparison and explanation context while preserving the original plan.

Actual HTTP/browser tests and independent calculator tests cover:

| Scenario | Synthetic changes | New additional coverage (baseline $590,375.55) |
| --- | --- | --- |
| Have a child | Dependents 4; education $100,000; annual support $55,000 | $654,413.10 |
| Buy a home | Mortgage $250,000 | $660,375.55 |
| Increase income | Income $100,000; annual support $60,000 | $678,450.66 |
| Pay off loans | Other debt $0 | $565,375.55 |
| Get married | Spouse income $60,000; annual support $55,000 | $634,413.10 |

Changing only salary, spouse income or dependent count intentionally does not change the financial estimate; those are context fields, not support/education formulas. This distinction needs to be explained during demonstrations.

Projection points rerun the same calculator at years 0, 5, 10, 15 and 20 with remaining support years. Other balances remain fixed unless explicitly changed. Proposed coverage is constant until the chosen term expires, then zero. Remaining gap is clamped to zero. This is a planning illustration, not a forecast of premiums, cash value, investment growth or mortgage amortization.

## Other confirmed defects fixed

- Blank optional rates became 0% instead of retaining defaults; blank required edits could become zero. Optional blanks now remain omitted and invalid required edits stay visibly invalid.
- Fractional percentage edits/display rounded away meaningful precision. Percentage round trips now preserve it.
- Raw backend accepted booleans, nonfinite amounts, invalid counts/ages and overflowed aggregates. These produce validation errors instead of financial results.
- Projection explanations could use baseline facts or unrestricted model amounts. They now use deterministic scenario facts and qualitative model commentary.
- Both chart series inherited the same stroke despite different legend colors. The proposed-coverage line now matches its existing legend.
- Build copying could include secret/generated files. Build output is cleaned and sensitive file patterns excluded.
- One generated Python bytecode file was tracked despite ignore rules. It is removed locally.

## Files changed

Audit changes: `.gitignore`, `AI_interact.py`, `back_end.py`, `calculator_bridge.py`, `README.md`, `lifemap-ai-main/src/app.js`, `lifemap-ai-main/src/theme.css`, `lifemap-ai-main/src/types/contracts.js`, `lifemap-ai-main/tests/contracts.test.js`, `lifemap-ai-main/tests/audit-browser.cjs`, `scripts/build_vercel.py`, `scripts/audit_secrets.py`, `tests/test_calculation_audit.py`, `tests/test_submission_safety.py`, this report, and removal of tracked bytecode.

The working tree also contains earlier uncommitted assessment/account work in `api_server.py`, `chat_features.py`, frontend config/dashboard/services, existing browser/chat tests, new auth service, assessment tests and setup documentation. Those are not newly introduced by this audit.

## Automated tests and commands

New calculator audit suite: 15 tests covering independent sum, first payment, equal rates, every need/resource, zero/excess resources, determinism, aliases, defaults, rate direction, invalid values/overflow, cents, all scenarios, context-only edits, override validation and AI projection amounts. New submission safety suite: 2 tests. Added frontend required/optional profile regression. The real-HTTP browser suite checks all five scenarios, retry retention, chart/legend, AI context, original plan, edit/recalculate, invalid blanks and rate round trips.

Results: Python 47/47; JavaScript 9/9; existing responsive browser suite PASS; real-HTTP audit browser suite PASS (4 calculate requests and 15 scenario requests including edits/retries/policy controls); build PASS; syntax and whitespace checks PASS; current-key scan PASS.

Exact verification commands (temporary paths are this machine's installed test tools):

```sh
npm test
PYTHONDONTWRITEBYTECODE=1 /private/tmp/lifemap-vercel-qa/bin/python -m unittest discover -s tests
PLAYWRIGHT_MODULE_PATH=/private/tmp/lifemap-pages-qa/node_modules/playwright QA_STATIC_ROOT="$PWD/lifemap-ai-main" node lifemap-ai-main/tests/browser-check.cjs
AUDIT_PYTHON=/private/tmp/lifemap-vercel-qa/bin/python PLAYWRIGHT_MODULE_PATH=/private/tmp/lifemap-pages-qa/node_modules/playwright node lifemap-ai-main/tests/audit-browser.cjs
PYTHONDONTWRITEBYTECODE=1 /private/tmp/lifemap-vercel-qa/bin/python scripts/build_vercel.py
python3 scripts/audit_secrets.py
node --check lifemap-ai-main/src/app.js
node --check lifemap-ai-main/tests/audit-browser.cjs
git diff --check
```

## Security scope and remaining submission risks

`.env.local` is ignored and untracked. The current saved Ollama key had zero matches in tracked files, generated `public` output or 146 checked reachable history blobs. The check does not prove absence of every unknown historical credential. Browser config contains endpoint URLs and empty public auth configuration; provider secrets stay server-side. API financial profiles are not unnecessarily logged. Auth passwords are sent directly to the auth provider, not the AI.

Remaining risks: exact requested income-support case needs original inputs; account provider is unconfigured; official Lincoln calculator integration is pending; audited changes are local and hosted sites still run older deployments. Financial model calls were stubbed in automated tests, so these tests do not certify live model extraction accuracy. API rate/concurrency guards are process-local rather than globally shared across serverless instances. Model response latency can still require retry. Authentication does not currently provide server-side saved-plan persistence or protect the public calculation endpoints.
