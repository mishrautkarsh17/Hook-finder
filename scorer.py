"""
scorer.py - Hybrid scoring engine for promo candidates.
Uses standard HTTP requests to generativelanguage.googleapis.com (no fragile SDK imports).
Combines:
1. Local heuristic/NLP scoring (instant, free, reproducible).
2. LLM deep evaluation (Gemini models) via direct REST API with automated local caching.
3. Automated fallback to NLP rationale generator if no API key is provided or if quota/network is limited.
"""

import os
import json
import hashlib
import requests
from typing import Dict, List, Any, Optional

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def candidate_to_prompt_text(candidate: Dict[str, Any]) -> str:
    """Formats candidate blocks into readable screenplay format for LLM evaluation."""
    lines = []
    lines.append(f"Episode: {candidate['episode_name']}")
    lines.append(f"Promo Duration: {candidate['total_duration']} seconds")
    for seg in candidate["segments"]:
        lines.append(f"Segment: {seg['start_ts']} to {seg['end_ts']} ({seg['duration']}s)")
    lines.append("\n--- PROMO SCENE SCRIPT ---")
    for b in candidate["blocks"]:
        time_str = f"[{b['start_ts']} - {b['end_ts']}]"
        if b["type"] == "DIALOGUE":
            emo_str = f" ({b['emotion']})" if b["emotion"] else ""
            lines.append(f"{time_str} {b['speaker']}{emo_str}: \"{b['content']}\"")
        else:
            lines.append(f"{time_str} [{b['type']}] {b['content']}")
    return "\n".join(lines)

