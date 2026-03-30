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

    rules_path = config_dir / "rules.yml"
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
                res = imp.run_import_script(
                    root_dir=root_dir,
                    src_dir=src_dir,
                    bank_id=bank_id,
                    rules_path=rules_path,
                    out_csv=out_csv,
                    out_unknown=out_unknown,
                    main_path=main_path,
                    pdf_path=pdf_path,
                    force_pdf_ocr=force_pdf_ocr,
                )
                # Store results in session_state so they persist across re-runs
                st.session_state[results_key] = {
                    "returncode": res.returncode,
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "out_csv": str(out_csv),
                    "out_unknown": str(out_unknown),
                    "out_suggestions": str(out_suggestions),
                    "pdf_path": str(pdf_path) if pdf_path else None,
                }

                # Run deduplication migration if import succeeded
                if res.returncode == 0 and out_csv.exists():
                    try:
                        st.write("🔄 Syncing with database and deduplicating...")
                        from csv_to_db_migrator import migrate_csvs_to_db_with_dedup
                        from settings import load_settings
                        settings = load_settings()
                        dedup_summary, duplicate_rows = migrate_csvs_to_db_with_dedup(
                            db_path=settings.data_dir / "ledger.db",
                            data_dir=data_dir,
                            accounts_path=config_dir / "accounts.yml",
                            csv_paths=[out_csv],
                        )
                        st.session_state[f"{results_key}_dedup"] = {
                            "inserted": dedup_summary.get("rows_inserted", 0),
                            "duplicate_rows": duplicate_rows,
                        }
                    except Exception as dedup_exc:
                        st.session_state[f"{results_key}_dedup"] = {
                            "inserted": 0,
                            "duplicate_rows": [],
                            "error": str(dedup_exc),
                        }
                
                if res.returncode == 0:
                    status.update(label=t("step_complete"), state="complete", expanded=False)
                else:
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
