# Autonomous AI Job Application Agent for Kiran A N
**Engineered with Google Antigravity | Python Backend & Browser Automation Architecture**

---

## 🌟 Executive Overview
This is a production-grade, locally operated, and privacy-first autonomous AI Job Application Agent tailored specifically for **Kiran A N**. It discovers, parses, ranks, and stages software engineering, full-stack, backend, database, and automation roles across official company career boards and compliant job portals.

The agent enforces a strict **Zero Fabrication Policy**: every skill claim, project attribute, and academic detail is strictly grounded in Kiran A N's verified baseline profile.

---

## 🏗️ Architecture & Component Overview

```
ai_job_agent/
├── config/
│   ├── candidate_profile.yaml      # Authoritative candidate profile and verified skills
│   ├── preferences.yaml            # Location, salary hold, role tiers & daily rate caps
│   └── job_sources.yaml            # Governance matrix for portals & ATS boards
├── candidate_profile/              # Profile loader and guardrail verifier
├── job_sources/                    # Compliant ATS feeds & portal connectors
├── job_parser/                     # Title normalization, experience & scam extraction
├── job_matcher/                    # Deterministic 100-point rubric with Hard Veto gate
├── duplicate_checker/              # Multi-key fingerprinting & URL canonicalization
├── resume_generator/               # ATS Resumes (Variants A, B, C in DOCX/PDF) & Cover Letters
├── application_workflow/           # 13-step pipeline & Zero-Guessing form validator
├── database/                       # SQLite application tracker with full audit history
├── telegram_notifications/         # Real-time Telegram Bot alerts (Templates A, B, C, D)
├── scheduler/                      # Thread-safe background periodic runner
├── dashboard/                      # Local Flask web dashboard with live KPI cards
├── docs/
│   ├── PLATFORM_CAPABILITY_MATRIX.md # Portal permissions and ToS analysis
│   └── MISSING_CANDIDATE_INFO.md     # Authoritative checklist of missing fields
└── tests/                          # 21-test automated verification suite
```

---

## 🚀 Quick Start Guide

### 1. Environment Setup
```bash
# Clone or open workspace
cd C:\Users\crs14\.gemini\antigravity\scratch\ai_job_agent

# Install dependencies (All verified on Python 3.10+)
pip install -r requirements.txt
```

### 2. Configure Telegram Bot Credentials
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, provide a name and username, and copy the HTTP API token.
3. Start a chat with your new bot by sending `/start`.
4. Retrieve your numeric Chat ID by visiting in your browser:
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. Copy `.env.example` to `.env` and populate your credentials:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```ini
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=987654321
   ```
   *(Note: If credentials are not set, the agent operates safely in mock fallback mode).*

---

## 📋 Running the Agent

### A. Run Automated Test Suite
Execute the comprehensive 21-test verification suite covering all 15 specification areas:
```bash
python -m pytest tests/ -v
```

### B. Generate Tailored ATS Resumes (Variants A, B, C)
Generate clean, ATS-compliant DOCX and PDF resumes with zero layout corruption:
```bash
python main.py --generate-resumes
```
Files will be placed in `output/resumes/`:
- `Kiran_A_N_Resume_RESUME_A.docx` & `.pdf` (Python Full Stack Developer)
- `Kiran_A_N_Resume_RESUME_B.docx` & `.pdf` (Python Backend Developer)
- `Kiran_A_N_Resume_RESUME_C.docx` & `.pdf` (SQL / Database Developer)

### C. Mode 1: Safe Job Discovery Run (Default)
Discover, score, and store entry-level opportunities without submitting applications:
```bash
# Synthetic fixture discovery & edge-case test:
python main.py --mode DISCOVERY_MODE --discover

# Live discovery across public ATS employer boards:
python main.py --mode DISCOVERY_MODE --live
```

### D. Launch Local Monitoring Web Dashboard
Launch the web dashboard with real-time KPI metrics, filterable job table, and emergency controls:
```bash
python main.py --dashboard --port 5000
```
Open your browser to: **http://127.0.0.1:5000**

### E. Background Scheduler for Periodic Discovery
Run background cycles every 60 minutes:
```bash
python main.py --scheduler
```

---

## 🛡️ Operational Modes & Safety Guardrails

| Mode | Command Flag | Automated Actions Permitted | Safety Gate |
| :--- | :--- | :--- | :--- |
| **Mode 1 (Default)** | `--mode DISCOVERY_MODE` | Discover, parse, 100-pt rubric score, deduplicate, SQLite log, daily summary report. **Zero form submissions.** | **None (Fully Safe)** |
| **Mode 2** | `--mode ASSISTED_APPLICATION_MODE` | Mode 1 + tailored resume variant selection, cover letter generation, form pre-population staging, and Telegram **Manual Action Required** alert with direct links. | Candidate completes submission |
| **Mode 3** | `--mode AUTHORIZED_AUTO_APPLY_MODE` | End-to-end automated submission strictly on authorized ATS portals within daily limit (10/day). Immediate halt on any missing field or challenge. | **Pre-Activation Sign-Off Required** |

---

## 📊 Deterministic 100-Point Scoring Rubric

| Dimension | Max Points | Evaluation Logic |
| :--- | :---: | :--- |
| **1. Technical Skills** | 35 | Overlap with Python, Django, SQL/Oracle SQL, JS ES6+, HTML/CSS, Git, Selenium basics. |
| **2. Project Relevance** | 20 | Match with Stock Market Analysis (Django) and Food Delivery (Frontend JS). |
| **3. Experience Fit** | 15 | 15 pts for Fresher / 0–1 yr; 8 pts for 1–2 yr; 0 pts & Hard Veto if >2.0 yrs. |
| **4. Location / WFH** | 10 | 10 pts for Bengaluru or India Remote. |
| **5. Posting Recency** | 10 | 10 pts for <48h; decaying score up to 30 days. |
| **6. Career Growth** | 10 | High fit for core full-stack, backend, or database engineering roles. |

### Hard Veto Conditions (Immediate Rejection Regardless of Points):
- Mandatory experience > 2.0 years.
- Demands mandatory PL/SQL, stored procedures, triggers, indexing optimization, Java, C++, Go, or React.
- Excluded category (Tech support, BPO voice, helpdesk, sales).
- Scam indicators, fee demands, or security deposits.
- Duplicate posting previously submitted.

---

## 🔒 The 13 Never-Guess Fields
The agent strictly halts and alerts the candidate whenever an application form requires:
1. Phone number
2. Email address
3. Date of birth
4. Internship start/end dates
5. Graduation year
6. Expected salary / CTC
7. Notice period
8. Current employment status
9. Work authorization / visa status
10. Willingness to relocate
11. Years of professional experience
12. Mandatory legal declarations
13. Sensitive demographic or personal data
