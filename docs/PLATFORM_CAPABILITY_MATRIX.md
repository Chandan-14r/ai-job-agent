# Platform Capability, Compliance & Governance Matrix
**Antigravity Autonomous AI Job Application Agent**  
**Governing Standard:** Production-Grade Compliance, Zero Security Circumvention & Rate Discipline

---

## 1. Overview & Regulatory Directives
This governance matrix outlines the permitted discovery and application capabilities across major Indian job portals, global professional networks, and employer Applicant Tracking Systems (ATS).

The system enforces strict operational compliance:
- **No Private API Reverse Engineering:** We do not spoof mobile app endpoints or forge session signatures.
- **Zero Anti-Bot Circumvention:** Never deploy stealth plugins, puppeteer-extra stealth, Cloudflare solver services, CAPTCHA farms, or session hijackers.
- **Respect User Agreements & Robots.txt:** Adhere to platform terms of service. Where auto-apply is restricted or prohibited (such as LinkedIn), the system transitions to `ASSISTED_BROWSER` or `MANUAL_ONLY` handoff.
- **Deterministic Rate Limiting & Backoff:** Rate caps are strictly enforced per domain with jittered delays and exponential backoff on HTTP 429/503 responses.

---

## 2. Multi-Platform Capability Matrix

| Platform / Portal | Permitted Discovery Mode | Permitted Application Mode | Auth / Session Requirement | Anti-Bot & Challenge Protocol | Rate Cap (Req/Hr) | Governance & Handling Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **LinkedIn Jobs** | `ASSISTED_BROWSER` / `API_FEED` | `MANUAL_ONLY` | Candidate authenticated browser session | Halt immediately on login wall, pin verification, or bot challenge | 20 | LinkedIn strictly prohibits automated application submissions. The agent extracts JD, generates matching score, customizes resume/cover letter, and generates a one-click manual submission package. |
| **Naukri.com** | `ASSISTED_BROWSER` | `ASSISTED_BROWSER` | Registered candidate profile session | Halt on OTP, SMS verification, or CAPTCHA | 30 | Primary portal for Indian IT fresher roles. Staged auto-fill permitted only with candidate pre-approval. |
| **Indeed India** | `ASSISTED_BROWSER` | `ASSISTED_BROWSER` | Public / Direct Redirect | Cloudflare challenge detection halts automation | 25 | Most technical roles redirect directly to employer ATS portals. |
| **Foundit (Monster)** | `ASSISTED_BROWSER` | `ASSISTED_BROWSER` | Standard portal profile | Halt on login challenge | 30 | Focus on entry-level Python and graduate trainee listings. |
| **Internshala** | `ASSISTED_BROWSER` | `ASSISTED_BROWSER` | Student/Candidate account | Halt on assessment questionnaires requiring candidate input | 25 | Dedicated handling for Python development internships and graduate engineering trainees. |
| **Wellfound (AngelList)** | `ASSISTED_BROWSER` | `MANUAL_ONLY` | Verified founder/talent network | Halt on interactive founder pitch requirements | 15 | Startup roles requiring tailored candidate pitches. Routed to candidate for manual review. |
| **Cutshort** | `ASSISTED_BROWSER` | `MANUAL_ONLY` | Candidate profile verification | Halt on skill assessment tests | 20 | Indian tech recruiting network. Match alerts sent via Telegram for direct manual candidate interaction. |
| **Instahyre** | `ASSISTED_BROWSER` | `MANUAL_ONLY` | Candidate profile | Halt on inbound invite | 20 | Curated matching platform; candidate profile visibility suffices without raw automated spamming. |
| **Greenhouse ATS** | `API_FEED` | `AUTHORIZED_AUTO_APPLY` | Public Job Board API / Token | Standard HTTPS REST API | 60 | Clean official REST API (`boards-api.greenhouse.io`). Fully supports verified automated submission in Mode 3 when candidate approval is active and all required fields are present. |
| **Lever ATS** | `API_FEED` | `AUTHORIZED_AUTO_APPLY` | Public Job Board API (`api.lever.co`) | Standard HTTPS REST API | 60 | Compliant public posting and application API endpoints. |
| **Ashby ATS** | `API_FEED` | `AUTHORIZED_AUTO_APPLY` | Public Job Board API | Standard HTTPS REST API | 60 | High-growth tech ATS with direct public endpoints. |
| **Workday Career** | `API_FEED` | `MANUAL_ONLY` | Mandatory per-company account & MFA | Complex multi-step wizard, custom logins, and MFA | 20 | Auto-apply prohibited due to proprietary login firewalls and account creation barriers. Prepared application package handed off via Telegram. |
| **Zoho Recruit / Darwinbox / Freshteam** | `API_FEED` / `ASSISTED_BROWSER` | `ASSISTED_BROWSER` | Company specific portal | Halt on custom file upload or security token | 30 | Popular Indian mid-market ATS platforms. |

---

## 3. Operational Modes Defined

```
+-----------------------------------------------------------------------------------+
| Mode 1: DISCOVERY_MODE (Active Default)                                           |
| - Continuous compliant discovery across all enabled sources                       |
| - 100-point rubric matching, deduplication & SQLite persistence                   |
| - Daily Telegram summaries & CSV/Markdown reports                                 |
| - ZERO form filling, ZERO submissions                                             |
+-----------------------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------------------+
| Mode 2: ASSISTED_APPLICATION_MODE                                                 |
| - All Mode 1 capabilities                                                         |
| - Automatic generation of tailored ATS Resume (A/B/C in DOCX/PDF) & Cover Letter  |
| - Form field pre-population staging                                               |
| - Telegram "Manual Action Required" alert with pre-staged link & documents         |
+-----------------------------------------------------------------------------------+
                                       |
                                       v [Requires Candidate Pre-Activation Sign-Off]
+-----------------------------------------------------------------------------------+
| Mode 3: AUTHORIZED_AUTO_APPLY_MODE                                                |
| - End-to-end automated submission strictly on AUTHORIZED_AUTO_APPLY ATS platforms |
| - Max 10 applications per day cap                                                 |
| - Immediate halt on ANY missing field, legal attestation, or CAPTCHA              |
| - Post-submission confirmation verification before recording status               |
+-----------------------------------------------------------------------------------+
```

---

## 4. Rate Limiting & Backoff Specifications
1. **Per-Platform Request Delays:** Configurable minimum of 2.5 seconds between successive network operations.
2. **HTTP 429 (Too Many Requests) / 503 (Service Unavailable) Protocol:**
   - Immediately suspend discovery on that specific domain.
   - Execute exponential backoff with factor $2.0 \times 2^{\text{attempt}} + \text{jitter}(0, 1.5)$.
   - Maximum 3 retries. If the domain continues to throttle, pause domain discovery for 1 hour and alert the candidate via Telegram.
3. **Daily Submission Throttling:** Hard global cap of 10 submitted applications per calendar day. Submission #11 is deterministically blocked and placed in the next day's queue.
