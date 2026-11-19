"""
parser.py - Robust screenplay parser for Kuku microdrama screenplays.
Extracts episode metadata, scenes, and micro-blocks (camera, action, dialogue, sound fx)
with normalized floating-point timestamps (seconds).
"""

import os
import re
import glob
from typing import Dict, List, Any, Optional

def parse_timestamp_to_seconds(ts_str: str) -> float:
    """
    Converts timestamps like '01:15.50' or '00:04.80' or '01:15' to seconds (float).
    """
    ts_str = ts_str.strip().strip("()")
    parts = ts_str.split(":")
    if len(parts) == 2:
        minutes = float(parts[0])
        seconds = float(parts[1])
        return round(minutes * 60 + seconds, 2)
    elif len(parts) == 3:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return round(hours * 3600 + minutes * 60 + seconds, 2)
    try:
        return round(float(ts_str), 2)
    except ValueError:
        return 0.0

def format_seconds_to_timestamp(seconds: float) -> str:
    """Formats float seconds back to MM:SS.ss string."""
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins:02d}:{secs:05.2f}"

def parse_screenplay(file_path: str) -> Dict[str, Any]:
    """
    Parses a single screenplay file into structured data.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read().replace("\r\n", "\n")

    # 1. Metadata
    ep_num_match = re.search(r"EPISODE NUMBER:\s*(.*)", content)
    logline_match = re.search(r"EPISODE LOGLINE:\s*(.*)", content)
    notes_match = re.search(r"CONTINUITY NOTES:\s*(.*?)(?=--- SCRIPT START ---|\Z)", content, re.DOTALL)

    episode_name = ep_num_match.group(1).strip() if ep_num_match else os.path.basename(file_path)
    logline = logline_match.group(1).strip() if logline_match else ""
    continuity_notes = notes_match.group(1).strip() if notes_match else ""

    # 2. Extract Script Body
    script_body = content
    if "--- SCRIPT START ---" in content:
        script_body = content.split("--- SCRIPT START ---")[1]
    if "--- SCRIPT END ---" in script_body:
        script_body = script_body.split("--- SCRIPT END ---")[0]

    # 3. Find all block headers: **TAG:**\nStart: (00:00.00) | End: (00:04.80)
    header_pattern = re.compile(
        r"\*\*([^*]+)\*\*\s*\nStart:\s*\(([0-9:.]+)\)\s*\|\s*End:\s*\(([0-9:.]+)\)"
    )

    headers = list(header_pattern.finditer(script_body))
    blocks: List[Dict[str, Any]] = []

    for i, h in enumerate(headers):
        tag_raw = h.group(1).strip().rstrip(":")
        start_ts = h.group(2).strip()
        end_ts = h.group(3).strip()

        start_sec = parse_timestamp_to_seconds(start_ts)
        end_sec = parse_timestamp_to_seconds(end_ts)

        # Body is text between end of current header and start of next header
        content_start = h.end()
        content_end = headers[i + 1].start() if i + 1 < len(headers) else len(script_body)
        raw_body = script_body[content_start:content_end].strip()

        # Clean any trailing SCENE headings or dividers
        body_lines = [
            line for line in raw_body.splitlines()
            if not line.startswith("SCENE ") and not line.startswith("Scene heading:")
            and not line.startswith("Scene start:") and not line.startswith("Scene end:")
            and not line.startswith("Actions and dialogue:")
        ]
        body_text = "\n".join(body_lines).strip()

        # Categorize tag
        tag_type = "DIALOGUE"
        speaker = ""
        emotion = ""

        upper_tag = tag_raw.upper()
        if upper_tag in ["CAMERA", "ACTION", "SOUND FX", "SFX", "MUSIC"]:
            tag_type = upper_tag
        else:
            # Character dialogue, e.g. "MATRIARCH (Cold, Commanding)" or "THE FORMER GROOM"
            speaker_match = re.match(r"^([^(]+)(?:\(([^)]+)\))?", tag_raw)
            if speaker_match:
                speaker = speaker_match.group(1).strip()
                emotion = speaker_match.group(2).strip() if speaker_match.group(2) else ""
            else:
                speaker = tag_raw

        blocks.append({
            "block_id": i + 1,
            "tag_raw": tag_raw,
            "type": tag_type,
            "speaker": speaker,
            "emotion": emotion,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duration": round(end_sec - start_sec, 2),
            "content": body_text,
            "start_ts": start_ts,
            "end_ts": end_ts
        })

    # Sort blocks
    blocks.sort(key=lambda b: (b["start_sec"], b["end_sec"]))
    total_duration = blocks[-1]["end_sec"] if blocks else 0.0

    return {
        "file_path": file_path,
        "episode_name": episode_name,
        "logline": logline,
        "continuity_notes": continuity_notes,
        "total_duration": total_duration,
        "total_duration_ts": format_seconds_to_timestamp(total_duration),
        "total_blocks": len(blocks),
        "blocks": blocks
    }

def parse_all_episodes(data_dir: str = "data") -> List[Dict[str, Any]]:
    """Parses all screenplays in directory ordered by episode number."""
    files = glob.glob(os.path.join(data_dir, "*.txt"))
    # Sort files naturally
    def extract_ep_num(fpath):
        m = re.search(r"episode-(\d+)", os.path.basename(fpath))
        return int(m.group(1)) if m else 999
    files.sort(key=extract_ep_num)

    episodes = [parse_screenplay(f) for f in files]
    return episodes

if __name__ == "__main__":
    episodes = parse_all_episodes("data")
    print(f"Parsed {len(episodes)} episodes successfully!")
    ep1 = episodes[0]
    print(f"\nEpisode 1: {ep1['episode_name']}")
    print(f"Logline: {ep1['logline']}")
    print(f"Duration: {ep1['total_duration_ts']} ({ep1['total_duration']}s)")
    print(f"Total blocks: {ep1['total_blocks']}")
    print("\nFirst block:")
    print(" ", ep1["blocks"][0])
    print("\nLast block:")
    print(" ", ep1["blocks"][-1])
