"""Synthetic Job Source generating realistic opportunities and edge cases for testing and dry-runs."""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timedelta

from job_parser.extractor import JobExtractor, ParsedJob, JobCategory
from job_sources.base_source import BaseJobSource


class SyntheticJobSource(BaseJobSource):
    def __init__(self):
        super().__init__(platform_id="synthetic_fixture", base_url="https://mock.jobs.local", rate_limit_delay=0.0)

    def discover_jobs(self, query: str = "python developer", location: str = "Bengaluru", limit: int = 20) -> List[ParsedJob]:
        """Return curated high-fidelity test jobs representing diverse categories and edge cases."""
        now_iso = datetime.utcnow().isoformat()
        yesterday_iso = (datetime.utcnow() - timedelta(days=1)).isoformat()
        old_iso = (datetime.utcnow() - timedelta(days=20)).isoformat()

        jobs_data = [
            # 1. High Priority Full Stack (Category B -> RESUME_A)
            {
                "title": "Junior Python Full Stack Developer",
                "employer": "FinTech Innovations Pvt Ltd",
                "location_raw": "Bengaluru, Karnataka",
                "description": (
                    "FinTech Innovations is hiring a Junior Python Full Stack Developer (0-1 year experience). "
                    "Responsibilities: Build scalable web applications using Python and Django MVT architecture. "
                    "Integrate relational SQL databases, design models with Django ORM, and create responsive UI "
                    "using HTML5, CSS3, Flexbox, and JavaScript (ES6+). Experience with Git version control required. "
                    "Freshers from 2024/2025/2026 batch eligible. Excellent learning environment."
                ),
                "url": "https://careers.fintechinnovations.com/jobs/detail?id=FT-2026-001&utm_source=linkedin&ref=job_alert",
                "ext_id": "FT-2026-001",
                "source": "greenhouse_ats",
                "date": now_iso,
            },
            # 2. High Priority Backend Developer (Category A -> RESUME_B)
            {
                "title": "Associate Software Engineer — Python Backend",
                "employer": "CloudScale Systems",
                "location_raw": "Bengaluru (Hybrid)",
                "description": (
                    "We are seeking an Associate Python Backend Engineer with 0-2 years experience. "
                    "Mandatory Skills: Core Python OOP, structured programming, exception handling, and Django backend. "
                    "Proficiency with SQL/Oracle SQL queries (CRUD, Joins, GROUP BY) and REST API fundamentals with JSON. "
                    "You will design database models, implement clean views and routing, and maintain data integrity. "
                    "Fresh graduates with project experience in Django are encouraged to apply."
                ),
                "url": "https://cloudscale.lever.co/postings/cs-py-402?utm_medium=email&source=careers",
                "ext_id": "CS-402",
                "source": "lever_ats",
                "date": yesterday_iso,
            },
            # 3. SQL & Database Developer (Category C -> RESUME_C)
            {
                "title": "Junior SQL Database Developer",
                "employer": "DataSphere Solutions",
                "location_raw": "Bengaluru",
                "description": (
                    "Looking for an entry-level SQL Developer (0-1 years of experience). "
                    "Key Responsibilities: Write and execute complex SQL / Oracle SQL queries, CRUD operations, "
                    "multi-table Joins, subqueries, and aggregate functions. Collaborate with backend engineering "
                    "teams to ensure relational database consistency and schema design. Freshers welcome."
                ),
                "url": "https://datasphere.com/careers/sql-dev?jobId=DS-SQL-99&trk=feed",
                "ext_id": "DS-SQL-99",
                "source": "direct_employer_career",
                "date": now_iso,
            },
            # 4. Internship / Trainee (Category D)
            {
                "title": "Python Software Development Intern",
                "employer": "Nexus Labs",
                "location_raw": "Remote (India)",
                "description": (
                    "Nexus Labs invites applications for a 6-month Python Software Development Internship. "
                    "Work with experienced engineers on web services built with Python, Django, and SQL. "
                    "Opportunity to learn test automation with Selenium. Open to pre-final and final year B.E./B.Tech graduates."
                ),
                "url": "https://internshala.com/internship/detail/python-intern-nexus-101",
                "ext_id": "NX-INT-101",
                "source": "internshala",
                "date": now_iso,
            },
            # 5. Over-Experience Hard Veto (>2.0 Years)
            {
                "title": "Senior Python Backend Engineer",
                "employer": "MegaCorp Tech",
                "location_raw": "Bengaluru",
                "description": (
                    "Looking for an experienced Senior Python Engineer. Mandatory: 5+ years of experience in Python, "
                    "microservices architecture, Kubernetes, and distributed systems."
                ),
                "url": "https://megacorp.com/jobs/sr-py-909",
                "ext_id": "MC-909",
                "source": "naukri",
                "date": yesterday_iso,
            },
            # 6. Critical Skill Exclusion Hard Veto (Mandatory PL/SQL Stored Procedures)
            {
                "title": "Oracle PL/SQL Developer",
                "employer": "Legacy Banking Tech",
                "location_raw": "Bengaluru",
                "description": (
                    "Mandatory requirements: Expert level PL/SQL programming. Must have extensive experience writing "
                    "stored procedures, triggers, database packages, and indexing optimization. Freshers with PL/SQL certification considered."
                ),
                "url": "https://legacybank.com/jobs/plsql-dev",
                "ext_id": "LB-PLSQL-11",
                "source": "naukri",
                "date": old_iso,
            },
            # 7. Fraudulent / Pay-to-Work Scam Veto
            {
                "title": "Graduate Python Trainee",
                "employer": "FastTrack Careers Pvt Ltd",
                "location_raw": "Bengaluru",
                "description": (
                    "Guaranteed job placement! Selected candidates must submit a refundable security deposit and training fee "
                    "of Rs 15,000 for company orientation and software licenses."
                ),
                "url": "https://fasttrack-scam.com/jobs/apply",
                "ext_id": "FT-SCAM-01",
                "source": "foundit",
                "date": now_iso,
            },
            # 8. Unrelated Excluded Role (BPO / Tech Support)
            {
                "title": "Technical Support Executive / Customer Care",
                "employer": "Global BPO Services",
                "location_raw": "Bengaluru",
                "description": (
                    "Hiring for International Voice Process and desktop support / customer care. Handle customer queries "
                    "via inbound calls. Shift timing: 24/7 rotational. Freshers eligible."
                ),
                "url": "https://globalbpo.com/jobs/voice-support",
                "ext_id": "GB-TS-88",
                "source": "naukri",
                "date": now_iso,
            },
            # 9. LinkedIn Restricted Portal Test
            {
                "title": "Entry-Level Django Developer",
                "employer": "QuickByte Solutions",
                "location_raw": "Bengaluru (On-site)",
                "description": (
                    "QuickByte is hiring an Entry-Level Django Developer (0-1 year experience). "
                    "Required: Python, Django, SQL databases, Git, and HTML/CSS. Build web modules and assist backend team."
                ),
                "url": "https://www.linkedin.com/jobs/view/3998123456/?refId=feed_item",
                "ext_id": "LI-3998123456",
                "source": "linkedin",
                "date": now_iso,
            },
        ]

        parsed_jobs = []
        for item in jobs_data[:limit]:
            parsed = JobExtractor.parse_job(
                title=item["title"],
                employer=item["employer"],
                description=item["description"],
                job_url=item["url"],
                external_job_id=item["ext_id"],
                source_platform=item["source"],
                posting_date=item["date"],
                location_raw=item["location_raw"],
                is_synthetic=True,
                verification_status="DEMO_ONLY",
            )
            parsed_jobs.append(parsed)

        return parsed_jobs
