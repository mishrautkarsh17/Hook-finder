"""
candidate_generator.py - Generates viable 20 to 60-second promo candidate segments
anchored on high-potential hooks (entry points) and cliffhangers (exit cutoffs).
Supports:
1. Single-stretch continuous promos within an episode.
2. Multi-segment promos (e.g., cross-scene or cross-episode teaser sequences).
"""

import re
from typing import Dict, List, Any, Tuple
from parser import format_seconds_to_timestamp

# Keywords signaling strong viral hooks (visual or auditory punch in first 3 seconds)
HOOK_KEYWORDS = [
    # Physical/Visual drama
    r"\bslap\b", r"\bslaps\b", r"\bgrab\b", r"\bshove\b", r"\bpush\b", r"\btear\b", r"\brip\b",
    r"\bchoke\b", r"\bknife\b", r"\bgown\b", r"\baltar\b", r"\bbetray\b", r"\bhumiliat\b",
    # Shocking dialogue markers
    r"\bwho are you\b", r"\bhow dare you\b", r"\byou disgust me\b", r"\bnever\b",
    r"\billegitimate\b", r"\bbastard\b", r"\bwhore\b", r"\blier\b", r"\bliar\b",
    r"\bcannot marry\b", r"\bturn around\b", r"\bpregnant\b", r"\bkill\b", r"\bdead\b",
    r"\bdivorce\b", r"\bworthless\b", r"\bplainness\b", r"\blow value\b", r"\bsecret\b",
    # Camera / Sound cues
    r"\bclose-up\b", r"\bcrash\b", r"\bgasp\b", r"\bscreams?\b", r"\bswells\b", r"\bdrone\b"
]

# Keywords signaling unresolved cliffhangers (cutoffs that demand knowing what happens next)
CLIFFHANGER_KEYWORDS = [
    r"\bcut to black\b", r"\bswells to an ominous\b", r"\bcliffhanger\b", r"\bfreeze\b",
    r"\bpause\b", r"\bhesitat\b", r"\bunanswered\b", r"\bgasp\b", r"\bwide-eyed\b",
    r"\bdefiance\b", r"\bclenches\b", r"\bshock\b", r"\bwh\?|\bwhat\?|\bwho\?|\bhow\?",
    r"\bwhisper\b", r"\bdoor slams\b", r"\bfootsteps\b", r"\bsilence\b", r"\bconfront\b"
]

def text_matches_any(text: str, patterns: List[str]) -> bool:
    lower = text.lower()
    for p in patterns:
        if re.search(p, lower):
            return True
    return False

def count_keyword_matches(text: str, patterns: List[str]) -> int:
    lower = text.lower()
    matches = 0
    for p in patterns:
        matches += len(re.findall(p, lower))
    return matches

def generate_episode_candidates(episode: Dict[str, Any], min_dur: float = 20.0, max_dur: float = 60.0) -> List[Dict[str, Any]]:
    """
    Identifies candidate 20-60s continuous promo windows for a single episode.
    """
    blocks = episode["blocks"]
    n = len(blocks)
    candidates = []

    # Identify candidate start indices (blocks that make punchy openings)
    # Good hooks happen within the first 3 seconds of the promo window
    for i in range(n):
        start_block = blocks[i]
        start_time = start_block["start_sec"]

        # Examine content of the first ~3-5 seconds starting from start_block
        hook_window_blocks = [
            b for b in blocks[i:] if b["start_sec"] <= start_time + 4.0
        ]
        hook_text = " ".join([b["content"] + " " + b["tag_raw"] for b in hook_window_blocks])
        hook_score = count_keyword_matches(hook_text, HOOK_KEYWORDS)

        # Dialogues with strong emotion or dramatic actions make great hooks
        for b in hook_window_blocks:
            if b["type"] == "DIALOGUE" and b["emotion"]:
                hook_score += 1
            if b["type"] == "ACTION" and any(k in b["content"].lower() for k in ["tears", "clench", "gasp", "stops", "slap"]):
                hook_score += 2

        # If it has some hook potential or is a natural scene beginning
        if hook_score == 0 and i > 0 and (start_time - blocks[i-1]["end_sec"]) < 1.0:
            # Skip uninteresting mid-sentence starting points
            continue

        # Look for valid endpoints j where duration is in [min_dur, max_dur]
        for j in range(i, n):
            end_block = blocks[j]
            end_time = end_block["end_sec"]
            duration = end_time - start_time

            if duration < min_dur:
                continue
            if duration > max_dur:
                break

            # Calculate cliffhanger potential of the ending block(s)
            cliff_window_blocks = [
                b for b in blocks[i:j+1] if b["end_sec"] >= end_time - 3.5
            ]
            cliff_text = " ".join([b["content"] + " " + b["tag_raw"] for b in cliff_window_blocks])
            cliff_score = count_keyword_matches(cliff_text, CLIFFHANGER_KEYWORDS)

            # Extra cliffhanger points if ending on a question or dramatic action
            for b in cliff_window_blocks:
                if "?" in b["content"]:
                    cliff_score += 2
                if "cut to black" in b["content"].lower() or "ominous" in b["content"].lower():
                    cliff_score += 3
                if b["type"] == "ACTION" and any(k in b["content"].lower() for k in ["defiance", "fury", "frozen", "shock"]):
                    cliff_score += 2

            # Candidate filter: only keep if there's at least modest hook & cliffhanger signal
            if hook_score > 0 or cliff_score > 0:
                raw_dialogues = [b for b in blocks[i:j+1] if b["type"] == "DIALOGUE"]
                # A good promo usually has at least some dialogue or speech
                if len(raw_dialogues) >= 1:
                    candidates.append({
                        "episode_name": episode["episode_name"],
                        "file_path": episode["file_path"],
                        "segments": [{
                            "episode": episode["episode_name"],
                            "start_sec": start_time,
                            "end_sec": end_time,
                            "start_ts": format_seconds_to_timestamp(start_time),
                            "end_ts": format_seconds_to_timestamp(end_time),
                            "duration": round(duration, 2)
                        }],
                        "total_duration": round(duration, 2),
                        "start_block_idx": i,
                        "end_block_idx": j,
                        "hook_raw_score": hook_score,
                        "cliff_raw_score": cliff_score,
                        "blocks": blocks[i:j+1]
                    })

    # Deduplicate overlapping candidates: keep highest combined raw score in sliding windows
    candidates.sort(key=lambda c: (c["hook_raw_score"] + c["cliff_raw_score"]), reverse=True)
    selected = []
    for cand in candidates:
        cand_start = cand["segments"][0]["start_sec"]
        cand_end = cand["segments"][0]["end_sec"]
        # Check overlap with already selected
        overlap = False
        for s in selected:
            s_start = s["segments"][0]["start_sec"]
            s_end = s["segments"][0]["end_sec"]
            # Overlap if intersection is > 50%
            inter = max(0, min(cand_end, s_end) - max(cand_start, s_start))
            if inter > 12.0:
                overlap = True
                break
        if not overlap:
            selected.append(cand)
        if len(selected) >= 5:  # Keep top 5 diverse candidates per episode
            break

    return selected

