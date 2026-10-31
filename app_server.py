"""One-process website and API server for local clones and Docker judging."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_local_environment():
    """Optional ignored local settings; deployed environment values take priority."""
    path = ROOT / '.env.local'
    if path.exists():
        allowed = {'OLLAMA_API_KEY', 'LIFEMAP_OLLAMA_URL', 'LIFEMAP_OLLAMA_MODEL',
                   'LIFEMAP_ALLOWED_ORIGINS'}
        for line in path.read_text().splitlines():
            key, separator, value = line.partition('=')
            if separator and key.strip() in allowed:
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    if os.environ.get('OLLAMA_API_KEY'):
        os.environ.setdefault('LIFEMAP_OLLAMA_URL', 'https://ollama.com/api/chat')
        os.environ.setdefault('LIFEMAP_OLLAMA_MODEL', 'gemma4:31b')


if __name__ == '__main__':
    load_local_environment()

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse
from api_server import LifeMapAPIHandler


class LifeMapAppHandler(LifeMapAPIHandler, SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'lifemap-ai-main'), **kwargs)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path.startswith('/api/'):
            return LifeMapAPIHandler.do_GET(self)
        if path == '/config.js':
            body = (
                "window.LIFEMAP_CONFIG = {};\n"
                "for (const [key, route] of [['chatApiUrl','chat'],['calculateApiUrl','calculate'],"
                "['scenarioApiUrl','scenario']]) {\n"
                " window.LIFEMAP_CONFIG[key] = window.location.origin + '/api/' + route;\n}\n"
            ).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
            return
        if any(part.startswith('.') or part in ('tests', 'node_modules') for part in path.split('/') if part):
            self.send_error(404)
            return
        return SimpleHTTPRequestHandler.do_GET(self)

    def list_directory(self, path):
        self.send_error(404)
        return None


def main():
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5173'))
    server = ThreadingHTTPServer((host, port), LifeMapAppHandler)
    print(f'LifeMap website and API listening at http://{host}:{port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
