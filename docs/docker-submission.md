# Docker resubmission checklist

The judge's first build used the command-box text as a shell command. The text started with "select", so it was not an executable build/start command and exited with code 127. The follow-up confirmed that the existing Dockerfile started the static site but omitted `chat_features.py`, leaving its separate API process dead.

## Submission form

At https://codelinc-lfg.com/submit, use the same submission code as before:

- Repository: `https://github.com/ArnavShergill/CodeLinc-11-2026-Project`
- How your project builds: **Dockerfile**
- Dockerfile path: **`Dockerfile`** (relative to repository root)
- Application port, if requested: **5173**
- Build context, if requested: repository root, **`.`**
- Command box: remove the previous prose. No custom command is needed in Dockerfile mode; the image defines its startup command.
- If a commit is requested, use the latest verified commit from the repository rather than the old `093a58d`.

The submission code is not a repository secret to publish; enter it directly in the form. The judge's email says the last submission counts and entries close at 09:00 Eastern. Check the organizer's current instructions for the deadline.

## Fixes

The Dockerfile now installs `requirements.txt`, copies every root Python module with `COPY *.py ./`, and runs `python app_server.py`. This includes `chat_features.py`, `learning.py`, `calculator_bridge.py`, and all other root runtime modules. One process serves both the frontend and API, so a failed API import fails the server rather than leaving only a static page running. The server binds `0.0.0.0:5173` in Docker, provides `/api/health`, generates same-origin frontend endpoint URLs, and supports a `PORT` override.

The container runs as a non-root user. `.env` files, credentials and local account databases are excluded from the Docker build context.

## Exact build/run/check commands

```sh
docker build --pull -t lifemap-submission -f Dockerfile .
docker run -d --name lifemap-submission -p 5173:5173 lifemap-submission
python3 scripts/smoke_submission.py http://127.0.0.1:5173
docker restart lifemap-submission
python3 scripts/smoke_submission.py http://127.0.0.1:5173
docker logs lifemap-submission
docker rm -f lifemap-submission
```

The smoke test checks the landing page and required assets, same-origin endpoints, API health, deterministic calculation, all five scenarios, greeting, percentage intake, private-file protection. It sends no financial data to a model provider.

The GitHub Actions **Verify Docker submission** workflow runs the actual Docker build and these smoke checks on Linux. Docker is not installed on the development Mac; a native smoke test alone is not presented as proof of a successful Docker build.

## Runtime configuration

The image starts and deterministic calculations work without an API key. AI-generated lessons and natural-language extraction need a model service: pass `OLLAMA_API_KEY` at runtime for Ollama Cloud, or configure `LIFEMAP_OLLAMA_URL` and `LIFEMAP_OLLAMA_MODEL` for a running local Ollama server. The submission system must provide the AI key as an environment variable if live cloud AI is evaluated. Never commit the key or bake it into the image.

Registration, login, and the account database have been removed. Financial plans remain in the browser tab. Official Lincoln integration remains pending. The financial formulas were not changed for this resubmission.
