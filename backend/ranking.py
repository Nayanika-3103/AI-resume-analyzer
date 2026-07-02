"""
backend/ranking.py — FAISS Vector Indexing, Constraint Verification & Output Formatting
========================================================================================
Phase 3 upgrade: adds ``VectorRanker`` for GPU/CPU inner-product search via
``faiss.IndexFlatIP``.  All Phase 1 & 2 functions (``sort_and_format_submission``,
``format_candidate_for_api``, ``generate_submission_csv``) are preserved verbatim.

Architecture
------------
::

    VectorRanker.build_index(embeddings)   ← L2-normalise → IndexFlatIP.add()
    VectorRanker.query_top_k(jd_vec, k=500)
        → (indices: np.ndarray[int64], scores: np.ndarray[float32])

Because vectors are L2-normalised before insertion, IndexFlatIP inner-product
equals cosine similarity.  This gives an exact, deterministic top-k in
O(N × D) time with no approximate quantisation error — suitable for 100 k
candidates at D=384 on a single CPU core within the 5-minute budget.

Classes
-------
VectorRanker
    Owns one FAISS index; thread-safe for concurrent reads after build.

Functions (Phase 1 / 2 — unchanged)
-------------------------------------
sort_and_format_submission
format_candidate_for_api
generate_submission_csv
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Phase 1 / 2 constants (unchanged)
# ---------------------------------------------------------------------------

_REQUIRED_SCORED_FIELDS: tuple[str, ...] = ("candidate_id", "score")
_TOP_N: int = 100

_CSV_COLUMNS: tuple[str, ...] = (
    "rank",
    "candidate_id",
    "name",
    "overall_score",
    "skill_match",
    "semantic_match",
    "experience_years",
    "top_skills",
    "status",
    "reason",
    "resume_summary",
    "github",
    "linkedin",
    "why_selected",
    "missing_skills",
    "best_alternate_roles",
)


# ===========================================================================
# VectorRanker  (Phase 3 — new)
# ===========================================================================


class VectorRanker:
    """FAISS-backed inner-product ranker for fast candidate pre-selection.

    Workflow
    --------
    1. Call :meth:`build_index` once with the matrix of all candidate
       embeddings to construct an in-memory ``IndexFlatIP``.
    2. Call :meth:`query_top_k` with the JD embedding to retrieve the top-k
       candidate indices and their cosine similarity scores in microseconds.

    Parameters
    ----------
    embedding_dim : int
        Dimensionality of the embedding space.  Must match the model output
        (384 for ``all-MiniLM-L6-v2``).

    Attributes
    ----------
    index : faiss.IndexFlatIP | None
        The FAISS index; ``None`` until :meth:`build_index` is called.
    n_indexed : int
        Number of vectors currently stored in the index.
    """

    def __init__(self, embedding_dim: int = 384) -> None:
        self.embedding_dim: int = embedding_dim
        self.index: Optional[Any] = None   # faiss.IndexFlatIP after build
        self.n_indexed: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_index(self, candidate_embeddings: np.ndarray) -> None:
        """Construct an in-memory FAISS IndexFlatIP from *candidate_embeddings*.

        Each row is L2-normalised in-place on a private copy so that
        inner-product equals cosine similarity.  The original array is
        never mutated.

        Parameters
        ----------
        candidate_embeddings:
            Shape ``(N, D)`` float32 or float64 array.  Each row is one
            candidate's embedding vector.

        Raises
        ------
        ValueError
            If *candidate_embeddings* is empty or has a mismatched column
            count relative to ``self.embedding_dim``.
        RuntimeError
            If the ``faiss`` package is not importable.
        """
        try:
            import faiss  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "faiss-cpu is required for VectorRanker. "
                "Install it with:  pip install faiss-cpu"
            ) from exc

        if candidate_embeddings.ndim != 2:
            raise ValueError(
                f"candidate_embeddings must be 2-D (N, D), "
                f"got shape {candidate_embeddings.shape}."
            )

        n, d = candidate_embeddings.shape
        if n == 0:
            raise ValueError("candidate_embeddings is empty — nothing to index.")
        if d != self.embedding_dim:
            logger.warning(
                "build_index: column count %d ≠ embedding_dim %d; "
                "updating embedding_dim to %d.",
                d, self.embedding_dim, d,
            )
            self.embedding_dim = d

        # Work on a contiguous float32 copy to satisfy FAISS memory layout.
        vectors: np.ndarray = np.ascontiguousarray(
            candidate_embeddings, dtype=np.float32
        )

        # L2-normalise: after this, inner-product ≡ cosine similarity.
        faiss.normalize_L2(vectors)

        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.index.add(vectors)  # type: ignore[union-attr]
        self.n_indexed = self.index.ntotal

        logger.info(
            "VectorRanker: index built — %d vectors, dim=%d.",
            self.n_indexed, self.embedding_dim,
        )

    def query_top_k(
        self,
        jd_embedding: np.ndarray,
        k: int = 500,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Return the top-*k* candidate indices and their cosine scores.

        Parameters
        ----------
        jd_embedding:
            1-D or 2-D array of shape ``(D,)`` or ``(1, D)``.
        k:
            Number of nearest neighbours to retrieve.  Clamped to
            ``self.n_indexed`` so callers never need to guard this.

        Returns
        -------
        indices : np.ndarray, shape (k,), dtype int64
            Row indices into the original ``candidate_embeddings`` matrix.
        scores : np.ndarray, shape (k,), dtype float32
            Cosine similarity scores in ``[0.0, 1.0]``, descending order.

        Raises
        ------
        RuntimeError
            If :meth:`build_index` has not been called yet.
        """
        if self.index is None:
            raise RuntimeError(
                "VectorRanker.build_index() must be called before query_top_k()."
            )

        # ── Normalise query vector ────────────────────────────────────────
        try:
            import faiss  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("faiss-cpu not available.") from exc

        query: np.ndarray = np.ascontiguousarray(
            jd_embedding, dtype=np.float32
        ).reshape(1, -1)
        faiss.normalize_L2(query)

        # ── Clamp k to available candidates ──────────────────────────────
        effective_k: int = min(k, self.n_indexed)

        # ── Search ───────────────────────────────────────────────────────
        scores_2d, indices_2d = self.index.search(query, effective_k)

        indices: np.ndarray = indices_2d[0]   # shape (k,)
        scores: np.ndarray = scores_2d[0]     # shape (k,)

        # Clip scores to [0, 1] — small fp rounding can produce 1.000002.
        scores = np.clip(scores, 0.0, 1.0)

        logger.debug(
            "VectorRanker.query_top_k: k=%d, top_score=%.4f, bottom_score=%.4f",
            effective_k,
            float(scores[0]) if len(scores) > 0 else 0.0,
            float(scores[-1]) if len(scores) > 0 else 0.0,
        )

        return indices, scores


