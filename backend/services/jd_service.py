"""
backend/services/jd_service.py — Job Description Business Logic
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.repositories import jd_repo

logger = logging.getLogger(__name__)


def create_job_description(
    company_id: int,
    user_id: int,
    title: str,
    description: str,
    requirements: str = "",
    make_active: bool = True,
) -> int:
    """Create a new JD and optionally activate it. Returns jd_id."""
    if not title.strip():
        raise ValueError("Job title cannot be empty.")
    if not description.strip():
        raise ValueError("Job description cannot be empty.")

    jd_id = jd_repo.create_jd(
        company_id=company_id,
        created_by=user_id,
        title=title.strip(),
        description=description.strip(),
        requirements=requirements.strip(),
    )

    if make_active:
        jd_repo.set_active_jd(company_id, jd_id)
        logger.info("Created and activated JD #%d: %s", jd_id, title)
    else:
        logger.info("Created JD #%d: %s (not active)", jd_id, title)

    return jd_id


def activate_jd(company_id: int, jd_id: int) -> None:
    """Set a JD as active (deactivating all others)."""
    jd = jd_repo.get_jd(jd_id)
    if not jd or jd["company_id"] != company_id:
        raise ValueError(f"Job description #{jd_id} not found.")
    jd_repo.set_active_jd(company_id, jd_id)
    logger.info("Activated JD #%d for company #%d", jd_id, company_id)


def get_active_jd(company_id: int) -> Optional[dict[str, Any]]:
    """Return the active JD dict or None."""
    return jd_repo.get_active_jd(company_id)


def get_active_jd_text(company_id: int) -> str:
    """Return the full text of the active JD for embedding."""
    jd = jd_repo.get_active_jd(company_id)
    if not jd:
        return ""
    parts = [jd.get("title", ""), jd.get("description", ""), jd.get("requirements", "")]
    return " ".join(p for p in parts if p).strip()


def list_job_descriptions(company_id: int) -> list[dict[str, Any]]:
    """Return all JDs for a company."""
    return jd_repo.list_jds(company_id)


def update_job_description(company_id: int, jd_id: int, title: str, description: str, requirements: str = "") -> None:
    """Update a JD."""
    jd = jd_repo.get_jd(jd_id)
    if not jd or jd["company_id"] != company_id:
        raise ValueError(f"Job description #{jd_id} not found.")
    jd_repo.update_jd(jd_id, title=title.strip(), description=description.strip(), requirements=requirements.strip())


def delete_job_description(company_id: int, jd_id: int) -> None:
    """Delete a JD."""
    jd = jd_repo.get_jd(jd_id)
    if not jd or jd["company_id"] != company_id:
        raise ValueError(f"Job description #{jd_id} not found.")
    jd_repo.delete_jd(jd_id)
    logger.info("Deleted JD #%d", jd_id)


def duplicate_job_description(company_id: int, user_id: int, jd_id: int) -> int:
    """Duplicate an existing JD. Returns new jd_id."""
    jd = jd_repo.get_jd(jd_id)
    if not jd or jd["company_id"] != company_id:
        raise ValueError(f"Job description #{jd_id} not found.")
    new_id = jd_repo.create_jd(
        company_id=company_id,
        created_by=user_id,
        title=f"Copy of {jd['title']}",
        description=jd["description"],
        requirements=jd.get("requirements", ""),
    )
    logger.info("Duplicated JD #%d → #%d", jd_id, new_id)
    return new_id
