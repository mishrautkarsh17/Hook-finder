"""
server.py - Production-ready FastAPI + React web server for Kuku Promo Studio.
Zero Streamlit, pure React + Tailwind frontend with REST API endpoints.
"""

import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from parser import parse_screenplay
from candidate_generator import generate_episode_candidates
from scorer import score_candidate

app = FastAPI(title="Kuku Promo Studio API")

# Serve static directory (contains React index.html)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
MASTER_JSON_PATH = os.path.join(os.path.dirname(__file__), "outputs", "promos_master.json")

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

    os.makedirs("cache", exist_ok=True)
    temp_path = os.path.join("cache", "react_temp_ep.txt")
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
            "cliffhanger": score_res["cliffhanger"],
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

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.py:app", host="0.0.0.0", port=8000, reload=True)
