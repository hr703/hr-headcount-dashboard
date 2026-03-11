#!/usr/bin/env python3
import json, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DATA_FILE    = os.path.join(os.path.dirname(__file__), 'data.json')
DATABASE_URL = os.environ.get('DATABASE_URL')

# ── STORAGE ──────────────────────────────────────────────────────────────────
if DATABASE_URL:
    import psycopg2

    def _conn():
        return psycopg2.connect(DATABASE_URL, sslmode='require')

    def _init():
        with _conn() as c:
            with c.cursor() as cur:
                cur.execute('''CREATE TABLE IF NOT EXISTS appdata
                               (id INT PRIMARY KEY, data TEXT NOT NULL)''')
                cur.execute('''INSERT INTO appdata (id, data)
                               VALUES (1, %s) ON CONFLICT (id) DO NOTHING''',
                            [json.dumps({'emp_data':[],'emp_depts':[],'emp_revisions':[],'emp_esops':[],'emp_esop_pool':50000})])
                c.commit()
    _init()

    def load_data():
        try:
            with _conn() as c:
                with c.cursor() as cur:
                    cur.execute('SELECT data FROM appdata WHERE id=1')
                    row = cur.fetchone()
                    return json.loads(row[0]) if row else {}
        except Exception as e:
            print(f'[DB READ ERROR] {e}')
            return {}

    def save_data(data):
        try:
            with _conn() as c:
                with c.cursor() as cur:
                    cur.execute('UPDATE appdata SET data=%s WHERE id=1', [json.dumps(data)])
                    c.commit()
        except Exception as e:
            print(f'[DB WRITE ERROR] {e}')
else:
    def load_data():
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        return {'emp_data':[],'emp_depts':[],'emp_revisions':[],'emp_esops':[],'emp_esop_pool':50000}

    def save_data(data):
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
# ─────────────────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200); self.send_cors(); self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/data':
            body = json.dumps(load_data()).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors(); self.end_headers()
            self.wfile.write(body)
        elif path in ('/', '/index.html'):
            with open(os.path.join(os.path.dirname(__file__), 'index.html'), 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_cors(); self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        path   = urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0))
        body   = json.loads(self.rfile.read(length))

        if path == '/api/data':
            save_data(body)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors(); self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404); self.end_headers()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f'HR Dashboard running at http://localhost:{port}')
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()