def generate_cross_episode_candidates(ep1: Dict[str, Any], ep2: Dict[str, Any], min_dur: float = 20.0, max_dur: float = 60.0) -> List[Dict[str, Any]]:
    """
    Creates high-impact 2-segment cross-episode promo candidates (e.g. cliffhanger of Ep 1 + confrontation in Ep 2).
    """
    # Segment A: Last 12-25s of ep1
    ep1_blocks = ep1["blocks"]
    ep2_blocks = ep2["blocks"]
    if not ep1_blocks or not ep2_blocks:
        return []

    ep1_end = ep1_blocks[-1]["end_sec"]
    # Look for last 15-25s of ep1
    seg1_blocks = [b for b in ep1_blocks if b["end_sec"] >= ep1_end - 22.0]
    if not seg1_blocks:
        return []

    seg1_start = seg1_blocks[0]["start_sec"]
    seg1_dur = ep1_end - seg1_start

    # Segment B: Opening 15-30s of ep2
    seg2_blocks = [b for b in ep2_blocks if b["end_sec"] <= 28.0]
    if not seg2_blocks:
        return []
    seg2_end = seg2_blocks[-1]["end_sec"]
    seg2_dur = seg2_end

    total_dur = seg1_dur + seg2_dur
    if min_dur <= total_dur <= max_dur:
        combined_blocks = seg1_blocks + seg2_blocks
        return [{
            "episode_name": f"{ep1['episode_name']} + {ep2['episode_name']}",
            "file_path": ep1["file_path"],
            "segments": [
                {
                    "episode": ep1["episode_name"],
                    "start_sec": seg1_start,
                    "end_sec": ep1_end,
                    "start_ts": format_seconds_to_timestamp(seg1_start),
                    "end_ts": format_seconds_to_timestamp(ep1_end),
                    "duration": round(seg1_dur, 2)
                },
                {
                    "episode": ep2["episode_name"],
                    "start_sec": 0.0,
                    "end_sec": seg2_end,
                    "start_ts": format_seconds_to_timestamp(0.0),
                    "end_ts": format_seconds_to_timestamp(seg2_end),
                    "duration": round(seg2_dur, 2)
                }
            ],
            "total_duration": round(total_dur, 2),
            "hook_raw_score": 5,
            "cliff_raw_score": 5,
            "blocks": combined_blocks,
            "is_cross_episode": True
        }]
    return []

if __name__ == "__main__":
    from parser import parse_screenplay
    ep1 = parse_screenplay(r"data\episode-001-Episode 1671703.txt")
    cands = generate_episode_candidates(ep1)
    print(f"Generated {len(cands)} promo candidates for Episode 1:")
    for idx, c in enumerate(cands):
        seg = c["segments"][0]
        print(f"\nCandidate {idx+1}: [{seg['start_ts']} - {seg['end_ts']}] ({c['total_duration']}s)")
        print(f"  Hook Raw Score: {c['hook_raw_score']} | Cliffhanger Raw Score: {c['cliff_raw_score']}")
        print(f"  Blocks count: {len(c['blocks'])}")
        # Print first dialogue and last action
        for b in c['blocks'][:2]:
            print(f"    Opening: [{b['tag_raw']}] {b['content'][:50]}...")
        for b in c['blocks'][-2:]:
            print(f"    Ending:  [{b['tag_raw']}] {b['content'][:50]}...")
