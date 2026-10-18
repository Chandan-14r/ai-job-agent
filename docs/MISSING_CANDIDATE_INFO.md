# Missing Candidate Information & Source-of-Truth Reconciliation Checklist
**Candidate:** Kiran A N  
**System Status:** Mode 1 (DISCOVERY_MODE Active) | Zero Fabrication Policy Enforced  
**Document Version:** 1.0.0 (Stage 1 Audit Reconciliation)

---

## Executive Summary
In strict compliance with the **Zero Fabrication Policy**, the AI Job Application Agent never guesses, infers, or hallucinates candidate data. During the Stage 1 workspace audit, all available directories and candidate baseline files were inspected. The baseline profile contains verified academic performance (B.E. CSE from JSSATE, CGPA: 7.98), verified training at QSpiders (Python Full Stack & Selenium), verified GitHub/LinkedIn/Portfolio links, and two verified portfolio projects (*Stock Market Analysis* and *Food Delivery Web Page*).

However, several critical candidate contact, academic timeline, and professional experience fields remain **UNKNOWN**. This document provides the authoritative checklist of missing attributes required before automated application workflows (Mode 2 / Mode 3) can be initiated.

---

## 1. High-Priority Missing Candidate Data

| Attribute | Baseline Status | Required Action / Candidate Input Needed | Impact if Missing |
| :--- | :--- | :--- | :--- |
| **Email Address** | `UNKNOWN / null` | Candidate must supply primary professional email | Blocks automated submission; triggers `AWAITING_MANUAL_ACTION` |
| **Phone / Mobile Number** | `UNKNOWN / null` | Candidate must supply active Indian contact number (+91) | Blocks automated submission; triggers `AWAITING_MANUAL_ACTION` |
| **Graduation Year (B.E. CSE)** | `UNKNOWN / null` | Confirm year of graduation from JSS Academy (e.g., 2024, 2025, or 2026) | Used on ATS application forms and education history |
| **Prinston Smart Engineer Internship** | `UNVERIFIED / Gaps` | **Mandatory Details Required:**<br>1. Exact Role Title (e.g., *Software Development Intern*)<br>2. Start Date (Month/Year)<br>3. End Date (Month/Year or Present)<br>4. Verified Responsibilities & Achievements | Cannot claim or output on ATS resumes until verified. Omitted from generated resumes to prevent fabrication. |
| **Date of Birth** | `UNKNOWN / null` | Candidate confirmation (DD/MM/YYYY) | Required on certain Indian corporate application portals |
| **Postal Code / Street Address** | `UNKNOWN / null` | Bangalore PIN code (e.g., 560085) | Needed for location verification on select ATS forms |

---

## 2. Operational Preferences Requiring Candidate Confirmation

| Preference Parameter | Default System Assumption | Candidate Review & Decision Needed |
| :--- | :--- | :--- |
| **Minimum Expected Salary (CTC)** | `None (Conservative Hold)` | What is the minimum annual CTC in INR (e.g., 3.5 LPA, 4.5 LPA)? Roles asking mandatory CTC will halt until specified. |
| **Notice Period** | `Immediate (Fresher default)` | Confirm if candidate is available to join immediately or within 15–30 days. |
| **Willingness to Relocate** | `No (Bengaluru / Remote India only)` | Confirm if roles in Hyderabad, Pune, Chennai, or NCR should be considered. |
| **Service Bonds / Employment Agreements** | `Strictly Rejected (False)` | Confirm if candidate is willing to sign 1-year or 2-year service agreements. |
| **Contract / Third-Party Payroll Roles** | `Strictly Rejected (False)` | Confirm if candidate accepts fixed-term contract roles or strictly permanent full-time. |

---

## 3. The 13 Never-Guess Fields & Guardrail Matrix

The table below details the 13 fields the agent will **NEVER** guess or invent:

```
[1] Phone Number                 --> Halt & Notify candidate immediately
[2] Email Address                --> Halt & Notify candidate immediately
[3] Date of Birth                --> Halt & Notify candidate immediately
[4] Employment/Internship Dates  --> Halt & Notify candidate immediately
[5] Graduation Year              --> Halt & Notify candidate immediately
[6] Expected CTC / Salary        --> Halt & Notify candidate immediately
[7] Notice Period                --> Halt & Notify candidate immediately
[8] Current Employment Status    --> Halt & Notify candidate immediately
[9] Work Authorization / Visa    --> Halt & Notify candidate immediately
[10] Relocation Willingness      --> Halt & Notify candidate immediately
[11] Total Years of Experience   --> Halt & Notify candidate immediately
[12] Legal Background Declarations--> Halt & Notify candidate immediately
[13] Sensitive Personal Data     --> Halt & Notify candidate immediately
```

---

## 4. How to Update Missing Information
Candidate can update these fields at any time via either of the following two safe methods:

1. **Option A (Configuration File):** Open `config/candidate_profile.yaml` and update the `contact`, `education`, and `internships` blocks.
2. **Option B (Environment Variables):** Provide `CANDIDATE_EMAIL` and `CANDIDATE_PHONE` inside `.env`.
