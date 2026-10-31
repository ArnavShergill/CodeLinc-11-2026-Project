# Conversational percentage inputs

Both guided intake and assessment chat use the shared parser in `AI_interact.py` before rates enter profile state. Human answers use percentage points: `2`, `2%`, `about 2 percent` → `0.02`; `2.5` or `2.5%` → `0.025`; zero → zero. Model-extracted rate values cannot override this normalization.

Bare nonzero fractions below one, including `0.02`, prompt clarification rather than guessing. Users can resolve the ambiguity by answering `0.02%` or `2%`. Blank, negative, malformed and out-of-range answers leave existing data unchanged and show the expected percentage format.

The conversational guard accepts 0–20% for both assumptions; it rejects unusually high values such as 89%. This is an input guard, not a change to calculator formulas, backend rate limits or review-form methodology. Rates remain optional calculator fields; this change does not add extra required intake questions.

Regression tests in `tests/test_percentage_input.py` cover both extraction paths, profile preservation, model-unit errors, calculator boundaries, and HTTP answers/errors. No UI redesign or financial formula changes.

Verification: 53 Python tests, 9 JavaScript tests, responsive browser suite, real-HTTP audit browser suite, Vercel build and `git diff --check` all pass. Commands are the same full-suite commands listed in `docs/pre-submission-audit.md`.
