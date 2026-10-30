# 🤖 AI Usage Log — COD RTO Decision Engine

**Project:** Oytra COD RTO Decision Engine  
**Author:** Vansh Patel (`vdppatel2204@gmail.com`)  
**Target:** Associate Software Engineer Internship at Oytra  
**Evaluation Lead:** Kapil (Founder / Engineering)  
**Date:** October 2026  
**Purpose:** Honest, engineering-grade documentation of where AI assisted, where it failed or hallucinated, and how those issues were identified and resolved through rigorous software engineering.

---

## 1. Where AI Was Used Effectively

### A. Rapid UI Component & CSS Prototyping
- **What AI Did:** Helped scaffold the Streamlit layout, Plotly chart configurations, and custom CSS mimicking modern institutional design systems (ClarioAI / Linear / Shadcn UI).
- **Engineering Value:** Saved ~4 hours of front-end styling boilerplate. Enabled fast iteration on CSS grid layouts, metric cards, and responsive columns.

### B. Domain NLP & Conversational Templates
- **What AI Did:** Drafted initial bilingual (English & Hinglish) WhatsApp message templates, covering delivery confirmations, return policies, product ingredient safety, and prepaid discount nudges.
- **Engineering Value:** Created authentic, culturally natural conversational copy that resonates with Indian D2C buyers without sounding like a robotic automated notification.

### C. Unit Test Scaffolding
- **What AI Did:** Generated skeleton test cases for mathematical bounds checking, threshold routing, and dataclass instantiation.
- **Engineering Value:** Sped up test suite creation, ensuring 100% test coverage across all 4 operational actions and unit economics formulas.

---

## 2. Where AI Fell Short & Human Engineering Was Required

### A. Tokenizer & Substring Collisions in Intent Parsing
- **Failure:** When writing initial intent classification rules, AI generated naive substring matches such as `if "ai" in text:` or `if "ha" in text:`.
- **Bug Identified:** The 2-letter substring `"ai"` matched common words like `"hair"` (*"Anti-Dandruff Hair Mask"*), `"hai"` (*"deliver ho sakta hai kya"*), and `"bhaiya"`! As a result, hair inquiries were mistakenly classified as bot identity questions.
- **Human Fix:** Refactored intent parsing into strict regex word-boundary patterns (`\b(ai|bot|human)\b` and `\b(yes|haan|ha|sure)\b`), completely eliminating false positive classifications.

### B. Windows ANSI vs. UTF-8 File Encoding
- **Failure:** Early scripts written via Windows command line defaulted to `cp1252` encoding rather than `UTF-8`.
- **Bug Identified:** Currency symbols (`₹`) and emojis (`✅`, `❌`, `🛡️`) were mangled into mojibake characters (`dY'`, `,130`).
- **Human Fix:** Enforced explicit `encoding="utf-8"` across all file I/O operations and configured environment variables (`$env:PYTHONIOENCODING="utf-8"`).

### C. Stale Bytecode in Running Streamlit Processes
- **Failure:** Streamlit re-executes `app.py` on interaction but caches imported modules (`src/decision_engine.py` and `src/whatsapp_mock.py`) in `sys.modules`. Edits to underlying engine files were ignored by the running web server.
- **Human Fix:** Implemented explicit dynamic module reloading at startup using `importlib.reload(decision_engine)` and `importlib.reload(whatsapp_mock)`.

### D. Architectural Decision: Rejecting Pure LLM Decisioning
- **Failure:** Generic AI recommendations suggested routing the entire order JSON through an LLM to decide whether to ship or cancel.
- **Human Correction:** Rejected this design. Financial decisions require deterministic auditability, sub-millisecond latency, and near-zero cost. We restricted LLM usage exclusively to qualitative address/name parsing and kept all scoring, weighting, and thresholding in pure Python.

---

## 3. Key Takeaway
AI functioned as an efficient accelerator for scaffolding and prototyping. However, domain accuracy, deterministic unit economics, robust error handling, and test-driven verification required rigorous human engineering and architectural discipline.
