from __future__ import annotations
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import streamlit as st
from services import import_service as imp
from ui.components.import_components import render_file_uploaders, render_import_results


def _results_key(bank_id: str) -> str:
    return f"import_results_{bank_id}"


def render_import_page(
    *,
    t: Callable,
    root_dir: Path,
    src_dir: Path,
    config_dir: Path,
    data_dir: Path,
    temp_dir: Path,
    bank_label: str,
    bank_id: str,
    bank_cfg: Dict,
    analytics_csv_targets: Dict[str, Tuple[str, str]],
    copy_feedback_key: str,
    nav_key: str,
    bank_key: str,
    import_use_case: ImportStatement,
):
    with st.expander(t("quick_start"), expanded=bank_id == "santander_likeu"):
        st.write(t("welcome_bank", bank=bank_label))
        st.write(t("steps_desc"))
        file_type_label = "Excel" if bank_cfg.get("type") == "xlsx" else "XML"
        st.markdown(t("step_1", file_type=file_type_label))
        st.markdown(t("step_2"))
        st.markdown(t("step_3"))
        st.markdown(t("step_4"))
        if bank_id == "santander_likeu":
            st.info(t("tip_santander"))
        else:
            st.info(t("tip_hsbc"))

    st.header(t("import_header", bank=bank_label))

    # Mobile tip
    with st.expander("📱 Mobile Tips", expanded=False):
        st.markdown("""
        - Files upload best in landscape mode
        - Ensure files are under 200MB
        - Processing may take 30-60 seconds
        - Keep screen active during upload
        """)

    # Use extracted component for file uploaders
    uploaded_main, uploaded_pdf = render_file_uploaders(t, bank_cfg)

    # Clear cached results when a new file is uploaded
    results_key = _results_key(bank_id)
    if uploaded_main is not None and st.session_state.get(f"{results_key}_file_name") != uploaded_main.name:
        st.session_state.pop(results_key, None)
        st.session_state.pop(f"{results_key}_dedup", None)
        st.session_state[f"{results_key}_file_name"] = uploaded_main.name

    force_pdf_ocr = False
    if uploaded_pdf:
        force_pdf_ocr = st.checkbox(t("use_ocr"), value=False, help=t("help_ocr"))

    if uploaded_main or (force_pdf_ocr and uploaded_pdf):
        if st.button(t("process_files"), type="primary"):
            # Use st.status for better real-time feedback
            with st.status(t("processing_status"), expanded=True) as status:
                st.write(t("step_parsing"))
                main_path = imp.save_uploaded_file(uploaded_main, temp_dir, "input")
                pdf_path = imp.save_uploaded_file(uploaded_pdf, temp_dir, "input")
                
                out_csv, out_unknown, out_suggestions = imp.resolve_output_paths(
                    data_dir=data_dir,
                    bank_label=bank_label,
                    bank_id=bank_id,
                    analytics_targets=analytics_csv_targets,
                )
                
                st.write(t("step_processing"))
                try:
                    res = import_use_case.execute(
                        bank_id=bank_id,
                        data_path=main_path,
                        pdf_path=pdf_path,
                        use_ocr=force_pdf_ocr,
                        strict=False
                    )

                    # For backward compatibility with render_import_results, 
                    # we write the legacy CSVs if they were expected.
                    import pandas as pd
                    
                    # 1. Main results CSV (Firefly format)
                    df_proc = pd.DataFrame(res.processed_transactions)
                    df_proc.to_csv(out_csv, index=False)
                    
                    # 2. Unknown merchants CSV
                    df_unk = pd.DataFrame(res.unknown_merchants)
                    df_unk.to_csv(out_unknown, index=False)
                    
                    # Store results in session_state
                    st.session_state[results_key] = {
                        "returncode": 0,
                        "stdout": f"Import ID: {res.import_id}\nProcessed: {res.total_processed}\nInserted: {res.inserted}\nSkipped: {res.skipped_duplicates}",
                        "stderr": "",
                        "out_csv": str(out_csv),
                        "out_unknown": str(out_unknown),
                        "out_suggestions": str(out_suggestions),
                        "pdf_path": str(pdf_path) if pdf_path else None,
                    }
                    
                    st.session_state[f"{results_key}_dedup"] = {
                        "inserted": res.inserted,
                        "duplicate_rows": [], # Deduplication is now handled via INSERT OR IGNORE in this phase
                    }
                    status.update(label=t("step_complete"), state="complete", expanded=False)
                    
                except Exception as e:
                    st.error(f"Import failed: {str(e)}")
                    st.session_state[results_key] = {
                        "returncode": 1,
                        "stdout": "",
                        "stderr": str(e),
                        "out_csv": str(out_csv),
                        "out_unknown": str(out_unknown),
                        "out_suggestions": str(out_suggestions),
                    }
                    status.update(label=t("error_processing"), state="error", expanded=True)

    # Render persisted results using extracted component
    results = st.session_state.get(results_key)
    if results:
        render_import_results(
            t=t,
            results=results,
            results_key=results_key,
            bank_id=bank_id,
            bank_label=bank_label,
            data_dir=data_dir,
            analytics_csv_targets=analytics_csv_targets,
            copy_feedback_key=copy_feedback_key,
            nav_key=nav_key,
        )

    st.markdown("---")
    st.caption(f"{t('working_dir')}: {root_dir}")
