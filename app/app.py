"""Agent run tracker: a tiny JSON API backed by Postgres."""
import json
import os
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg2
import psycopg2.extras

DB = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ.get("DB_NAME", "runs"),
    "user": os.environ.get("DB_USER", "app"),
    "password": os.environ.get("DB_PASSWORD", "app"),
    "connect_timeout": 3,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          SERIAL PRIMARY KEY,
    agent       TEXT NOT NULL,
    status      TEXT NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

_schema_ready = False
_schema_lock = threading.Lock()


@contextmanager
def db():
    """Open a connection, make sure the schema exists, commit on success."""
    global _schema_ready
    conn = psycopg2.connect(**DB)
    try:
        if not _schema_ready:
            with _schema_lock:
                if not _schema_ready:
                    with conn, conn.cursor() as cur:
                        cur.execute("SELECT pg_advisory_xact_lock(42)")
                        cur.execute(SCHEMA)
                    _schema_ready = True
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            with db() as cur:
                cur.execute("SELECT 1")
            self._send(200, {"status": "ok"})
        elif self.path == "/runs":
            with db() as cur:
                cur.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 100")
                rows = cur.fetchall()
            self._send(200, rows)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/runs":
            return self._send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
            agent = str(data["agent"])
        except (ValueError, KeyError):
            return self._send(400, {"error": "body must be JSON with an 'agent' field"})
        status = str(data.get("status", "completed"))
        duration_ms = int(data.get("duration_ms", 0))
        with db() as cur:
            cur.execute(
                "INSERT INTO runs (agent, status, duration_ms) VALUES (%s, %s, %s) RETURNING *",
                (agent, status, duration_ms),
            )
            row = cur.fetchone()
        self._send(201, row)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"listening on :{port}, db host {DB['host']}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
