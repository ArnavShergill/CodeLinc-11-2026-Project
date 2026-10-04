"""Prepare the static frontend with the same-domain Vercel chat endpoint."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
source = root / "lifemap-ai-main"
output = root / "public"
# Build from a clean generated directory: ignored secrets cannot survive an old build.
if output.exists():
    shutil.rmtree(output)
shutil.copytree(source, output, ignore=shutil.ignore_patterns(
    "tests", "artifacts", "node_modules", ".env", ".env.*", ".vercel",
    "__pycache__", "*.pyc", ".DS_Store", "credentials*.json", "service-account*.json", "*.key", "*.pem",
    ".lifemap-data", "*.sqlite3", "*.sqlite3-*"
))
(output / "config.js").write_text(
    (source / "config.js").read_text()
    + "\nwindow.LIFEMAP_CONFIG.chatApiUrl = window.location.origin + '/api/chat';\n"
    + "for (const [key, route] of [['calculateApiUrl', 'calculate'], ['scenarioApiUrl', 'scenario']]) {\n"
    + "  if (window.LIFEMAP_CONFIG[key] === 'https://lifemap-ai-live.vercel.app/api/' + route) {\n"
    + "    window.LIFEMAP_CONFIG[key] = window.location.origin + '/api/' + route;\n"
    + "  }\n}\n"
)
