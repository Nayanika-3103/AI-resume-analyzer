"""
backend/repositories/jd_repo.py — Job Description CRUD
"""
from __future__ import annotations

from typing import Any, Optional

from backend.database.db import get_db


def create_jd(
    company_id: int,
    created_by: int,
    title: str,
    description: str,
    requirements: str = "",
) -> int:
    """Insert a new job description. Returns new jd_id."""
    with get_db() as db:
        cur = db.execute(
            """INSERT INTO job_descriptions (company_id, created_by, title, description, requirements)
               VALUES (?, ?, ?, ?, ?)""",
            (company_id, created_by, title, description, requirements),
        )
        return cur.lastrowid


def get_jd(jd_id: int) -> Optional[dict[str, Any]]:
    """Return a single JD dict or None."""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM job_descriptions WHERE id = ? LIMIT 1", (jd_id,)
        ).fetchone()
        return dict(row) if row else None


def list_jds(company_id: int) -> list[dict[str, Any]]:
    """Return all JDs for a company, newest first."""
    with get_db() as db:
        rows = db.execute(
            """SELECT jd.*, u.name as creator_name
               FROM job_descriptions jd
               LEFT JOIN users u ON jd.created_by = u.id
               WHERE jd.company_id = ?
               ORDER BY jd.created_at DESC""",
            (company_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_active_jd(company_id: int) -> Optional[dict[str, Any]]:
    """Return the currently active JD or None."""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM job_descriptions WHERE company_id = ? AND is_active = 1 LIMIT 1",
            (company_id,),
        ).fetchone()
        return dict(row) if row else None


def set_active_jd(company_id: int, jd_id: int) -> None:
    """Deactivate all JDs for company and activate the given jd_id."""
    with get_db() as db:
        db.execute(
            "UPDATE job_descriptions SET is_active = 0, updated_at = datetime('now') WHERE company_id = ?",
            (company_id,),
        )
        db.execute(
            "UPDATE job_descriptions SET is_active = 1, updated_at = datetime('now') WHERE id = ?",
            (jd_id,),
        )


def update_jd(jd_id: int, **fields) -> None:
    """Update arbitrary JD fields."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [jd_id]
    with get_db() as db:
        db.execute(
            f"UPDATE job_descriptions SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            values,
        )


def delete_jd(jd_id: int) -> None:
    """Delete a JD (cascades to candidates, analyses, etc. via foreign keys)."""
    with get_db() as db:
        db.execute("DELETE FROM job_descriptions WHERE id = ?", (jd_id,))


def increment_resume_count(jd_id: int) -> None:
    """Increment the resume_count for a JD by 1."""
    with get_db() as db:
        db.execute(
            "UPDATE job_descriptions SET resume_count = resume_count + 1 WHERE id = ?",
            (jd_id,),
        )
