"""
server.py - Production-ready FastAPI + React web server for Kuku Promo Studio.
Zero Streamlit, pure React + Tailwind frontend with REST API endpoints.
"""

import os
import json
import zipfile
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from parser import parse_screenplay, parse_all_episodes
from candidate_generator import generate_episode_candidates, generate_cross_episode_candidates
from scorer import score_candidate
from ranker import process_show, export_outputs

app = FastAPI(title="Kuku Promo Studio API")

# Root directory resolution
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(ROOT_DIR, "static")
MASTER_JSON_PATH = os.path.join(ROOT_DIR, "outputs", "promos_master.json")

# Determine writable cache directory (handles Vercel / serverless where only /tmp is writable)
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    CACHE_DIR = "/tmp/cache"
else:
    CACHE_DIR = os.path.join(ROOT_DIR, "cache")

try:
    os.makedirs(CACHE_DIR, exist_ok=True)
except Exception:
    CACHE_DIR = "/tmp/cache"
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception:
        pass

class ScreenplayRequest(BaseModel):
    screenplay_text: str
    api_key: Optional[str] = None

@app.get("/api/promos")
def get_promos():
    """Returns the pre-evaluated master catalog of 282 promos."""
    if os.path.exists(MASTER_JSON_PATH):
        with open(MASTER_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.post("/api/analyze")
def analyze_screenplay(req: ScreenplayRequest):
    """Parses and scores a new unseen screenplay on-the-fly."""
    if not req.screenplay_text.strip():
        raise HTTPException(status_code=400, detail="Screenplay text cannot be empty.")

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception:
        pass
    temp_path = os.path.join(CACHE_DIR, "react_temp_ep.txt")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(req.screenplay_text)

    parsed = parse_screenplay(temp_path)
    if parsed["total_blocks"] == 0:
        raise HTTPException(status_code=400, detail="No timestamped blocks found in screenplay format.")

    candidates = generate_episode_candidates(parsed)
    scored_promos = []

    for c in candidates:
        score_res = score_candidate(c, api_key=req.api_key, bypass_cache=True)
        scored_promos.append({
            "episode": parsed["episode_name"],
            "total_duration_sec": c["total_duration"],
            "segments": [
                {
                    "episode": seg["episode"],
                    "start_time": seg["start_ts"],
                    "end_time": seg["end_ts"],
                    "duration_sec": seg["duration"]
                }
                for seg in c["segments"]
            ],
            "hook": score_res["hook"],
            "hook_reasoning": score_res.get("hook_reasoning", "Captures immediate psychological attention in first 3s."),
            "cliffhanger": score_res["cliffhanger"],
            "cliffhanger_reasoning": score_res.get("cliffhanger_reasoning", "Cuts at the peak of emotional escalation before resolution."),
            "why_it_works": score_res["why_it_works"],
            "scores": {
                "overall": score_res["overall_score"],
                "hook": score_res.get("hook_score"),
                "cliffhanger": score_res.get("cliffhanger_score"),
                "eval_source": score_res.get("source", "API")
            }
        })

    scored_promos.sort(key=lambda p: p["scores"]["overall"], reverse=True)

    return {
        "episode_name": parsed["episode_name"],
        "duration_ts": parsed["total_duration_ts"],
        "total_blocks": parsed["total_blocks"],
        "promos": scored_promos
    }

@app.post("/api/upload_show")
async def upload_whole_show(
    files: List[UploadFile] = File(...),
    api_key: Optional[str] = Form(None)
):
    """
    Accepts an entire show:
    - Multiple .txt screenplay files (multi-file select)
    - OR a .zip archive containing all episode .txt files
    Parses all episodes, discovers single & cross-episode promos, and runs the ranking engine.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    upload_dir = os.path.join(CACHE_DIR, "uploaded_batch_show")
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)
    try:
        os.makedirs(upload_dir, exist_ok=True)
    except Exception:
        pass

    extracted_txt_count = 0

    for file in files:
        filename = file.filename.lower()
        if filename.endswith(".zip"):
            # It's a ZIP archive of the entire show!
            zip_dest = os.path.join(upload_dir, file.filename)
            with open(zip_dest, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            with zipfile.ZipFile(zip_dest, "r") as zip_ref:
                for member in zip_ref.namelist():
                    if member.endswith(".txt") and not member.startswith("__MACOSX"):
                        # Extract directly into upload_dir (flatten directories)
                        filename_only = os.path.basename(member)
                        if filename_only:
                            with zip_ref.open(member) as source, open(os.path.join(upload_dir, filename_only), "wb") as target:
                                shutil.copyfileobj(source, target)
                                extracted_txt_count += 1
        elif filename.endswith(".txt"):
            # Direct text screenplay
            dest = os.path.join(upload_dir, file.filename)
            with open(dest, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            extracted_txt_count += 1

    if extracted_txt_count == 0:
        raise HTTPException(status_code=400, detail="No valid .txt screenplay files found in upload.")

    # Run the full ranking pipeline on this newly uploaded show
    ranked_promos = process_show(data_dir=upload_dir, api_key=api_key)
    try:
        export_outputs(ranked_promos)
    except Exception:
        pass

    return {
        "episodes_processed": extracted_txt_count,
        "promos_count": len(ranked_promos),
        "promos": ranked_promos[:50]  # return top 50
    }

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Kuku Promo Studio API is running</h1>")

@app.get("/index.html", response_class=HTMLResponse)
def serve_index_html():
    return serve_index()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.py:app", host="0.0.0.0", port=8000, reload=True)
