"""Prepare the static frontend with the same-domain Vercel chat endpoint."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
source = root / "lifemap-ai-main"
output = root / "public"
shutil.copytree(source, output, dirs_exist_ok=True, ignore=shutil.ignore_patterns("tests", "artifacts", "node_modules"))
(output / "config.js").write_text(
    (source / "config.js").read_text()
    + "\nwindow.LIFEMAP_CONFIG.chatApiUrl = window.location.origin + '/api/chat';\n"
)
