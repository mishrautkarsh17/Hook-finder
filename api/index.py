import sys
import os
import traceback
from fastapi import FastAPI, Response

# Top-level app variable unconditionally declared for Vercel AST scanner
app = FastAPI(title="Kuku Promo Studio")

try:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)

    from server import app as server_app
    app = server_app
except Exception as e:
    err_msg = f"Startup Error: {str(e)}\n{traceback.format_exc()}"
    print(err_msg)

    @app.get("/{rest_of_path:path}")
    def catch_all(rest_of_path: str = ""):
        return Response(content=err_msg, media_type="text/plain", status_code=500)