# ===========================================================================
# Phase 1 / 2 functions (unchanged)
# ===========================================================================


def sort_and_format_submission(
    scored_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort, rank, and cap scored candidates per hackathon validator rules.

    Sorting contract
    ----------------
    1. Primary:   ``score`` **descending**.
    2. Secondary: ``candidate_id`` **ascending** (alphanumeric tie-breaker).

    Parameters
    ----------
    scored_candidates:
        List of dicts, each containing at minimum:
        ``{"candidate_id": str, "score": float, "reasoning": str}``.

    Returns
    -------
    list[dict[str, Any]]
        Top-``_TOP_N`` candidates with an additional ``"rank"`` key
        (1-indexed).  Returns an empty list for empty input.

    Raises
    ------
    ValueError
        If any candidate dict is missing ``"candidate_id"`` or ``"score"``.
    """
    if not scored_candidates:
        return []

    # ── Validate required fields ──────────────────────────────────────────
    for entry in scored_candidates:
        for field in _REQUIRED_SCORED_FIELDS:
            if field not in entry:
                raise ValueError(
                    f"Scored candidate is missing required field '{field}': {entry!r}"
                )

    # ── Sort: primary score↓, secondary candidate_id↑ ────────────────────
    sorted_candidates = sorted(
        scored_candidates,
        key=lambda c: (-c["score"], c["candidate_id"]),
    )

    # ── Cap to top-N and assign ranks ─────────────────────────────────────
    top_n = sorted_candidates[:_TOP_N]
    for rank, candidate in enumerate(top_n, start=1):
        candidate["rank"] = rank

    return top_n


def format_candidate_for_api(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Transform an enriched candidate dict into the frontend API shape."""
    profile: dict[str, Any] = candidate.get("profile", {}) or {}
    analysis: dict[str, Any] = candidate.get("analysis", {}) or {}

    raw_skills: list[dict[str, Any]] = candidate.get("skills", []) or []
    sorted_skills = sorted(
        raw_skills,
        key=lambda s: s.get("duration_months", 0),
        reverse=True,
    )
    top_skills: list[str] = [s.get("name", "") for s in sorted_skills[:5]]
    certifications: list[Any] = candidate.get("certifications", []) or []

    return {
        "rank": candidate.get("rank"),
        "candidate_id": candidate.get("candidate_id", ""),
        "name": candidate.get("name", ""),
        "overall_score": round(candidate.get("score", 0.0), 4),
        "skill_match": candidate.get("skill_match", 0.0),
        "semantic_match": candidate.get("semantic_match", 0.0),
        "experience_years": candidate.get("experience_years", 0.0),
        "top_skills": top_skills,
        "status": candidate.get("status", "UNKNOWN"),
        "reason": candidate.get("reasoning", ""),
        "resume_summary": profile.get("summary", ""),
        "skills": raw_skills,
        "experience": candidate.get("experience", []),
        "education": candidate.get("education", []),
        "projects": candidate.get("projects", []),
        "certifications": certifications,
        "github": profile.get("github", ""),
        "linkedin": profile.get("linkedin", ""),
        "why_selected": analysis.get("why_selected", ""),
        "missing_skills": analysis.get("missing_skills", []),
        "best_alternate_roles": analysis.get("best_alternate_roles", []),
    }


def generate_submission_csv(
    ranked_candidates: list[dict[str, Any]],
) -> str:
    """Render the top-100 ranked candidates as a ``sample_submission.csv`` string."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=list(_CSV_COLUMNS),
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()

    for candidate in ranked_candidates:
        api_row = format_candidate_for_api(candidate)
        api_row["top_skills"] = " | ".join(api_row.get("top_skills", []))
        api_row["missing_skills"] = " | ".join(
            str(s) for s in api_row.get("missing_skills", [])
        )
        api_row["best_alternate_roles"] = " | ".join(
            str(r) for r in api_row.get("best_alternate_roles", [])
        )
        writer.writerow(api_row)

    return output.getvalue()
