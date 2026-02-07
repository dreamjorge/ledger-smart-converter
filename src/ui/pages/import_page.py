from pathlib import Path
from typing import Callable, Dict, Tuple

import pandas as pd
import streamlit as st

from services import import_service as imp


def _load_csv_if_exists(path):
    if path and Path(path).exists():
        return pd.read_csv(path)
    return None


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
    uploaded_main = None
    uploaded_pdf = None
    col1, col2 = st.columns(2)
    with col1:
        if bank_cfg.get("type") == "xlsx":
            uploaded_main = st.file_uploader(t("select_xlsx"), type=["xlsx"], help=t("help_xlsx"))
        else:
            uploaded_main = st.file_uploader(t("select_xml"), type=["xml", "csv", "xlsx"], help=t("help_xml"))
    with col2:
        uploaded_pdf = st.file_uploader(t("select_pdf"), type=["pdf"], help=t("help_pdf"))

    force_pdf_ocr = False
    if uploaded_pdf:
        force_pdf_ocr = st.checkbox(t("use_ocr"), value=False, help=t("help_ocr"))

    rules_path = config_dir / "rules.yml"
    if uploaded_main or (force_pdf_ocr and uploaded_pdf):
        if st.button(t("process_files"), type="primary"):
            with st.spinner(t("processing")):
                main_path = imp.save_uploaded_file(uploaded_main, temp_dir, "input")
                pdf_path = imp.save_uploaded_file(uploaded_pdf, temp_dir, "input")
                out_csv, out_unknown, out_suggestions = imp.resolve_output_paths(
                    data_dir=data_dir,
                    bank_label=bank_label,
                    bank_id=bank_id,
                    analytics_targets=analytics_csv_targets,
                )
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
                if res.returncode == 0:
                    st.success(t("process_complete"))
                    st.info(
                        f"""
                    {t('next_steps_title')}
                    {t('next_step_1')}
                    {t('next_step_2')}
                    {t('next_step_3')}
                    {t('next_step_4')}
                    """
                    )
                    if st.button(t("copy_to_analysis")):
                        copied, result = imp.copy_csv_to_analysis(
                            data_dir=data_dir,
                            analytics_targets=analytics_csv_targets,
                            bank_label=bank_label,
                            csv_path=out_csv,
                        )
                        if copied:
                            st.session_state[copy_feedback_key] = t("copy_success", path=result)
                            st.session_state[nav_key] = t("nav_analytics")
                            st.session_state[bank_key] = bank_label
                            st.experimental_rerun()
                        elif result == "missing_src":
                            st.warning(t("copy_error_missing"))
                        else:
                            st.warning(t("copy_error_unknown_bank"))

                    with st.expander(t("view_logs"), expanded=pdf_path is not None):
                        st.code(res.stdout, language="text")

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
                    st.error(res.stderr)
                    st.code(res.stdout, language="text")

    st.markdown("---")
    st.caption(f"{t('working_dir')}: {root_dir}")
