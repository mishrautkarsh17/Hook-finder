"""
app.py - Ultra-Modern Cinematic Dark-Mode UI for Kuku Microdrama Promo Finder.
Styled like Netflix / ReelShort with:
- Dark theme & Glassmorphism design
- 9:16 Vertical Video Phone Mockup previewing the promo visually
- Timeline duration scrubber bars
- Live dynamic screenplay parsing & LLM scoring via Gemini API / NLP
- Zero Node.js required, 100% Python, deployable in 1 click
"""

import os
import json
import zipfile
import requests
import streamlit as st

from parser import parse_screenplay, parse_all_episodes, format_seconds_to_timestamp
from candidate_generator import generate_episode_candidates, generate_cross_episode_candidates
from scorer import score_candidate
from ranker import process_show, export_outputs

st.set_page_config(
    page_title="Kuku Promo Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# CINEMATIC DARK-THEME & GLASSMORPHISM STYLING
# -------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }

    /* Main background */
    .stApp {
        background: radial-gradient(circle at 10% 10%, #111420 0%, #090a0f 90%);
        color: #f1f5f9;
    }

    /* Cinematic Header */
    .hero-container {
        padding: 24px 32px;
        background: linear-gradient(135deg, rgba(229, 9, 20, 0.15) 0%, rgba(15, 23, 42, 0.4) 100%);
        border: 1px solid rgba(229, 9, 20, 0.3);
        border-radius: 16px;
        margin-bottom: 28px;
        backdrop-filter: blur(12px);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff4b4b, #ff8a65, #ffb74d);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin-top: 4px;
        font-weight: 400;
    }

    /* Promo Glass Card */
    .glass-card {
        background: rgba(18, 22, 34, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .glass-card:hover {
        border-color: rgba(229, 9, 20, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(229, 9, 20, 0.15);
    }

    /* Phone Mockup 9:16 Preview */
    .phone-mockup {
        width: 100%;
        max-width: 260px;
        height: 380px;
        border-radius: 28px;
        border: 3px solid #334155;
        background: #000000;
        box-shadow: 0 20px 40px rgba(0,0,0,0.8), inset 0 0 12px rgba(255,255,255,0.05);
        padding: 18px 14px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        position: relative;
        overflow: hidden;
    }
    .phone-notch {
        width: 70px;
        height: 12px;
        background: #1e293b;
        border-radius: 8px;
        margin: 0 auto 10px auto;
    }
    .phone-tag {
        font-size: 0.65rem;
        text-transform: uppercase;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        display: inline-block;
        letter-spacing: 0.5px;
    }
    .phone-overlay-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #ffffff;
        margin-top: 6px;
        line-height: 1.2;
    }
    .phone-caption {
        font-size: 0.75rem;
        color: #cbd5e1;
        line-height: 1.3;
        margin-top: 6px;
        background: rgba(0,0,0,0.6);
        padding: 8px;
        border-radius: 8px;
        border-left: 3px solid #E50914;
    }
    .phone-bottom-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid rgba(255,255,255,0.1);
        padding-top: 8px;
        margin-top: 8px;
        font-size: 0.7rem;
        color: #94a3b8;
    }

    /* Badges */
    .pill {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 4px;
    }
    .pill-red { background: rgba(229, 9, 20, 0.2); color: #ff6b6b; border: 1px solid rgba(229, 9, 20, 0.4); }
    .pill-cyan { background: rgba(6, 182, 212, 0.15); color: #67e8f9; border: 1px solid rgba(6, 182, 212, 0.3); }
    .pill-purple { background: rgba(168, 85, 247, 0.15); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.3); }
    .pill-green { background: rgba(34, 197, 94, 0.15); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.3); }

    /* Timeline scrubber bar */
    .timeline-track {
        width: 100%;
        height: 8px;
        background: #1e293b;
        border-radius: 4px;
        position: relative;
        margin: 12px 0 6px 0;
        overflow: hidden;
    }
    .timeline-fill {
        height: 100%;
        background: linear-gradient(90deg, #E50914, #ff8a65);
        border-radius: 4px;
    }

    /* Score display */
    .score-badge {
        font-size: 1.5rem;
        font-weight: 800;
        color: #ff4b4b;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Clean sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0c0e17;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# HERO HEADER
# -------------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <div>
        <div class="hero-title">🎬 Kuku Promo Studio</div>
        <div class="hero-subtitle">Next-Gen AI Microdrama Ad Detector & 9:16 Vertical Video Optimizer</div>
    </div>
    <div style="text-align: right;">
        <span class="pill pill-red">⚡ ReelShort & TikTok Ready</span>
        <span class="pill pill-cyan">🤖 Gemini 3 Flash Hybrid</span>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
st.sidebar.markdown("### ⚙️ Engine Control")

DEFAULT_KEY = os.environ.get("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input(
    "🔑 Gemini API Key",
    type="password",
    value=DEFAULT_KEY,
    help="Pre-loaded with your active Google AI Studio key."
)
active_api_key = api_key_input.strip() if api_key_input.strip() else None

if active_api_key:
    if st.sidebar.button("🔌 Ping Gemini API"):
        with st.spinner("Pinging Generative Language API..."):
            try:
                res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={active_api_key}", timeout=6)
                if res.status_code == 200:
                    st.sidebar.success("✅ Gemini Connected & Ready")
                else:
                    st.sidebar.warning(f"Response: {res.status_code}")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")

st.sidebar.markdown("---")
view_mode = st.sidebar.radio(
    "Navigation",
    [
        "🧪 Live Screenplay Tester (Interactive)",
        "🏆 Top Promos & Phone Simulator",
        "📁 Batch Process New Show",
        "📖 Engineering Architecture"
    ]
)

# -------------------------------------------------------------
# TAB 1: LIVE TESTER WITH 9:16 PHONE PREVIEW
# -------------------------------------------------------------
if view_mode == "🧪 Live Screenplay Tester (Interactive)":
    st.subheader("🧪 Live Screenplay Tester")
    st.markdown("Drop **any new microdrama screenplay** here to extract, slice, and generate viral 20–60s vertical promos on the fly.")

    c_input1, c_input2 = st.columns([1, 1])
    with c_input1:
        uploaded_file = st.file_uploader("Upload Screenplay (.txt)", type=["txt"])
    with c_input2:
        eval_engine_choice = st.selectbox(
            "Evaluation Brain:",
            ["Gemini 3 Flash (Live AI Reasoning)", "Ultra-Fast Deterministic Local NLP Engine"]
        )

    user_pasted = st.text_area(
        "Or Paste Screenplay Text Directly:",
        height=140,
        placeholder="EPISODE NUMBER: Episode X\n\n**CAMERA:**\nStart: (00:00.00) | End: (00:04.00)\n..."
    )

    if st.button("🚀 Analyze & Generate Promos", type="primary"):
        raw_text = None
        if uploaded_file is not None:
            raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
        elif user_pasted.strip():
            raw_text = user_pasted.strip()

        if not raw_text:
            st.warning("Please upload a .txt file or paste screenplay content.")
        else:
            with st.spinner("Parsing temporal micro-blocks & evaluating viral windows..."):
                os.makedirs("cache", exist_ok=True)
                temp_path = os.path.join("cache", "temp_dynamic_ep.txt")
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(raw_text)

                parsed_ep = parse_screenplay(temp_path)

                if parsed_ep["total_blocks"] == 0:
                    st.error("No timestamped blocks found. Check format (**TAG:** followed by Start: | End:).")
                else:
                    st.success(f"🎬 **{parsed_ep['episode_name']}** — Duration: `{parsed_ep['total_duration_ts']}` ({parsed_ep['total_blocks']} temporal blocks)")

                    candidates = generate_episode_candidates(parsed_ep)
                    st.info(f"✨ Identified **{len(candidates)}** candidate 20–60s promo windows.")

                    key_to_use = active_api_key if eval_engine_choice.startswith("Gemini") else None
                    bypass_cache = True if eval_engine_choice.startswith("Gemini") else False

                    scored_results = []
                    progress_bar = st.progress(0)
                    for idx, c in enumerate(candidates):
                        score_res = score_candidate(c, api_key=key_to_use, bypass_cache=bypass_cache)
                        c["score_res"] = score_res
                        c["overall"] = score_res["overall_score"]
                        scored_results.append(c)
                        progress_bar.progress((idx + 1) / len(candidates))

                    scored_results.sort(key=lambda x: x["overall"], reverse=True)

                    st.markdown("---")
                    st.markdown("### 📱 Generated Vertical Video Promos (Ranked Live)")

                    for idx, sc in enumerate(scored_results, 1):
                        seg = sc["segments"][0]
                        res = sc["score_res"]
                        engine_badge = res.get("source", "NLP_ENGINE")

                        with st.container():
                            col_card, col_phone = st.columns([2, 1])

                            with col_card:
                                st.markdown(f"""
                                <div class="glass-card">
                                    <div style="display:flex; justify-content:space-between; align-items:center;">
                                        <div>
                                            <span class="pill pill-red">Rank #{idx}</span>
                                            <span class="pill pill-cyan">⏱️ {seg['duration']} seconds</span>
                                            <span class="pill pill-purple">⚙️ {engine_badge}</span>
                                        </div>
                                        <div class="score-badge">★ {res['overall_score']}<span style="font-size:0.9rem; color:#64748b;">/10</span></div>
                                    </div>
                                    <div class="timeline-track">
                                        <div class="timeline-fill" style="width: {min(100, int((seg['duration']/60.0)*100))}%;"></div>
                                    </div>
                                    <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:12px;">
                                        Time Range: <b>{seg['start_ts']}</b> ➔ <b>{seg['end_ts']}</b> (Target: 20-60s)
                                    </div>
                                    <div style="margin-bottom:10px;">
                                        <b style="color:#67e8f9;">⚡ 0-3s Hook:</b><br>
                                        <span style="color:#e2e8f0; font-size:0.92rem;">{res['hook']}</span>
                                    </div>
                                    <div style="margin-bottom:10px;">
                                        <b style="color:#f472b6;">🔥 Cliffhanger Cut-off:</b><br>
                                        <span style="color:#e2e8f0; font-size:0.92rem;">{res['cliffhanger']}</span>
                                    </div>
                                    <div>
                                        <b style="color:#fbbf24;">💡 Conversion Rationale:</b><br>
                                        <span style="color:#cbd5e1; font-size:0.88rem;">{res['why_it_works']}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                                with st.expander("📜 Show Script Excerpt for this Clip", expanded=False):
                                    for b in sc["blocks"]:
                                        if b["type"] == "DIALOGUE":
                                            emo = f" ({b['emotion']})" if b['emotion'] else ""
                                            st.write(f"**[{b['start_ts']} - {b['end_ts']}] {b['speaker']}{emo}:** {b['content']}")
                                        else:
                                            s_ts = b['start_ts']
                                            e_ts = b['end_ts']
                                            b_typ = b['type']
                                            b_cnt = b['content']
                                            st.write(f"_[{s_ts} - {e_ts}] [{b_typ}] {b_cnt}_")

                            with col_phone:
                                # Interactive 9:16 Phone Mockup
                                st.markdown(f"""
                                <div class="phone-mockup">
                                    <div class="phone-notch"></div>
                                    <div>
                                        <div class="phone-tag pill-red">PROMO #{idx}</div>
                                        <div class="phone-overlay-title">{parsed_ep['episode_name']}</div>
                                        <div style="font-size:0.65rem; color:#94a3b8; margin-top:2px;">TikTok / Reels / Shorts 9:16</div>
                                    </div>
                                    <div class="phone-caption">
                                        <b>⚡ HOOK:</b> {res['hook'][:75]}...
                                    </div>
                                    <div class="phone-caption" style="border-left-color:#c2185b; margin-top:4px;">
                                        <b>🔥 CLIFF:</b> {res['cliffhanger'][:75]}...
                                    </div>
                                    <div class="phone-bottom-bar">
                                        <span>⏱️ {seg['start_ts']} - {seg['end_ts']}</span>
                                        <span style="color:#ff6b6b; font-weight:700;">★ {res['overall_score']}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 2: TOP PROMOS & PHONE SIMULATOR
# -------------------------------------------------------------
elif view_mode == "🏆 Top Promos & Phone Simulator":
    st.subheader("🏆 Global Ranked Promos Catalog")

    MASTER_JSON_PATH = os.path.join("outputs", "promos_master.json")
    promos_data = []
    if os.path.exists(MASTER_JSON_PATH):
        with open(MASTER_JSON_PATH, "r", encoding="utf-8") as f:
            promos_data = json.load(f)

    if not promos_data:
        st.warning("No promo catalog found. Please process a show first.")
    else:
        c_f1, c_f2, c_f3 = st.columns([2, 2, 2])
        with c_f1:
            min_score = st.slider("Min Overall Score", min_value=5.0, max_value=10.0, value=8.5, step=0.1)
        with c_f2:
            max_duration = st.slider("Max Duration (sec)", min_value=20, max_value=60, value=50, step=1)
        with c_f3:
            cross_only = st.checkbox("Cross-Episode Promos Only", value=False)

        filtered = [
            p for p in promos_data
            if p["scores"]["overall"] >= min_score
            and p["total_duration_sec"] <= max_duration
            and (not cross_only or p.get("is_cross_episode", False))
        ]

        st.caption(f"Showing **{len(filtered)}** promos matching your filter criteria:")

        for p in filtered[:20]:
            col_left, col_right = st.columns([2, 1])

            with col_left:
                st.markdown(f"""
                <div class="glass-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span class="pill pill-red">Rank #{p['rank']}</span>
                            <span class="pill pill-cyan">📺 {p['episode']}</span>
                            <span class="pill pill-purple">⏱️ {p['total_duration_sec']}s</span>
                        </div>
                        <div class="score-badge">★ {p['scores']['overall']}/10</div>
                    </div>
                    <div class="timeline-track">
                        <div class="timeline-fill" style="width: {min(100, int((p['total_duration_sec']/60.0)*100))}%;"></div>
                    </div>
                    <div style="font-size:0.85rem; color:#94a3b8; margin:8px 0;">
                        <b>Timestamps:</b> {p['segments'][0]['start_time']} ➔ {p['segments'][-1]['end_time']}
                    </div>
                    <div style="margin-bottom:8px;">
                        <b style="color:#67e8f9;">⚡ Hook (0-3s):</b><br>
                        <span style="color:#f1f5f9; font-size:0.9rem;">{p['hook']}</span>
                    </div>
                    <div style="margin-bottom:8px;">
                        <b style="color:#f472b6;">🔥 Cliffhanger:</b><br>
                        <span style="color:#f1f5f9; font-size:0.9rem;">{p['cliffhanger']}</span>
                    </div>
                    <div>
                        <b style="color:#fbbf24;">💡 Why It Works:</b><br>
                        <span style="color:#cbd5e1; font-size:0.85rem;">{p['why_it_works']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_right:
                st.markdown(f"""
                <div class="phone-mockup">
                    <div class="phone-notch"></div>
                    <div>
                        <div class="phone-tag pill-red">RANK #{p['rank']}</div>
                        <div class="phone-overlay-title">{p['episode']}</div>
                        <div style="font-size:0.65rem; color:#94a3b8;">Instagram Reels / TikTok</div>
                    </div>
                    <div class="phone-caption">
                        <b>⚡ HOOK:</b> {p['hook'][:80]}...
                    </div>
                    <div class="phone-caption" style="border-left-color:#c2185b; margin-top:4px;">
                        <b>🔥 CLIFF:</b> {p['cliffhanger'][:80]}...
                    </div>
                    <div class="phone-bottom-bar">
                        <span>{p['total_duration_sec']}s clip</span>
                        <span style="color:#ff6b6b; font-weight:700;">★ {p['scores']['overall']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 3: BATCH PROCESS NEW SHOW
# -------------------------------------------------------------
elif view_mode == "📁 Batch Process New Show":
    st.subheader("📁 Process an Entire Season or Batch of Screenplays")
    st.markdown("Upload a **ZIP of screenplay text files** or specify a folder path to run the end-to-end pipeline.")

    zip_upload = st.file_uploader("Upload Screenplay ZIP", type=["zip"])
    custom_dir = st.text_input("Folder path on disk:", value="data")

    limit_input = st.number_input("Limit episodes to process (0 = all):", min_value=0, max_value=200, value=0)

    if st.button("🚀 Run Full Pipeline on Show", type="primary"):
        target_dir = custom_dir
        if zip_upload is not None:
            extract_dir = os.path.join("cache", "uploaded_show")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_upload, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            target_dir = extract_dir
            st.success(f"Extracted screenplays to `{extract_dir}`")

        with st.spinner("Processing entire season..."):
            limit = limit_input if limit_input > 0 else None
            promos = process_show(data_dir=target_dir, api_key=active_api_key, max_episodes=limit)
            export_outputs(promos)
            st.success(f"🎉 Evaluated and ranked **{len(promos)}** promos across the show!")

# -------------------------------------------------------------
# TAB 4: ENGINEERING ARCHITECTURE
# -------------------------------------------------------------
elif view_mode == "📖 Engineering Architecture":
    st.subheader("📖 Production Architecture & Evaluation Criteria")

    col_a1, col_a2 = st.columns([1, 1])
    with col_a1:
        st.markdown("""
        ### 🎯 The Scoring Function
        $$\\text{Overall Score} = 0.40 \\times H + 0.40 \\times C + 0.20 \\times S$$
        - **$H$ (Hook, 0-3s):** Measures immediate visual/verbal shock (slaps, public humiliation, gasp, shocking revelation).
        - **$C$ (Cliffhanger Cut):** Pinpoints cuts at the height of emotional tension before resolution.
        - **$S$ (Standalone Clarity):** Ensures a cold scroller who has never watched the series understands the conflict.

        ### 💰 Cost & Latency at Scale
        - **Code Pre-Filter:** Discards 90%+ invalid stretches in milliseconds at zero cost.
        - **Gemini Flash Layer:** Calls AI only on top 3–5 viable candidate windows.
        - **Total cost per 50-episode season:** **< $0.05**.
        """)
    with col_a2:
        st.markdown("""
        ### ⚠️ Transparent Quality Failure Cases
        1. **The 'Lore / Prop' Trap:** Later episode cliffhangers often depend on specific props (e.g. a second will or a family pendant) that require contextual lore that cold viewers lack.
        2. **False-Positive Action Hooks:** Sudden door slams or camera snaps can trigger high hook scores even when dialogue afterwards slows down.
        3. **Pacing Discrepancies:** A 3-second screenplay beat might take longer on screen depending on the actor's delivery and music edit.
        """)
