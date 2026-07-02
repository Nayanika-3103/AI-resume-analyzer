"""
backend/services/report_service.py — CSV/Excel Report Generation
"""
from __future__ import annotations

import csv
import io
from typing import Any, Optional

from backend.repositories import analysis_repo, candidate_repo
from backend.repositories.candidate_repo import PIPELINE_STAGES


def generate_ranking_csv(company_id: int, jd_id: Optional[int] = None) -> bytes:
    """Generate a ranking CSV for all candidates. Returns bytes."""
    rows, _ = candidate_repo.list_candidates(
        company_id=company_id,
        jd_id=jd_id,
        sort_by="score_desc",
        page_size=1000,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Rank", "Name", "Email", "Current Title", "Experience (yrs)",
        "Overall Score (%)", "Skill Match (%)", "Semantic Match (%)",
        "Recommendation", "Pipeline Stage", "GitHub", "LinkedIn",
        "Reasoning", "Uploaded At"
    ])

    for i, row in enumerate(rows, 1):
        writer.writerow([
            i,
            row.get("name", ""),
            row.get("email", ""),
            row.get("current_title", ""),
            row.get("experience_years", 0),
            round(float(row.get("overall_score", 0)) * 100, 1),
            round(float(row.get("skill_match", 0)) * 100, 1),
            round(float(row.get("semantic_match", 0)) * 100, 1),
            row.get("recommendation", ""),
            row.get("pipeline_stage", ""),
            row.get("github", ""),
            row.get("linkedin", ""),
            row.get("reasoning", ""),
            row.get("created_at", ""),
        ])

    return output.getvalue().encode("utf-8")


def generate_pipeline_csv(company_id: int, jd_id: Optional[int] = None) -> bytes:
    """Generate a pipeline status CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Stage", "Candidate Count"])

    funnel = analysis_repo.get_pipeline_funnel(company_id, jd_id)
    for stage, count in zip(funnel["stages"], funnel["counts"]):
        writer.writerow([stage, count])

    return output.getvalue().encode("utf-8")


def generate_analytics_csv(company_id: int, jd_id: Optional[int] = None) -> bytes:
    """Generate an analytics summary CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    # KPI section
    kpis = analysis_repo.get_kpi_counts(company_id, jd_id)
    writer.writerow(["=== Dashboard KPIs ==="])
    writer.writerow(["Metric", "Value"])
    for k, v in kpis.items():
        writer.writerow([k, v])
    writer.writerow([])

    # Score distribution
    sd = analysis_repo.get_score_distribution(company_id, jd_id)
    writer.writerow(["=== Score Distribution ==="])
    writer.writerow(["Range", "Count"])
    for bucket, count in zip(sd["buckets"], sd["counts"]):
        writer.writerow([bucket, count])
    writer.writerow([])

    # Missing skills
    ms = analysis_repo.get_missing_skills_frequency(company_id, jd_id)
    writer.writerow(["=== Most Missing Skills ==="])
    writer.writerow(["Skill", "Frequency"])
    for skill, count in zip(ms.get("skills", []), ms.get("counts", [])):
        writer.writerow([skill, count])

    return output.getvalue().encode("utf-8")


def generate_candidate_report(candidate_db_id: int) -> bytes:
    """Generate a single candidate CSV report."""
    candidate = candidate_repo.get_candidate(candidate_db_id)
    if not candidate:
        return b"Candidate not found."

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Candidate Report"])
    writer.writerow([])

    analysis = candidate.get("analysis") or {}
    writer.writerow(["Field", "Value"])
    writer.writerow(["Name", candidate.get("name", "")])
    writer.writerow(["Email", candidate.get("email", "")])
    writer.writerow(["Phone", candidate.get("phone", "")])
    writer.writerow(["Title", candidate.get("current_title", "")])
    writer.writerow(["Experience (yrs)", candidate.get("experience_years", 0)])
    writer.writerow(["GitHub", candidate.get("github", "")])
    writer.writerow(["LinkedIn", candidate.get("linkedin", "")])
    writer.writerow(["Overall Score", f"{float(analysis.get('overall_score', 0)) * 100:.1f}%"])
    writer.writerow(["Skill Match", f"{float(analysis.get('skill_match', 0)) * 100:.1f}%"])
    writer.writerow(["Semantic Match", f"{float(analysis.get('semantic_match', 0)) * 100:.1f}%"])
    writer.writerow(["Recommendation", analysis.get("recommendation", "")])
    writer.writerow(["Pipeline Stage", candidate.get("pipeline_stage", "")])
    writer.writerow(["AI Summary", analysis.get("ai_summary", "")])
    writer.writerow(["Reasoning", analysis.get("reasoning", "")])
    writer.writerow([])

    skills = candidate.get("skills", [])
    writer.writerow(["=== Skills ==="])
    writer.writerow(["Skill", "Proficiency", "Duration (months)"])
    for s in skills:
        writer.writerow([s.get("name", ""), s.get("proficiency", ""), s.get("duration_months", 0)])

    return output.getvalue().encode("utf-8")
