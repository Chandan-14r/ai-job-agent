"""SQLite Application Tracking Repository with Full Audit Trail."""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import Application, ApplicationStatus, ApplicationStatusHistory, VALID_STATE_TRANSITIONS

logger = logging.getLogger(__name__)


class ApplicationRepository:
    def __init__(self, db_path: Optional[Path | str] = None, auto_seed: bool = False):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "applications.db"
            self.auto_seed = True
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.auto_seed = auto_seed

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Initialize database tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                employer TEXT NOT NULL,
                job_title TEXT NOT NULL,
                employment_type TEXT NOT NULL DEFAULT 'FULL_TIME',
                job_description_summary TEXT DEFAULT '',
                job_url TEXT DEFAULT '',
                canonical_url TEXT DEFAULT '',
                source_platform TEXT DEFAULT '',
                external_job_id TEXT DEFAULT '',
                location TEXT DEFAULT 'Bengaluru, Karnataka, India',
                work_arrangement TEXT DEFAULT 'On-site',
                posting_date TEXT,
                discovery_timestamp TEXT NOT NULL,
                matching_score INTEGER DEFAULT 0,
                matching_explanation_json TEXT DEFAULT '{}',
                required_skills_json TEXT DEFAULT '[]',
                missing_skills_json TEXT DEFAULT '[]',
                selected_resume_version TEXT DEFAULT 'RESUME_A',
                cover_letter_path TEXT,
                application_status TEXT NOT NULL DEFAULT 'DISCOVERED',
                submission_timestamp TEXT,
                application_reference_number TEXT,
                manual_action_required_reason TEXT,
                last_verification_timestamp TEXT,
                error_log TEXT,
                recruiter_contact_json TEXT DEFAULT '{}'
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id TEXT NOT NULL,
                previous_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                changed_at_timestamp TEXT NOT NULL,
                reason_or_actor TEXT DEFAULT '',
                FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
            );
            """)

            # Indexes for high performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_employer ON applications(employer);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_title ON applications(job_title);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(application_status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_canonical_url ON applications(canonical_url);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_platform_extid ON applications(source_platform, external_job_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_history_app_id ON application_status_history(application_id);")

            # Automatic column migrations for provenance & URL validation
            cursor.execute("PRAGMA table_info(applications);")
            existing_cols = {col[1] for col in cursor.fetchall()}
            migration_cols = [
                ("is_synthetic", "INTEGER DEFAULT 0"),
                ("verification_status", "TEXT DEFAULT 'SOURCE_CONFIRMED'"),
                ("verification_method", "TEXT DEFAULT 'ATS_PUBLIC_API'"),
                ("job_availability_status", "TEXT DEFAULT 'ACTIVE'"),
                ("salary_range", "TEXT"),
                ("min_experience_years", "REAL DEFAULT 0.0"),
                ("date_discovered", "TEXT"),
                ("date_last_checked", "TEXT"),
            ]
            for col_name, col_def in migration_cols:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE applications ADD COLUMN {col_name} {col_def};")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_synthetic ON applications(is_synthetic);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_verification ON applications(verification_status);")
            conn.commit()

            # Auto-seed verified baseline jobs if table is empty on default DB (e.g. fresh clone or Render deployment)
            if self.auto_seed and self.db_path != ":memory:":
                try:
                    cursor.execute("SELECT COUNT(*) FROM applications;")
                    if cursor.fetchone()[0] == 0:
                        seed_file = Path(self.db_path).resolve().parent / "seed_jobs.json"
                        if not seed_file.exists():
                            seed_file = Path(__file__).resolve().parent.parent / "data" / "seed_jobs.json"
                        if seed_file.exists():
                            with open(seed_file, "r", encoding="utf-8") as sf:
                                seed_data = json.load(sf)
                            for r in seed_data:
                                keys = list(r.keys())
                                placeholders = ", ".join(["?"] * len(keys))
                                col_str = ", ".join(keys)
                                cursor.execute(f"INSERT OR IGNORE INTO applications ({col_str}) VALUES ({placeholders})", list(r.values()))
                            conn.commit()
                            logger.info(f"Loaded {len(seed_data)} verified jobs from seed_jobs.json into fresh database")
                except Exception as se:
                    logger.warning(f"Auto-seed check error: {se}")

    def add_application(self, app: Application) -> Application:
        """Insert a newly discovered application."""
        if not app.id:
            app.id = str(uuid.uuid4())

        now_ts = app.discovery_timestamp or datetime.utcnow().isoformat()
        app.discovery_timestamp = now_ts
        if not app.date_discovered:
            app.date_discovered = now_ts
        if not app.date_last_checked:
            app.date_last_checked = now_ts

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO applications (
                id, employer, job_title, employment_type, job_description_summary,
                job_url, canonical_url, source_platform, external_job_id,
                location, work_arrangement, posting_date, discovery_timestamp,
                matching_score, matching_explanation_json, required_skills_json, missing_skills_json,
                selected_resume_version, cover_letter_path, application_status,
                submission_timestamp, application_reference_number, manual_action_required_reason,
                last_verification_timestamp, error_log, recruiter_contact_json,
                is_synthetic, verification_status, verification_method, job_availability_status,
                salary_range, min_experience_years, date_discovered, date_last_checked
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                app.id, app.employer, app.job_title, app.employment_type, app.job_description_summary,
                app.job_url, app.canonical_url, app.source_platform, app.external_job_id,
                app.location, app.work_arrangement, app.posting_date, app.discovery_timestamp,
                app.matching_score, app.matching_explanation_json, app.required_skills_json, app.missing_skills_json,
                app.selected_resume_version, app.cover_letter_path, app.application_status,
                app.submission_timestamp, app.application_reference_number, app.manual_action_required_reason,
                app.last_verification_timestamp, app.error_log, app.recruiter_contact_json,
                1 if app.is_synthetic else 0, app.verification_status, app.verification_method, app.job_availability_status,
                app.salary_range, app.min_experience_years, app.date_discovered, app.date_last_checked
            ))

            # Initial status history record
            cursor.execute("""
            INSERT INTO application_status_history (
                application_id, previous_status, new_status, changed_at_timestamp, reason_or_actor
            ) VALUES (?, ?, ?, ?, ?)
            """, (
                app.id, "NONE", app.application_status, app.discovery_timestamp, "Initial Discovery"
            ))
            conn.commit()

        return app

    def update_status(self, application_id: str, new_status: ApplicationStatus | str,
                      reason_or_actor: str = "", submission_ref: Optional[str] = None) -> bool:
        """Update status with strict state machine validation and full audit logging."""
        new_status_str = new_status.value if isinstance(new_status, ApplicationStatus) else new_status
        current_app = self.get_application_by_id(application_id)
        if not current_app:
            return False

        current_status = current_app.application_status
        now_ts = datetime.utcnow().isoformat()

        # Validate transition if current_status is known enum
        try:
            curr_enum = ApplicationStatus(current_status)
            new_enum = ApplicationStatus(new_status_str)
            allowed = VALID_STATE_TRANSITIONS.get(curr_enum, [])
            if new_enum not in allowed and curr_enum != new_enum:
                raise ValueError(f"Illegal state transition from {curr_enum.value} to {new_enum.value}")
        except ValueError as e:
            # Re-raise state transition violations
            if "Illegal state transition" in str(e):
                raise

        submission_ts = now_ts if new_status_str in [ApplicationStatus.SUBMITTED.value, ApplicationStatus.APPLICATION_CONFIRMED.value] else current_app.submission_timestamp

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE applications
            SET application_status = ?,
                submission_timestamp = COALESCE(?, submission_timestamp),
                application_reference_number = COALESCE(?, application_reference_number),
                last_verification_timestamp = ?
            WHERE id = ?
            """, (new_status_str, submission_ts, submission_ref, now_ts, application_id))

            cursor.execute("""
            INSERT INTO application_status_history (
                application_id, previous_status, new_status, changed_at_timestamp, reason_or_actor
            ) VALUES (?, ?, ?, ?, ?)
            """, (application_id, current_status, new_status_str, now_ts, reason_or_actor))
            conn.commit()

        return True

    def get_application_by_id(self, application_id: str) -> Optional[Application]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE id = ?", (application_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_application(row)
        return None

    def find_by_canonical_url(self, canonical_url: str) -> Optional[Application]:
        if not canonical_url:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE canonical_url = ?", (canonical_url,))
            row = cursor.fetchone()
            if row:
                return self._row_to_application(row)
        return None

    def find_by_platform_job_id(self, source_platform: str, external_job_id: str) -> Optional[Application]:
        if not source_platform or not external_job_id:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM applications WHERE source_platform = ? AND external_job_id = ?",
                (source_platform, external_job_id)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_application(row)
        return None

    def find_by_composite_key(self, employer: str, job_title: str, location: str) -> Optional[Application]:
        """Find matching application by normalized composite key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM applications WHERE LOWER(TRIM(employer)) = LOWER(TRIM(?)) "
                "AND LOWER(TRIM(job_title)) = LOWER(TRIM(?)) "
                "AND LOWER(TRIM(location)) = LOWER(TRIM(?))",
                (employer, job_title, location)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_application(row)
        return None

    def get_applications(
        self,
        employer: Optional[str] = None,
        job_title: Optional[str] = None,
        status: Optional[str] = None,
        source_platform: Optional[str] = None,
        employment_type: Optional[str] = None,
        work_arrangement: Optional[str] = None,
        verification_status: Optional[str] = None,
        min_score: Optional[int] = None,
        demo_only: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 150,
        offset: int = 0
    ) -> List[Application]:
        query = "SELECT * FROM applications WHERE 1=1"
        params: List[Any] = []

        if demo_only is True:
            query += " AND is_synthetic = 1"
        elif demo_only is False:
            query += " AND (is_synthetic = 0 OR is_synthetic IS NULL)"

        if employer:
            query += " AND LOWER(employer) LIKE ?"
            params.append(f"%{employer.lower()}%")
        if job_title:
            query += " AND LOWER(job_title) LIKE ?"
            params.append(f"%{job_title.lower()}%")
        if status:
            query += " AND application_status = ?"
            params.append(status)
        if source_platform:
            query += " AND source_platform = ?"
            params.append(source_platform)
        if employment_type:
            query += " AND employment_type = ?"
            params.append(employment_type)
        if work_arrangement:
            query += " AND LOWER(work_arrangement) = ?"
            params.append(work_arrangement.lower())
        if verification_status:
            query += " AND verification_status = ?"
            params.append(verification_status)
        if min_score is not None:
            query += " AND matching_score >= ?"
            params.append(min_score)
        if search:
            query += " AND (LOWER(employer) LIKE ? OR LOWER(job_title) LIKE ? OR LOWER(job_description_summary) LIKE ? OR LOWER(required_skills_json) LIKE ?)"
            s_term = f"%{search.lower()}%"
            params.extend([s_term, s_term, s_term, s_term])

        query += " ORDER BY matching_score DESC, discovery_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_application(r) for r in rows]

    def get_status_history(self, application_id: str) -> List[ApplicationStatusHistory]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM application_status_history WHERE application_id = ? ORDER BY id ASC",
                (application_id,)
            )
            rows = cursor.fetchall()
            return [
                ApplicationStatusHistory(
                    id=r["id"],
                    application_id=r["application_id"],
                    previous_status=r["previous_status"],
                    new_status=r["new_status"],
                    changed_at_timestamp=r["changed_at_timestamp"],
                    reason_or_actor=r["reason_or_actor"],
                )
                for r in rows
            ]

    def get_daily_submission_count(self, target_date: Optional[date] = None) -> int:
        """Count total applications submitted or confirmed on target date (enforces 10/day cap)."""
        if target_date is None:
            target_date = date.today()
        date_prefix = target_date.isoformat() # "YYYY-MM-DD"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT COUNT(*) as count FROM applications
            WHERE submission_timestamp LIKE ?
               OR (application_status IN ('SUBMITTED', 'APPLICATION_CONFIRMED')
                   AND discovery_timestamp LIKE ?)
            """, (f"{date_prefix}%", f"{date_prefix}%"))
            row = cursor.fetchone()
            return int(row["count"]) if row else 0

    def get_kpi_summary(self, demo_mode: bool = False) -> Dict[str, Any]:
        """Aggregate live KPI metrics for dashboard and reporting."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Scope by mode: live production vs demo
            filter_clause = "WHERE is_synthetic = 1" if demo_mode else "WHERE (is_synthetic = 0 OR is_synthetic IS NULL)"
            and_clause = "AND is_synthetic = 1" if demo_mode else "AND (is_synthetic = 0 OR is_synthetic IS NULL)"

            # Total discovered
            cursor.execute(f"SELECT COUNT(*) as cnt FROM applications {filter_clause}")
            total_apps = cursor.fetchone()["cnt"]

            # Genuine jobs count (always across all records)
            cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE (is_synthetic = 0 OR is_synthetic IS NULL)")
            genuine_count = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE is_synthetic = 1")
            demo_count = cursor.fetchone()["cnt"]

            # Total discovered split by employment type
            cursor.execute(f"SELECT employment_type, COUNT(*) as cnt FROM applications {filter_clause} GROUP BY employment_type")
            emp_counts = {r["employment_type"]: r["cnt"] for r in cursor.fetchall()}

            cursor.execute(f"SELECT COUNT(*) as cnt FROM applications WHERE matching_score >= 85 {and_clause}")
            high_priority = cursor.fetchone()["cnt"]

            daily_submissions = self.get_daily_submission_count()

            cursor.execute(f"SELECT COUNT(*) as cnt FROM applications WHERE application_status = 'AWAITING_MANUAL_ACTION' {and_clause}")
            awaiting_manual = cursor.fetchone()["cnt"]

            cursor.execute(f"SELECT COUNT(*) as cnt FROM applications WHERE application_status IN ('ASSESSMENT_RECEIVED', 'INTERVIEW') {and_clause}")
            interviews_assessments = cursor.fetchone()["cnt"]

            cursor.execute(f"SELECT COUNT(*) as cnt FROM applications WHERE application_status = 'FAILED' {and_clause}")
            failed_count = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM applications WHERE (is_synthetic = 0 OR is_synthetic IS NULL) AND verification_status = 'VERIFIED_ACTIVE'")
            verified_active_urls = cursor.fetchone()["cnt"]

        return {
            "total_applications": total_apps,
            "genuine_jobs_count": genuine_count,
            "demo_jobs_count": demo_count,
            "verified_active_urls": verified_active_urls,
            "full_time_count": emp_counts.get("FULL_TIME", 0),
            "internship_count": emp_counts.get("INTERNSHIP", 0) + emp_counts.get("TRAINEE", 0),
            "high_priority_matches": high_priority,
            "submitted_today": daily_submissions,
            "daily_limit": 10,
            "awaiting_manual_action": awaiting_manual,
            "assessments_and_interviews": interviews_assessments,
            "failed_attempts": failed_count,
        }

    def update_url_verification(
        self,
        application_id: str,
        verification_status: str,
        verification_method: str = "HTTP_PROBE",
        job_availability_status: str = "ACTIVE",
    ) -> bool:
        """Update URL verification status and timestamp for an application."""
        now_ts = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE applications
            SET verification_status = ?,
                verification_method = ?,
                job_availability_status = ?,
                date_last_checked = ?
            WHERE id = ?
            """, (verification_status, verification_method, job_availability_status, now_ts, application_id))
            conn.commit()
            return cursor.rowcount > 0

    def mark_all_synthetic_records(self, employer_names: List[str]) -> int:
        """Retroactively mark synthetic demo employers in database."""
        count = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for emp in employer_names:
                cursor.execute("""
                UPDATE applications
                SET is_synthetic = 1,
                    verification_status = 'DEMO_ONLY',
                    verification_method = 'SYNTHETIC_FIXTURE'
                WHERE LOWER(employer) = LOWER(?)
                """, (emp,))
                count += cursor.rowcount
            conn.commit()
        return count

    def export_to_csv(self, output_path: Path | str) -> str:
        """Export all applications to a structured CSV report."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        apps = self.get_applications(limit=10000)

        fieldnames = [
            "id", "employer", "job_title", "employment_type", "location", "work_arrangement",
            "source_platform", "matching_score", "application_status", "selected_resume_version",
            "submission_timestamp", "job_url", "is_synthetic", "verification_status"
        ]

        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for a in apps:
                writer.writerow({
                    "id": a.id,
                    "employer": a.employer,
                    "job_title": a.job_title,
                    "employment_type": a.employment_type,
                    "location": a.location,
                    "work_arrangement": a.work_arrangement,
                    "source_platform": a.source_platform,
                    "matching_score": a.matching_score,
                    "application_status": a.application_status,
                    "selected_resume_version": a.selected_resume_version,
                    "submission_timestamp": a.submission_timestamp or "",
                    "job_url": a.job_url,
                    "is_synthetic": 1 if a.is_synthetic else 0,
                    "verification_status": a.verification_status,
                })
        return str(out)

    def _row_to_application(self, row: sqlite3.Row) -> Application:
        keys = row.keys()
        return Application(
            id=row["id"],
            employer=row["employer"],
            job_title=row["job_title"],
            employment_type=row["employment_type"],
            job_description_summary=row["job_description_summary"] or "",
            job_url=row["job_url"] or "",
            canonical_url=row["canonical_url"] or "",
            source_platform=row["source_platform"] or "",
            external_job_id=row["external_job_id"] or "",
            location=row["location"] or "Bengaluru, Karnataka, India",
            work_arrangement=row["work_arrangement"] or "On-site",
            posting_date=row["posting_date"],
            discovery_timestamp=row["discovery_timestamp"],
            matching_score=row["matching_score"] or 0,
            matching_explanation_json=row["matching_explanation_json"] or "{}",
            required_skills_json=row["required_skills_json"] or "[]",
            missing_skills_json=row["missing_skills_json"] or "[]",
            selected_resume_version=row["selected_resume_version"] or "RESUME_A",
            cover_letter_path=row["cover_letter_path"],
            application_status=row["application_status"] or ApplicationStatus.DISCOVERED.value,
            submission_timestamp=row["submission_timestamp"],
            application_reference_number=row["application_reference_number"],
            manual_action_required_reason=row["manual_action_required_reason"],
            last_verification_timestamp=row["last_verification_timestamp"],
            error_log=row["error_log"],
            recruiter_contact_json=row["recruiter_contact_json"] or "{}",
            is_synthetic=bool(row["is_synthetic"]) if "is_synthetic" in keys and row["is_synthetic"] is not None else False,
            verification_status=row["verification_status"] if "verification_status" in keys and row["verification_status"] else "SOURCE_CONFIRMED",
            verification_method=row["verification_method"] if "verification_method" in keys and row["verification_method"] else "ATS_PUBLIC_API",
            job_availability_status=row["job_availability_status"] if "job_availability_status" in keys and row["job_availability_status"] else "ACTIVE",
            salary_range=row["salary_range"] if "salary_range" in keys else None,
            min_experience_years=float(row["min_experience_years"]) if "min_experience_years" in keys and row["min_experience_years"] is not None else 0.0,
            date_discovered=row["date_discovered"] if "date_discovered" in keys else None,
            date_last_checked=row["date_last_checked"] if "date_last_checked" in keys else None,
        )


def get_default_repository() -> ApplicationRepository:
    return ApplicationRepository()
