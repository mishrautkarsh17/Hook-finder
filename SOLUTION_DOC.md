# Kuku — AI Generalist Assignment: Problem 1 (Promo Finder)
**Role:** AI Generalist | **Submission Scope:** Problem 1 (Find the Promos)

---

## 1. Executive Summary & Problem Framing
Microdramas thrive on high emotional frequency, fast narrative velocity, and short 1-to-2 minute vertical episodes. Today, human video editors manually screen every screenplay and episode to hand-pick social media promos for TikTok, Instagram Reels, and YouTube Shorts. 

This project builds an automated, hybrid AI promo detection and ranking pipeline that scans microdrama screenplays and produces ready-to-cut 20–60 second promo specifications with sub-second timestamps, hook classifications, cliffhanger breakdowns, and standalone conversion rationales.

### Core Assumptions Made:
1. **Screenplay-to-Edit Fidelity:** The timestamps present in the screenplays are treated as the true temporal anchors for camera, audio, and dialogue cuts.
2. **The "Scrolling Viewer" Standard:** A promo must achieve narrative grab within the first 3.0 seconds, maintain momentum, and cut precisely before the emotional climax resolves.
3. **Cross-Episode Continuity:** Micro-series feature cliffhangers at episode boundaries; therefore, cross-episode multi-segment pairings (ending of Ep N + opening of Ep N+1) are valid and often outperform single-episode cuts for retargeting campaigns.

---

## 2. Approach, Architecture & Scale

```
Screenplay (.txt) ➔ [Deterministic Parser] ➔ Micro-blocks (with sub-sec timestamps)
                                   ↓
                   [Candidate Generator (20-60s Windows)]
                                   ↓ (Pre-filters 90%+ unviable stretches in ~0.05s)
                   [Hybrid Evaluator]
                   ├── Fast NLP Heuristic Layer (Zero-cost, offline fallback)
                   └── LLM Qualitative Layer (Google Gemini 3 Flash REST API)
                                   ↓
                   [Global Ranker & Output Exporter]
                   ├── outputs/promos_master.json (Structured data: 282 ranked promos)
                   ├── outputs/promos_master.md   (Editorial strategy report)
                   └── React 18 SPA + FastAPI Web Studio (Interactive phone simulator & tester)
```

### Division of Labor (Code vs. AI):
- **What is kept in Code/Rules:**
  - Parsing timestamps, dialogue tags, and camera directions into float-second micro-blocks.
  - Window generation strictly enforcing the 20.0s to 60.0s duration constraint.
  - Initial heuristic filtering (detecting high-intensity openers like slaps, reveals, gasps, and cutoffs).
  - Redundancy and temporal overlap suppression ($IoU > 12s$) to ensure variety.
- **What is delegated to AI:**
  - Qualitative evaluation of "Standalone Clarity" (whether an outsider understands the stakes).
  - Editorial reasoning (`why_it_works`) and narrative tension scoring via Gemini Flash.
- **Human-in-the-Loop:**
  - Social media editors use the interactive web studio to review, filter, and approve ranked candidates before video rendering.

### Production Scalability & Cost:
By pre-filtering candidates with deterministic code before invoking the LLM, token consumption is reduced by **~85%**. Processing a full 50-episode season costs **under $0.05** using Gemini 3 Flash, executing in under 3 minutes with disk-level caching.

---

## 3. Top Promos & Posting Strategy

### Ranked Top Promos (Evaluated via Gemini 3 Flash):
1. **Rank #1 — Episode 3 [00:32.40 – 01:11.00] (38.6s) | Score: 9.3/10**
   - **Hook (0-3s):** High-stakes emotional rejection of a daughter by a cold matriarch creates instant sympathy and tension.
   - **Cliffhanger:** Cuts mid-confrontation just as a mysterious, powerful stranger challenges the antagonist's authority.
   - **Why It Works:** Balances the 'Cinderella' underdog trope with high-octane rescue fantasy, triggering instant viewer engagement.
2. **Rank #2 — Episode 15 [00:46.00 – 01:24.20] (38.2s) | Score: 9.3/10**
   - **Hook (0-3s):** Immediate aggressive confrontation and a defiant *"No"* from the protagonist.
   - **Cliffhanger:** Cuts exactly as the antagonist challenges the hero to a duel.
   - **Why It Works:** Combines hero-arrival payoff with acute physical stakes.
3. **Rank #5 — Episode 3 + Episode 4 (Cross-Episode Teaser) (50.95s) | Score: 9.3/10**
   - **Hook (0-3s):** Visual of a scarred hand offering a ring to a humiliated bride.
   - **Cliffhanger:** Cuts as the lead is overcome with emotion before the response.

### Posting Strategy:
- **Phase 1 (Cold User Acquisition / Top-of-Funnel):** Deploy Rank #1 (Episode 3) and Episode 1 on TikTok and Instagram Reels. Visceral archetypes (cheated bride, wicked family) convert cold audiences without lore.
- **Phase 2 (Retargeting / Binge Triggering):** Deploy cross-episode multi-segment promos (Rank #5) to users who watched earlier episodes to push them past subscription paywalls.
- **Optimal Duration:** The top performers concentrate in the **25–42 second** bracket, matching vertical video retention peaks.

---

## 4. Quality Audit: Where Does the Tool Fail? (Honest Failure Analysis)
1. **The "Lore/Prop" Cliffhanger Trap:** In mid-to-late episodes, scripts frequently cut on a character discovering a document, ring, or will. The tool scores this high on cliffhanger metrics due to dramatic cues, but cold scrollers cannot appreciate the stake because they don't know the backstory.
2. **False-Positive Visual Hooks:** Rapid camera motions or door slams can trigger high hook scores even when followed by slower conversational exposition.
3. **Screenplay vs. Performed Pacing:** Screenplays denote pauses as 1-2 lines, but director choices or slow dialogue delivery in video may drag the promo's momentum.

---

## 5. Live Interview Re-run Capability
The prototype includes a **Live Screenplay Tester** tab in the web app (`http://localhost:8000`). During the interview, evaluators can upload or paste any unseen episode screenplay, and the tool will parse, slice, and score viable promos in real time.
