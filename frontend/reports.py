"""
reports.py
Download center for CSV exports — ranking, analytics, pipeline, individual candidates.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import io
from components import card_open, card_close
from backend.services.report_service import generate_ranking_csv, generate_pipeline_csv, generate_analytics_csv


def render(t: dict):
    company_id = st.session_state.get("company_id")
    active_jd = st.session_state.get("active_jd")
    jd_id = active_jd["id"] if active_jd else None
    jd_label = active_jd["title"] if active_jd else "All JDs"

    st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        card_open()
        st.markdown(
            f"""
            <div style="text-align:center;padding:0.5rem 0 1rem 0;">
                <div style="font-size:2.5rem;margin-bottom:0.6rem;">🏆</div>
                <div style="font-size:1rem;font-weight:800;color:{t['text']};">Candidate Ranking</div>
                <div style="font-size:0.8rem;color:{t['text_secondary']};margin:0.4rem 0 1rem 0;">
                    All candidates sorted by AI match score<br>JD: {jd_label}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        csv_bytes = generate_ranking_csv(company_id, jd_id)
        df=pd.read_csv(io.BytesIO(csv_bytes))
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')   
        st.download_button(
            "📥 Download Ranking Excel (XLSX)",
            data=excel_buffer.getvalue(),
            file_name="candidate_ranking.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_ranking_xlsx",
        )
        card_close()

    with c2:
        card_open()
        st.markdown(
            f"""
            <div style="text-align:center;padding:0.5rem 0 1rem 0;">
                <div style="font-size:2.5rem;margin-bottom:0.6rem;">📊</div>
                <div style="font-size:1rem;font-weight:800;color:{t['text']};">Analytics Summary</div>
                <div style="font-size:0.8rem;color:{t['text_secondary']};margin:0.4rem 0 1rem 0;">
                    Score distribution, skills, education breakdown<br>JD: {jd_label}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        analytics_bytes = generate_analytics_csv(company_id, jd_id)
        st.download_button(
            "📥 Download Analytics CSV",
            data=analytics_bytes,
            file_name="analytics_summary.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_analytics",
        )
        card_close()

    with c3:
        card_open()
        st.markdown(
            f"""
            <div style="text-align:center;padding:0.5rem 0 1rem 0;">
                <div style="font-size:2.5rem;margin-bottom:0.6rem;">🔄</div>
                <div style="font-size:1rem;font-weight:800;color:{t['text']};">Pipeline Report</div>
                <div style="font-size:0.8rem;color:{t['text_secondary']};margin:0.4rem 0 1rem 0;">
                    Candidate counts per hiring stage<br>JD: {jd_label}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        pipeline_bytes = generate_pipeline_csv(company_id, jd_id)
        st.download_button(
            "📥 Download Pipeline CSV",
            data=pipeline_bytes,
            file_name="pipeline_report.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_pipeline",
        )
        card_close()

    # ── Individual candidate report ────────────────────────────────────────────
    st.markdown("<div style='height:0.3rem;'></div>", unsafe_allow_html=True)
    card_open()
    st.markdown('<div class="arx-section-title">📋 Individual Candidate Report</div>', unsafe_allow_html=True)

    selected_id = st.session_state.get("selected_candidate_id")
    if selected_id:
        from backend.services.report_service import generate_candidate_report
        from backend.repositories.candidate_repo import get_candidate
        c = get_candidate(selected_id)
        if c:
            name = c.get("name", "Candidate")
            st.markdown(
                f'<div style="font-size:0.85rem;color:{t["text_secondary"]};margin-bottom:0.8rem;">'
                f'Currently selected: <b>{name}</b></div>',
                unsafe_allow_html=True,
            )
            report_bytes = generate_candidate_report(selected_id)
            st.download_button(
                f"📥 Download {name}'s Report",
                data=report_bytes,
                file_name=f"{name.replace(' ','_')}_report.csv",
                mime="text/csv",
                key="dl_candidate",
            )
    else:
        st.markdown(
            f'<div style="color:{t["text_muted"]};font-size:0.85rem;">'
            f'Select a candidate from the Ranked Candidates page to download their individual report.</div>',
            unsafe_allow_html=True,
        )
        if st.button("→ Go to Ranked Candidates", key="reports_goto_rank"):
            st.session_state.page = "Ranked Candidates"
            st.rerun()
    card_close()