def get_cache_key(candidate: Dict[str, Any]) -> str:
    text = candidate_to_prompt_text(candidate)
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def score_with_nlp(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic rule-based NLP scoring and explanation generator.
    Always available, zero cost, completely offline.
    """
    blocks = candidate["blocks"]
    start_sec = candidate["segments"][0]["start_sec"]
    end_sec = candidate["segments"][-1]["end_sec"]

    # Analyze first 3.5 seconds for Hook
    hook_blocks = [b for b in blocks if b["start_sec"] <= start_sec + 3.5]
    hook_desc_parts = []
    hook_score = min(10, max(4, candidate.get("hook_raw_score", 0) + 4))

    for b in hook_blocks:
        if b["type"] == "DIALOGUE":
            hook_desc_parts.append(f'{b["speaker"]} says: "{b["content"]}"')
        elif b["type"] == "ACTION":
            hook_desc_parts.append(b["content"])
        elif b["type"] == "CAMERA":
            hook_desc_parts.append(b["content"])

    hook_desc = " | ".join(hook_desc_parts[:2]) if hook_desc_parts else "Immediate dramatic opening action"

    # Analyze last 4.0 seconds for Cliffhanger
    cliff_blocks = [b for b in blocks if b["end_sec"] >= end_sec - 4.0]
    cliff_desc_parts = []
    cliff_score = min(10, max(4, candidate.get("cliff_raw_score", 0) + 4))

    for b in cliff_blocks:
        if b["type"] == "DIALOGUE":
            cliff_desc_parts.append(f'{b["speaker"]} leaves unanswered: "{b["content"]}"')
        elif b["type"] in ["ACTION", "SOUND FX", "CAMERA"]:
            cliff_desc_parts.append(b["content"])

    cliff_desc = " | ".join(cliff_desc_parts[-2:]) if cliff_desc_parts else "Cuts at the height of emotional tension"

    # Standalone clarity estimation (presence of recognizable stakes/relationships)
    speakers = list(set([b["speaker"] for b in blocks if b["type"] == "DIALOGUE" and b["speaker"]]))
    dialogue_count = len([b for b in blocks if b["type"] == "DIALOGUE"])
    standalone_score = 7.0
    if len(speakers) >= 2 and dialogue_count >= 3:
        standalone_score = 8.5
    elif len(speakers) == 1:
        standalone_score = 6.0

    # Composite score: Hook (40%), Cliffhanger (40%), Standalone clarity (20%)
    overall_score = round(0.40 * hook_score + 0.40 * cliff_score + 0.20 * standalone_score, 2)

    why_it_works = (
        f"Opens immediately with high visual/dialogue stakes ({hook_desc[:65]}...) "
        f"and cuts abruptly before the conflict resolves ({cliff_desc[:65]}...), driving high watch-completion."
    )

    return {
        "source": "NLP_ENGINE",
        "hook_score": hook_score,
        "cliffhanger_score": cliff_score,
        "standalone_score": standalone_score,
        "overall_score": overall_score,
        "hook": hook_desc,
        "hook_reasoning": f"Opens on immediate high-contrast emotional action ({hook_desc[:60]}...), breaking feed scroll patterns within the critical 3-second attention window.",
        "cliffhanger": cliff_desc,
        "cliffhanger_reasoning": f"Abruptly severs narrative flow right at peak confrontation ({cliff_desc[:60]}...), leaving an intense psychological curiosity gap.",
        "why_it_works": why_it_works
    }

def score_with_gemini_rest(candidate: Dict[str, Any], api_key: str) -> Optional[Dict[str, Any]]:
    """
    Calls Gemini API via direct REST HTTP (clean, no library conflicts).
    """
    script_text = candidate_to_prompt_text(candidate)
    prompt = f"""You are an expert social media editor for viral vertical microdramas (like ReelShort, DramaBox, Kuku TV).
Analyze this candidate 20-60 second promo clip taken from a microdrama episode.

{script_text}

Evaluate this promo against the three strict criteria:
1. HOOK (first 3 seconds): Does it grab a scrolling viewer with a slap, shocking reveal, betrayal, or intense line?
2. CLIFFHANGER: Does it cut at an agonizingly unresolved moment so the viewer MUST click to see what happens next?
3. STANDALONE CLARITY: Does the conflict make immediate sense to someone who has never watched the series before?

Respond with a valid JSON object only (no markdown, no backticks, no wrap):
{{
  "hook_score": <int 1-10>,
  "cliffhanger_score": <int 1-10>,
  "standalone_score": <int 1-10>,
  "overall_score": <float 1-10>,
  "hook": "<what specifically happens in the first 3 seconds>",
  "hook_reasoning": "<1-2 sentences explaining WHY this specific 0-3s opening stops a scrolling user on TikTok/Reels>",
  "cliffhanger": "<what specifically happens at the exact cut-off moment>",
  "cliffhanger_reasoning": "<1-2 sentences explaining WHY this cutoff creates severe psychological tension and forces the viewer to click>",
  "why_it_works": "<one overarching line on why this promo will convert scrolling social media users into paying viewers>"
}}
"""
    models_to_try = [
        "gemini-3.1-flash-lite-preview",
        "gemini-3-flash-preview",
        "gemini-2.0-flash",
        "gemini-flash-latest"
    ]
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=12)
            if res.status_code == 200:
                data = res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Clean possible markdown wrap
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                parsed_json = json.loads(text.strip())
                parsed_json["source"] = f"GEMINI_API ({model})"
                return parsed_json
        except Exception:
            continue

    return None

def score_candidate(candidate: Dict[str, Any], api_key: Optional[str] = None, bypass_cache: bool = False) -> Dict[str, Any]:
    """
    Scores a candidate promo.
    If api_key is provided, it prioritizes calling the live LLM API.
    """
    cache_key = get_cache_key(candidate)
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")

    # 1. Check cache (only accept cache if bypass_cache is False and it's from API when API requested)
    resolved_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if not bypass_cache and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                # If user provided API key, don't use stale NLP cache
                if resolved_key and "NLP" in cached_data.get("source", ""):
                    pass
                else:
                    return cached_data
        except Exception:
            pass

    # 2. Try REST LLM if API key provided
    result = None
    if resolved_key:
        result = score_with_gemini_rest(candidate, resolved_key)

    # 3. Fallback to NLP engine only if LLM failed
    if not result:
        result = score_with_nlp(candidate)

    # 4. Save to cache
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result

if __name__ == "__main__":
    from parser import parse_screenplay
    from candidate_generator import generate_episode_candidates

    ep1 = parse_screenplay(r"data\episode-001-Episode 1671703.txt")
    cands = generate_episode_candidates(ep1)

    print(f"Scoring top candidate for Episode 1 via REST/NLP...")
    score_data = score_candidate(cands[0])
    print("\nResult:")
    print(json.dumps(score_data, indent=2))
