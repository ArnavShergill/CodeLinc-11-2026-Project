# Stateful assessment chat

`POST /api/chat` retains the existing `message`, `conversation`, and `context` request fields and `reply` response field. Its response also includes `profile`, `mode`, and `assessment`. During intake it includes `missingFields`. On completion it includes the unchanged calculator result contract and `resultSource: "backend"`.

Carry the returned `profile` as `context.profile` and returned `assessment` as `context.assessment` on the next request. The frontend chat adapter does this. State is client-carried, validated on every request, and never stored in a shared process-wide customer dictionary. Independent tabs cannot overwrite each other's profile. Dropping state starts a new assessment.

A needs-assessment request starts intake. The model extracts all explicitly provided facts and corrections using the current question as context. Previously supplied facts remain unless explicitly updated; null and omitted values never remove them. Unambiguous direct numeric and none/zero answers also work if the model is unavailable. Invalid numeric values are rejected. Every intake turn derives its one question from the existing required-field helpers.

An educational question receives a short explanation and preserves the pending assessment. When all eight required calculator fields are available, the existing calculator bridge runs. The coverage statement is built directly from its returned values. Optional AI explanation cannot include numeric amounts or replace that coverage statement. The backend formula and its defaults are unchanged.

`API_request()` remains a string-returning compatibility helper; API clients should retain the structured `/api/chat` response state. `/api/intake` remains a separate proposed-facts/confirmation endpoint.

Test with `python -m unittest discover -s tests` and `npm test`.
