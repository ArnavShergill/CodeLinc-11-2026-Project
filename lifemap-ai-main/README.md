# LifeMap frontend

Eight-screen LifeMap customer demo with a unified deep teal, warm ivory and blue visual identity for 0x11 / codeLinc 11. The browser app uses a small local Python bridge for AI chat; profile values, plan calculations and explanations remain demo fixtures.

## Run

Run the frontend and API in separate terminals. For the included frontend server, open a terminal at the repository root (the folder containing `lifemap-ai-main`) and run:

```sh
npm run dev
```

In the second terminal at the repository root, start the Python API:

```sh
npm run api
```

Then open http://127.0.0.1:5173. If using VS Code Live Server instead, it may serve the frontend on port 5500; the API still listens separately on `127.0.0.1:8000`, and allows requests from both frontend ports. Port 5500 cannot also be used by the API while Live Server is using it. The API health endpoint is http://127.0.0.1:8000/api/health. Ollama must be running locally with `gemma3:latest` available (`ollama pull gemma3`). Requires Python 3, Pydantic, the Ollama service, and npm; no npm install is needed. `LIFEMAP_OLLAMA_MODEL` and `LIFEMAP_OLLAMA_URL` can override the model service defaults. Inter from Google Fonts is optional; local sans-serif fonts provide a fallback.

## Click through

Get started → Start my plan → send four replies (or Use example) → Review my information → edit any fields → Calculate my plan → See full breakdown → Try a life scenario → choose a milestone. Use the sidebar for Home, My Plan, Future Simulator, Coverage Breakdown, and Ask LifeMap. My Plan is selected during intake and review. Mobile navigation opens with the menu button.

Hash routes: `#landing`, `#home`, `#intake`, `#review`, `#results`, `#breakdown`, `#simulator`, `#learn`. Landing anchor: `#features`. How It Works, Watch Demo, FAQ, Settings and the Amos dropdown use lightweight informational dialogs. Direct results/breakdown links show a useful empty state until a result is requested.

## Files and ownership

The frontend is a dependency-free browser app with a small Python service bridge for local AI chat.

- `index.html`: entry document.
- `package.json`: local preview, API, and contract-test commands; no framework dependencies.
- `src/app.js`: navigation, page presentation and frontend interaction state.
- `src/styles.css`: reference blue/white palette, desktop/tablet/mobile styling, focus and reduced-motion support.
- `src/assets/protection-illustration.svg`: original shield/home/heart illustration with family and policy symbols.
- `src/theme.css`: shared teal/ivory/blue design for landing and every application screen.
- `src/two-tone.css`: saved two-color experiment, currently inactive; the single-color teal version is selected.
- `src/assets/teal-landscape.svg`: retained prior landscape, currently unused.
- `src/landing.css`: scoped deep teal, warm stone and ivory styling inspired by the latest user reference.
- `src/assets/family-placeholder.svg`: retained earlier illustration, currently unused.
- `src/data/mockConversation.js`: isolated guided demo questions and responses.
- `src/types/contracts.js`: documented contract names and frontend input validation.
- `src/data/mockProfile.js`: exact synthetic profile from the supplied contract.
- `src/data/mockResult.js`: isolated illustrative LifeNeedsResult; no financial formula.
- `src/data/mockScenarios.js`: fixed timelines and before/after scenario fixtures.
- `src/services/planService.js`: AI, backend and explanation adapters.
- `../api_server.py`: local HTTP bridge that forwards browser chat requests to `AI_interact.API_request`.
- `tests/contracts.test.js`: meaningful adapter boundary and validation tests.
- `tests/browser-check.cjs`: optional browser journey and mobile QA helper.
- `artifacts/`: browser screenshots from completed QA.

## Integration boundaries

**AI chat:** Intake messages and Ask LifeMap questions call `src/services/planService.js` → `POST http://127.0.0.1:8000/api/chat` → `api_server.py` → `AI_interact.API_request`. Conversation turns are included for context. The AI reply is live, but intake still advances four demo questions and fills synthetic fixture profile values; it does not extract user facts into the profile.

**Backend owner:** Replace `calculatePlan` in the same service: POST complete LifeNeedsProfile → validated LifeNeedsResult. Keep errors surfaced to the review UI. Replace the fixture provider without changing the result presentation. No endpoint URL was supplied.

**AI explanation:** Replace `explainPlan`: verified LifeNeedsResult → plain-language explanation. Numbers stay owned by the backend.

**Shared contract:** Exact top-level field names and synthetic profile are preserved. The supplied contract does not specify breakdown item types. `{label, amount}` is a frontend fixture convention only; agree on the real item schema and map it at the service boundary. Numeric types/rates reflect the synthetic fixture; rates are fractional in data and displayed as percentages in review.

## Demo limits

No authentication, persistence, natural-language profile extraction, live calculations or scenario formulas. Login enters the demo. Profile edits are functional but intentionally do not alter the fixed result or scenario values; this is explained visibly. Reload resets the demo. Static educational topics and calculation results remain fixtures. The local AI service must be running to use chat; connection and model errors are surfaced in the UI. The public landing uses the selected single-color deep teal version with blue accents. The public landing and application share the requested palette: floating warm-ivory navigation, a centered serif headline, a protection illustration, deep teal shading, blue CTAs and three quiet benefits. Welcome has two cards and an Ask input; review uses editable rows with advanced fields in an expandable section. The simulator has one blue line and tooltips available on hover, focus, or selection. Before making profiles or calculations live, normalize and validate real responses and agree on breakdown types.

## Verification

`npm test`: six checks cover profile validation, fixed results independent of edits, the Python AI bridge adapter, surfaced AI-service errors, unavailable-service guidance, and invalid-profile rejection.

Chrome QA passed the complete customer journey, main buttons and dialogs, profile row editing and invalid-age validation, all five scenario comparisons, chart hover/selection and keyboard interaction, mobile menu, and educational/question interactions. All eight routes were checked at 1440×1000, 768×1024, and 390×844 with no horizontal overflow. No console errors or uncaught page exceptions. Screenshots of all eight desktop/mobile screens are in `artifacts/`.

The optional browser helper requires Playwright and Chrome. Set `PLAYWRIGHT_MODULE_PATH` to an installed Playwright package or install Playwright in a separate QA environment, then run `node tests/browser-check.cjs` while the preview server runs.
