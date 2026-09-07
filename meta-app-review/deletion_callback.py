#!/usr/bin/env python3
"""Meta Data Deletion Callback — stdlib-only skeleton (required for App Review).

Meta POSTs a signed_request when a user removes your app / requests deletion.
This endpoint verifies the signature (APP_SECRET), purges that user's rows from
matches.db, and returns {"confirmation_code": ...} for the user to track status.

Run behind TLS on your always-on box:
    APP_SECRET=... python3 meta-app-review/deletion_callback.py   # :8080/deletion
Then register https://YOUR-HOST/deletion as the Data Deletion Callback URL.

NOTE: our matches table keys on public handles/permalinks, not Meta PSIDs, so the
purge matches on the app-scoped user id stored in the `fields` column convention
(see TODO). Adapt the DELETE to your schema before submitting to review.
"""
import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "matches.db")


def parse_signed_request(signed_request, secret):
    sig_b64, payload_b64 = signed_request.split(".", 1)
    sig = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
    payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)))
    expected = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("bad signature")
    return payload


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/deletion":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            params = urllib.parse.parse_qs(body)
            data = parse_signed_request(params["signed_request"][0], os.environ["APP_SECRET"])
            user_id = data.get("user_id", "")
            # TODO: adapt to your schema — deletes rows attributable to this user.
            con = sqlite3.connect(DB_PATH)
            cur = con.execute("DELETE FROM matches WHERE snippet LIKE ?", (f"%{user_id}%",))
            con.commit()
            purged = cur.rowcount
            con.close()
            code = f"DEL-{int(time.time())}-{user_id[-4:] if user_id else '0000'}"
            print(f"[deletion] user={user_id} purged={purged} code={code}")
            resp = {"url": f"https://example.invalid/deletion-status/{code}",
                    "confirmation_code": code}
            out = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
        except Exception as e:
            print(f"[deletion] failed: {e}")
            self.send_response(400)
            self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not os.environ.get("APP_SECRET"):
        raise SystemExit("set APP_SECRET env first")
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
