from pathlib import Path

import streamlit as st
import yaml

import ml_categorizer as ml
from settings import load_settings
from translations import TRANSLATIONS
from ui.pages.analytics_page import render_analytics_dashboard
from ui.pages.import_page import render_import_page

# Initialize Session State for Language
if "lang" not in st.session_state:
    st.session_state.lang = "en"


def t(key, **kwargs):
    """Helper to get translated string."""
    lang = st.session_state.lang
    text = TRANSLATIONS[lang].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def tc(category):
    """Helper to get translated category name."""
    if not category:
        return category
    key = f"cat_{category.lower()}"
    return t(key)


st.set_page_config(
    page_title=t("page_title"),
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed",  # Sidebar is info-only; controls live in main content
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Ledger Smart Converter - Bank statement importer with ML categorization"
    }
)

def load_css(file_path: Path):
    """Load custom CSS from an external file."""
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.error(f"CSS file not found: {file_path}")

SETTINGS = load_settings()
ROOT_DIR = SETTINGS.root_dir
CONFIG_DIR = SETTINGS.config_dir
DATA_DIR = SETTINGS.data_dir
SRC_DIR = ROOT_DIR / "src"

# Mobile viewport meta tag for proper scaling
VIEWPORT_META = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
"""

st.markdown(VIEWPORT_META, unsafe_allow_html=True)
load_css(SRC_DIR / "ui" / "style.css")
TEMP_DIR = SETTINGS.temp_dir

ANALYTICS_CSV_TARGETS = {
    "Santander LikeU": ("santander", "firefly_likeu.csv"),
    "HSBC Mexico": ("hsbc", "firefly_hsbc.csv"),
}


@st.cache_data
def get_banks_config():
    rules_path = CONFIG_DIR / "rules.yml"
    if rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            return cfg.get("banks", {})
    return {}


NAV_KEY = "nav_page"
BANK_KEY = "bank_select"
COPY_FEEDBACK_KEY = "copy_feedback"
TEMP_DIR.mkdir(exist_ok=True)


@st.cache_resource
def get_ml_engine():
    engine = ml.TransactionCategorizer()
    if engine.load_model():
        return engine
    ml.train_global_model()
    engine.load_model()
    return engine


ML_ENGINE = get_ml_engine()


def build_bank_map(banks_cfg, t_func):
    """Build a display-name → bank-id mapping from config.

    Args:
        banks_cfg: Dict of bank configs from rules.yml, or empty dict.
        t_func: Translation helper callable.

    Returns:
        Dict mapping display label to bank_id.
    """
    if banks_cfg:
        return {cfg.get("display_name", bid): bid for bid, cfg in banks_cfg.items()}
    return {t_func("bank_santander"): "santander_likeu", t_func("bank_hsbc"): "hsbc"}


def main():
    # --- Top bar: header + language/bank controls (always visible, no sidebar needed) ---
    col_title, col_lang, col_bank = st.columns([3, 1, 1])
    with col_title:
        st.markdown('<h1 class="premium-header">Ledger Smart Converter</h1>', unsafe_allow_html=True)
        st.markdown(f'<p style="color: var(--text-muted); font-size: 1.1rem; margin-top: -1rem;">{t("app_title")}</p>', unsafe_allow_html=True)

    lang_options = {"🇺🇸 EN": "en", "🇲🇽 ES": "es"}
    with col_lang:
        selected_lang_label = st.selectbox(
            t("language_select"),
            options=list(lang_options.keys()),
            index=0 if st.session_state.lang == "en" else 1,
            key="lang_selector",
            label_visibility="collapsed",
        )
    new_lang = lang_options[selected_lang_label]
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        for key in (NAV_KEY, BANK_KEY, COPY_FEEDBACK_KEY):
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    banks_cfg = get_banks_config()
    bank_map = build_bank_map(banks_cfg, t)
    bank_options = list(bank_map.keys())
    if BANK_KEY not in st.session_state or st.session_state[BANK_KEY] not in bank_options:
        st.session_state[BANK_KEY] = bank_options[0]
    with col_bank:
        bank_label = st.selectbox(
            t("select_bank"),
            options=bank_options,
            key=BANK_KEY,
            label_visibility="collapsed",
        )
    bank_id = bank_map[bank_label]
    bank_cfg = banks_cfg.get(bank_id, {})

    # --- Sidebar: info-only (optional, collapsible) ---
    st.sidebar.title(t("sidebar_welcome"))
    st.sidebar.markdown(t("sidebar_desc"))
    rules_path = CONFIG_DIR / "rules.yml"
    if rules_path.exists():
        st.sidebar.success(f"{t('loaded_rules')}: {rules_path.name}")
    else:
        st.sidebar.error(t("no_rules"))
    st.sidebar.info(t("sidebar_info"))

    # --- Main navigation via tabs ---
    tab_import, tab_analytics = st.tabs([t("nav_import"), t("nav_analytics")])

    with tab_import:
        render_import_page(
            t=t,
            root_dir=ROOT_DIR,
            src_dir=SRC_DIR,
            config_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
            temp_dir=TEMP_DIR,
            bank_label=bank_label,
            bank_id=bank_id,
            bank_cfg=bank_cfg,
            analytics_csv_targets=ANALYTICS_CSV_TARGETS,
            copy_feedback_key=COPY_FEEDBACK_KEY,
            nav_key=NAV_KEY,
            bank_key=BANK_KEY,
        )

    with tab_analytics:
        render_analytics_dashboard(
            t=t,
            tc=tc,
            config_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
            copy_feedback_key=COPY_FEEDBACK_KEY,
            ml_engine=ML_ENGINE,
        )


if __name__ == "__main__":
    main()
