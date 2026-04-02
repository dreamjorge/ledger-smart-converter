# -*- coding: utf-8 -*-
"""Components for the import page.

This module contains UI components for file uploading, result rendering,
and deduplication review in the import workflow.
"""
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import streamlit as st
from services import import_service as imp


def _load_csv_if_exists(path):
    import pandas as pd
    if path and Path(path).exists():
        return pd.read_csv(path)
    return None


def render_file_uploaders(t: Callable, bank_cfg: Dict) -> Tuple[Optional[st.runtime.uploaded_file_manager.UploadedFile], Optional[st.runtime.uploaded_file_manager.UploadedFile]]:
    """Render main and PDF file uploaders.

    Returns:
        Tuple of (uploaded_main, uploaded_pdf)
    """
    col1, col2 = st.columns([1, 1])
    uploaded_main = None
    uploaded_pdf = None

    with col1:
        if bank_cfg.get("type") == "xlsx":
            uploaded_main = st.file_uploader(t("select_xlsx"), type=["xlsx"], help=t("help_xlsx"), key="main_uploader")
        else:
            uploaded_main = st.file_uploader(t("select_xml"), type=["xml", "csv", "xlsx"], help=t("help_xml"), key="main_uploader")
    with col2:
        uploaded_pdf = st.file_uploader(t("select_pdf"), type=["pdf"], help=t("help_pdf"), key="pdf_uploader")
    
    return uploaded_main, uploaded_pdf


def render_dedup_review(t: Callable, results_key: str, duplicate_rows: list):
    """Render the deduplication review UI with action selectors.
    
    Args:
        t: Translation function.
        results_key: Session state key for results.
        duplicate_rows: List of duplicate transaction rows.
    """
    st.warning(t("dedup_rows_skipped", n=len(duplicate_rows)))
    with st.expander(t("dedup_review_title")):
        decisions: Dict[str, str] = {}
        action_options = ["skip", "overwrite", "keep_both"]
        action_labels = {
            "skip": t("dedup_action_skip"),
            "overwrite": t("dedup_action_overwrite"),
            "keep_both": t("dedup_action_keep_both"),
        }
        for row in duplicate_rows[:50]:
            h = row.get("source_hash", "")
            col_info, col_action = st.columns([3, 1])
            col_info.write(
                f"**{row.get('date', '')}** | {row.get('description', '')} | `{row.get('amount', '')}`"
            )
            chosen = col_action.selectbox(
                label=f"Action for {h}",
                options=action_options,
                format_func=lambda x: action_labels[x],
                key=f"dedup_{h}",
                label_visibility="collapsed",
            )
            decisions[h] = chosen

        if len(duplicate_rows) > 50:
            st.caption(f"Showing first 50 of {len(duplicate_rows)} duplicates.")

        if st.button(t("dedup_apply_decisions"), type="primary"):
            try:
                from services.dedup_service import resolve_duplicates
                from services.db_service import DatabaseService
                from settings import load_settings
                settings = load_settings()
                db = DatabaseService(db_path=settings.data_dir / "ledger.db")
                counts = resolve_duplicates(
                    db=db,
                    duplicate_rows=duplicate_rows,
                    decisions=decisions,
                )
                st.success(t(
                    "dedup_resolved",
                    overwritten=counts["overwritten"],
                    kept_both=counts["kept_both"],
                    skipped=counts["skipped"],
                ))
                # Clear dedup state after resolution
                st.session_state.pop(f"{results_key}_dedup", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to apply decisions: {exc}")


def render_import_results(
    t: Callable,
    results: Dict,
    results_key: str,
    bank_id: str,
    bank_label: str,
    data_dir: Path,
    analytics_csv_targets: Dict,
    copy_feedback_key: str,
    nav_key: str,
):
    """Render the results of an import process."""
    out_csv = Path(results["out_csv"])
    out_unknown = Path(results["out_unknown"])
    out_suggestions = Path(results["out_suggestions"])
    had_pdf = bool(results.get("pdf_path"))

    if results["returncode"] == 0:
        st.success(t("process_complete"))

        # Deduplication summary
        dedup = st.session_state.get(f"{results_key}_dedup")
        if dedup and not dedup.get("error"):
            st.info(t("dedup_rows_inserted", n=dedup["inserted"]))
            duplicate_rows = dedup.get("duplicate_rows", [])
            if duplicate_rows:
                render_dedup_review(t, results_key, duplicate_rows)
        elif dedup and dedup.get("error"):
            st.warning(f"DB sync skipped: {dedup['error']}")

        st.info(
            f"""
        {t('next_steps_title')}
        {t('next_step_1')}
        {t('next_step_2')}
        {t('next_step_3')}
        {t('next_step_4')}
        """
        )
        if st.button(t("copy_to_analysis"), key=f"copy_btn_{bank_id}"):
            copied, result = imp.copy_csv_to_analysis(
                data_dir=data_dir,
                analytics_targets=analytics_csv_targets,
                bank_label=bank_label,
                csv_path=out_csv,
                bank_id=bank_id,
            )
            if copied:
                st.session_state[copy_feedback_key] = t("copy_success", path=result)
                st.session_state[nav_key] = "analytics"
                st.rerun()
            elif result == "missing_src":
                st.warning(t("copy_error_missing"))
            else:
                st.warning(t("copy_error_unknown_bank"))

        with st.expander(t("view_logs"), expanded=had_pdf):
            st.code(results["stdout"], language="text")

        tab1, tab2, tab3 = st.tabs([t("tab_csv"), t("tab_unknown"), t("tab_suggestions")])
        with tab1:
            df_csv = _load_csv_if_exists(out_csv)
            if df_csv is not None:
                st.dataframe(df_csv, width="stretch")
                with open(out_csv, "rb") as f:
                    st.download_button(t("download_csv"), f, "firefly_import.csv", "text/csv")
            else:
                st.warning(t("no_csv"))
        with tab2:
            df_unk = _load_csv_if_exists(out_unknown)
            if df_unk is not None:
                st.dataframe(df_unk, width="stretch")
            else:
                st.info(t("no_unknown"))
        with tab3:
            if out_suggestions.exists():
                with open(out_suggestions, "r", encoding="utf-8") as f:
                    sugg_content = f.read()
                st.code(sugg_content, language="yaml")
                st.download_button(t("download_suggestions"), sugg_content, "suggestions.yml", "text/yaml")
            else:
                st.info(t("no_suggestions"))
    else:
        st.error(t("error_processing"))
        st.error(results["stderr"])
        st.code(results["stdout"], language="text")
