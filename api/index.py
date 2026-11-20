import sys
import os
import traceback
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Ensure root directory is on sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from server import app
except Exception as e:
    err_tb = traceback.format_exc()
    print("CRITICAL IMPORT ERROR ON VERCEL:")
    print(err_tb)

    app = FastAPI(title="Kuku Promo Studio (Startup Diagnostic)")

    @app.get("/{full_path:path}")
    def catch_all(full_path: str = ""):
        return HTMLResponse(
            f"<html><body style='background:#0d1117;color:#fff;font-family:sans-serif;padding:30px;'>"
            f"<h2 style='color:#f85149;'>Vercel Python Startup Diagnostic</h2>"
            f"<p>An error occurred during application initialization:</p>"
            f"<pre style='background:#161b22;color:#ff7b72;padding:20px;border-radius:8px;overflow-x:auto;border:1px solid #30363d;'>{err_tb}</pre>"
            f"</body></html>",
            status_code=500
        )
