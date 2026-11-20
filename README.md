# 🎬 Kuku — AI Microdrama Promo & Hook Finder

An intelligent, production-grade promo detection and ranking engine built for AI vertical microdramas (TikTok, Instagram Reels, YouTube Shorts). 

It processes timestamped screenplays with sub-second precision, generates 20–60s candidate windows anchored on high-energy hooks and unresolved cliffhangers, and scores them using a **hybrid architecture** (Fast Heuristic Code Pre-filter + Google Gemini Generative AI).

---

## 🌟 Key Features
- **Deterministic Timestamp Parser (`parser.py`):** Parses microdrama screenplays extracting micro-blocks (camera, dialogue, sound effects, action) with normalized sub-second timestamps.
- **Candidate Window Generator (`candidate_generator.py`):** Mathematically identifies viable 20–60 second windows anchored on 3s visual/verbal hooks and exit cliffhangers. Supports both single-episode and cross-episode multi-segment promos.
- **Hybrid Scoring Engine (`scorer.py`):**
  - **Stage 1 (Code Pre-Filter):** Filters 90%+ unviable stretches in milliseconds at zero cost.
  - **Stage 2 (Gemini LLM Layer):** Calls Google Gemini Flash via direct REST to generate qualitative rationales, hook/cliffhanger breakdowns, and audience standalone clarity ratings.
  - **Deterministic NLP Fallback:** Operates 100% offline if no API key is provided or quota runs out.
- **Global Ranker & Raw Outputs (`ranker.py`):** Evaluated all 50 episodes, generating `outputs/promos_master.json` (282 ranked promos) and `outputs/promos_master.md`.
- **Modern React + Tailwind Web Studio (`server.py`):**
  - Interactive catalog with real-time score filtering.
  - **9:16 Vertical Phone Simulator:** Previews clips inside a mobile feed mockup.
  - **Live Screenplay Tester:** Drop or paste any unseen screenplay to test during interviews.
- **Streamlit Alternative (`app.py`):** Ready for one-click deployment on Streamlit Community Cloud.

---

## 🚀 Quickstart

### Method 1: Running Directly from the Downloaded Folder (No Git Required)
If you already have this folder on your machine (or unzipped the project archive):

1. **Open a terminal in the project folder:**
   - **Windows:** Open the folder in File Explorer, click the address bar at the top, type `powershell` or `cmd`, and press **Enter**.
   - **macOS / Linux:** Open your terminal and `cd` to the folder directory:
     ```bash
     cd /path/to/Hook-finder
     ```

2. **(Optional) Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the Web Studio:**
   - **Option A — Modern React 18 + Tailwind Studio (Recommended):**
     ```bash
     python server.py
     ```
     Open **[http://localhost:8000](http://localhost:8000)** in your browser.
   - **Option B — Streamlit Dashboard:**
     ```bash
     streamlit run app.py
     ```
     Open **[http://localhost:8501](http://localhost:8501)** in your browser.

5. **(Optional) Run the Batch CLI Pipeline directly:**
   ```bash
   python ranker.py
   ```
   This processes all 50 episode screenplays in `data/`, generates candidate cuts, evaluates them, and writes the ranked results to `outputs/promos_master.json` and `outputs/promos_master.md`.

> **Note on AI Keys:** The engine works **100% offline out-of-the-box** using deterministic NLP heuristic scoring. If you want live Gemini generative AI evaluations, optionally set your key:
> ```bash
> # Windows (PowerShell)
> $env:GEMINI_API_KEY="your_api_key_here"
> # macOS / Linux
> export GEMINI_API_KEY="your_api_key_here"
> ```
> *(You can also paste the API key directly in the web UI header.)*

---

### Method 2: Clone from GitHub
```bash
git clone https://github.com/mishrautkarsh17/Hook-finder.git
cd Hook-finder
pip install -r requirements.txt
python server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 📁 Repository Structure
```
├── data/                    # 50 microdrama screenplay text files (Input pack)
├── outputs/
│   ├── promos_master.json   # Full raw outputs: 282 ranked promos
│   └── promos_master.md     # Comprehensive editorial report
├── static/
│   └── index.html           # Modern React 18 + Tailwind CSS frontend
├── parser.py                # Timestamp parser & micro-block extractor
├── candidate_generator.py   # 20-60s window finder & heuristic filter
├── scorer.py                # Hybrid scoring engine (Gemini API + NLP fallback)
├── ranker.py                # Global ranking pipeline & exporter
├── server.py                # FastAPI server serving React SPA & REST API
├── app.py                   # Streamlit dashboard alternative
├── SOLUTION_DOC.md          # Official 2-page solution write-up (Markdown)
├── SOLUTION_DOC.html        # Print-ready A4 2-page solution document
├── PRESENTATION_SLIDES.html # 16:9 widescreen presentation slides for demo video
└── requirements.txt         # Python dependencies
```

---

## 📊 Posting Strategy & Quality Audit
- **Top-of-Funnel (Cold Social Ads):** Deploy Episode 1 (Rank #1: 01:47.40 – 02:18.00) and Episode 3. Universal themes (altar betrayal, public humiliation) require zero lore for a scrolling viewer.
- **Mid-Funnel Retargeting:** Use multi-segment cross-episode promos to create unresolved curiosity loops across episode boundaries.
- **Honest Limitations:** As documented in `SOLUTION_DOC.md`, the tool can occasionally over-weight generic physical actions (door slams) and later-episode cliffhangers that hinge on obscure family props/wills that cold scrollers don't recognize.
