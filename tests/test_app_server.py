"""Clone/Docker server regression: website and APIs share one live process."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from app_server import LifeMapAppHandler
from scripts.smoke_submission import verify


class AppServerTests(unittest.TestCase):
    def test_complete_submission_smoke(self):
        with tempfile.TemporaryDirectory() as temporary:
            from api_server import _requests
            _requests.clear()
            server = ThreadingHTTPServer(('127.0.0.1', 0), LifeMapAppHandler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = 'http://127.0.0.1:' + str(server.server_port)
            try:
                verify(base)
                _requests.clear()
                verify(base)
            finally:
                server.shutdown(); server.server_close(); worker.join()
                _requests.clear()

    def test_docker_copies_all_runtime_modules_and_excludes_secrets(self):
        root = Path(__file__).resolve().parents[1]
        docker = (root / 'Dockerfile').read_text()
        self.assertIn('COPY *.py ./', docker)
        self.assertIn('pip install --no-cache-dir -r requirements.txt', docker)
        self.assertIn('CMD ["python", "app_server.py"]', docker)
        self.assertNotIn('npm run api &', docker)
        ignored = (root / '.dockerignore').read_text()
        for pattern in ('.env.*', '.lifemap-data/', '*.sqlite3', '.venv/'):
            self.assertIn(pattern, ignored)
