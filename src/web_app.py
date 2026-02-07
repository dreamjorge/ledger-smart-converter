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


st.set_page_config(page_title=t("page_title"), page_icon="💳", layout="wide")

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    :root {
        --primary: #6366f1;
        --primary-hover: #4f46e5;
        --bg-dark: #0f172a;
        --card-bg: rgba(30, 41, 59, 0.7);
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --border: rgba(255, 255, 255, 0.1);
    }

    .main {
        background-color: var(--bg-dark);
        font-family: 'Outfit', sans-serif;
        color: var(--text-main);
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
    }

    h1, h2, h3 {
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: var(--text-main) !important;
    }

    [data-testid="stMetric"] {
        background: var(--card-bg);
        padding: 1.5rem !important;
        border-radius: 16px !important;
        border: 1px solid var(--border) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        backdrop-filter: blur(12px) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
        border-color: var(--primary) !important;
    }

    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid var(--border) !important;
    }

    .stButton > button {
        background-color: var(--primary) !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.5rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }

    .stButton > button:hover {
        background-color: var(--primary-hover) !important;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.4) !important;
        transform: scale(1.02);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent !important;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: var(--card-bg) !important;
        border-radius: 8px 8px 0 0 !important;
        border: 1px solid var(--border) !important;
        color: var(--text-muted) !important;
        padding: 8px 20px !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--primary) !important;
        color: white !important;
        border-bottom: 2px solid white !important;
    }

    .stTextInput > div > div > input, .stSelectbox > div > div > div {
        background-color: #1e293b !important;
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
        color: var(--text-main) !important;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .element-container, .stMarkdown, .stPlotlyChart {
        animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    .premium-header {
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem !important;
        font-weight: 800 !important;
        margin-bottom: 0.5rem !important;
    }

    header, footer { visibility: hidden; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

SETTINGS = load_settings()
ROOT_DIR = SETTINGS.root_dir
CONFIG_DIR = SETTINGS.config_dir
DATA_DIR = SETTINGS.data_dir
SRC_DIR = ROOT_DIR / "src"
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


def main():
    st.markdown('<h1 class="premium-header">Ledger Smart Converter</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="color: var(--text-muted); font-size: 1.1rem; margin-top: -1rem;">{t("app_title")}</p>', unsafe_allow_html=True)

    lang_options = {"🇺🇸 English": "en", "🇲🇽 Español": "es"}
    selected_lang_label = st.sidebar.selectbox(
        t("language_select"), options=list(lang_options.keys()), index=0 if st.session_state.lang == "en" else 1, key="lang_selector"
    )

    new_lang = lang_options[selected_lang_label]
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        for key in (NAV_KEY, BANK_KEY, COPY_FEEDBACK_KEY):
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.sidebar.title(t("sidebar_welcome"))
    st.sidebar.markdown(t("sidebar_desc"))
    st.sidebar.header(t("config"))

    nav_options = [t("nav_import"), t("nav_analytics")]
    if NAV_KEY not in st.session_state or st.session_state[NAV_KEY] not in nav_options:
        st.session_state[NAV_KEY] = nav_options[0]
    page = st.sidebar.radio(t("navigate"), nav_options, key=NAV_KEY)

    st.sidebar.markdown("---")

    banks_cfg = get_banks_config()
    if banks_cfg:
        bank_map = {cfg.get("display_name", bid): bid for bid, cfg in banks_cfg.items()}
    else:
        bank_map = {t("bank_santander"): "santander_likeu", t("bank_hsbc"): "hsbc"}
    bank_options = list(bank_map.keys())
    if BANK_KEY not in st.session_state or st.session_state[BANK_KEY] not in bank_options:
        st.session_state[BANK_KEY] = bank_options[0]
    bank_label = st.sidebar.selectbox(t("select_bank"), options=bank_options, key=BANK_KEY)
    bank_id = bank_map[bank_label]
    bank_cfg = banks_cfg.get(bank_id, {})

    rules_path = CONFIG_DIR / "rules.yml"
    if rules_path.exists():
        st.sidebar.success(f"{t('loaded_rules')}: {rules_path.name}")
    else:
        st.sidebar.error(t("no_rules"))

    st.sidebar.markdown("---")
    st.sidebar.info(t("sidebar_info"))

    if page == t("nav_analytics"):
        render_analytics_dashboard(
            t=t,
            tc=tc,
            data_dir=DATA_DIR,
            config_dir=CONFIG_DIR,
            copy_feedback_key=COPY_FEEDBACK_KEY,
            ml_engine=ML_ENGINE,
        )
        return

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


if __name__ == "__main__":
    main()
