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
    initial_sidebar_state="auto",  # Auto-collapse on mobile
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Ledger Smart Converter - Bank statement importer with ML categorization"
    }
)

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

    /* ===== BASE STYLES ===== */
    .main {
        background-color: var(--bg-dark);
        font-family: 'Outfit', sans-serif;
        color: var(--text-main);
        padding: 1rem;
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
    }

    h1, h2, h3 {
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: var(--text-main) !important;
    }

    /* ===== RESPONSIVE METRICS ===== */
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

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid var(--border) !important;
    }

    /* ===== BUTTONS (Touch-Friendly) ===== */
    .stButton > button {
        background-color: var(--primary) !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        min-height: 44px !important; /* Touch-friendly size */
        font-size: 1rem !important;
    }

    .stButton > button:hover {
        background-color: var(--primary-hover) !important;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.4) !important;
        transform: scale(1.02);
    }

    .stButton > button:active {
        transform: scale(0.98);
    }

    /* ===== TABS (Responsive) ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent !important;
        flex-wrap: wrap !important;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: var(--card-bg) !important;
        border-radius: 8px 8px 0 0 !important;
        border: 1px solid var(--border) !important;
        color: var(--text-muted) !important;
        padding: 12px 20px !important;
        min-height: 44px !important;
        white-space: nowrap !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--primary) !important;
        color: white !important;
        border-bottom: 2px solid white !important;
    }

    /* ===== INPUTS (Touch-Friendly) ===== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input {
        background-color: #1e293b !important;
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
        color: var(--text-main) !important;
        min-height: 44px !important;
        font-size: 16px !important; /* Prevents zoom on iOS */
    }

    /* ===== FILE UPLOADER (Mobile Friendly) ===== */
    [data-testid="stFileUploader"] {
        border: 2px dashed var(--border) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        background: var(--card-bg) !important;
        min-height: 120px !important;
    }

    [data-testid="stFileUploader"] button {
        min-height: 44px !important;
    }

    /* ===== EXPANDERS ===== */
    .streamlit-expanderHeader {
        background: var(--card-bg) !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        min-height: 44px !important;
    }

    /* ===== CHARTS (Responsive) ===== */
    .stPlotlyChart {
        width: 100% !important;
    }

    /* ===== ANIMATIONS ===== */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .element-container, .stMarkdown, .stPlotlyChart {
        animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    /* ===== HEADER ===== */
    .premium-header {
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: clamp(2rem, 5vw, 3rem) !important;
        font-weight: 800 !important;
        margin-bottom: 0.5rem !important;
        line-height: 1.2 !important;
    }

    /* ===== MOBILE STYLES (max-width: 768px) ===== */
    @media (max-width: 768px) {
        /* Main container */
        .main {
            padding: 0.5rem !important;
        }

        /* Header */
        .premium-header {
            font-size: 2rem !important;
            margin-bottom: 0.25rem !important;
        }

        /* Metrics - Stack vertically */
        [data-testid="stMetric"] {
            padding: 1rem !important;
            margin-bottom: 0.5rem !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.875rem !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
        }

        /* Buttons */
        .stButton > button {
            padding: 1rem !important;
            font-size: 1rem !important;
            min-height: 48px !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab"] {
            padding: 10px 16px !important;
            font-size: 0.875rem !important;
            flex: 1 1 auto !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            min-width: 280px !important;
            max-width: 100vw !important;
        }

        [data-testid="stSidebar"] [data-testid="stMarkdown"] {
            font-size: 0.875rem !important;
        }

        /* File uploader */
        [data-testid="stFileUploader"] {
            padding: 1rem !important;
            min-height: 100px !important;
        }

        /* Columns - Stack on mobile */
        .row-widget.stHorizontal {
            flex-direction: column !important;
        }

        [data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
        }

        /* Charts */
        .stPlotlyChart {
            height: 300px !important;
        }

        /* Expanders */
        .streamlit-expanderHeader {
            padding: 0.75rem !important;
            font-size: 0.875rem !important;
        }

        /* Inputs */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > div,
        .stNumberInput > div > div > input {
            font-size: 16px !important;
            padding: 0.75rem !important;
        }

        /* Hide some decorative elements on mobile */
        [data-testid="stMetric"]:hover {
            transform: none !important;
        }

        /* Reduce animation */
        .element-container, .stMarkdown, .stPlotlyChart {
            animation: none !important;
        }
    }

    /* ===== TABLET STYLES (769px - 1024px) ===== */
    @media (min-width: 769px) and (max-width: 1024px) {
        .main {
            padding: 1rem !important;
        }

        .premium-header {
            font-size: 2.5rem !important;
        }

        [data-testid="stMetric"] {
            padding: 1.25rem !important;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 10px 18px !important;
        }
    }

    /* ===== DESKTOP OPTIMIZATIONS (min-width: 1025px) ===== */
    @media (min-width: 1025px) {
        .main {
            max-width: 1400px !important;
            margin: 0 auto !important;
            padding: 2rem !important;
        }

        [data-testid="stSidebar"] {
            min-width: 320px !important;
        }
    }

    /* ===== ACCESSIBILITY ===== */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation: none !important;
            transition: none !important;
        }
    }

    /* ===== PRINT STYLES ===== */
    @media print {
        [data-testid="stSidebar"],
        .stButton,
        [data-testid="stFileUploader"] {
            display: none !important;
        }

        .main {
            background: white !important;
            color: black !important;
        }
    }

    /* ===== HIDE STREAMLIT DEFAULTS ===== */
    header, footer {
        visibility: hidden !important;
    }

    #MainMenu {
        visibility: hidden !important;
    }

    /* ===== TOUCH IMPROVEMENTS ===== */
    @media (hover: none) and (pointer: coarse) {
        /* Better touch targets */
        button, a, [role="button"] {
            min-height: 44px !important;
            min-width: 44px !important;
        }

        /* Remove hover effects on touch devices */
        [data-testid="stMetric"]:hover {
            transform: none !important;
        }

        .stButton > button:hover {
            transform: none !important;
        }
    }
</style>
"""

# Mobile viewport meta tag for proper scaling
VIEWPORT_META = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
"""

st.markdown(VIEWPORT_META, unsafe_allow_html=True)
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


def get_responsive_columns(mobile_cols=1, desktop_cols=2):
    """Helper to create responsive column layouts.

    Returns number of columns based on viewport (simplified approach).
    Streamlit doesn't have native viewport detection, so we use desktop_cols by default
    and rely on CSS to stack columns on mobile.
    """
    return desktop_cols


def render_mobile_tip():
    """Render a helpful tip for mobile users."""
    st.info("""
    📱 **Mobile Tip**: For the best experience:
    - Use landscape mode for charts
    - Tap the sidebar icon (←) to access navigation
    - Swipe to see more metrics
    - Use the 'wide' layout for better visibility
    """)


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
