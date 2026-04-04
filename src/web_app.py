from pathlib import Path
from typing import Any, Dict, List, Tuple, cast

import streamlit as st
import yaml

from settings import load_settings
from translations import TRANSLATIONS
from services.user_service import get_pref, set_pref, get_active_user, set_active_user

# --- 1. CONFIGURACIÓN DE PÁGINA (SIEMPRE PRIMERO) ---
st.set_page_config(
    page_title="Ledger Smart Converter",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="auto",
)

# --- 2. INICIALIZACIÓN DE ESTADO ---
if "lang" not in st.session_state:
    st.session_state.lang = get_pref("lang", "es")

if "active_user" not in st.session_state:
    st.session_state.active_user = get_active_user()


def t(key, **kwargs) -> str:
    """Helper to get translated string."""
    lang = st.session_state.lang
    raw_text: Any = TRANSLATIONS[lang].get(key, key)
    text = raw_text if isinstance(raw_text, str) else str(raw_text)
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
    return t(f"cat_{category.lower()}")


# --- 3. RECURSOS Y CONFIG ---
SETTINGS = load_settings()
ROOT_DIR = SETTINGS.root_dir
CONFIG_DIR = SETTINGS.config_dir
DATA_DIR = SETTINGS.data_dir
SRC_DIR = ROOT_DIR / "src"
TEMP_DIR = SETTINGS.temp_dir
TEMP_DIR.mkdir(exist_ok=True)


def load_css(file_path: Path):
    """Load custom CSS."""
    if file_path.exists():
        st.markdown(
            f"<style>{file_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


@st.cache_resource
def get_ml_engine():
    import ml_categorizer as ml

    engine = ml.TransactionCategorizer()
    if not engine.load_model():
        ml.train_global_model()
        engine.load_model()
    return engine


@st.cache_data
def get_banks_config():
    rules_path = CONFIG_DIR / "rules.yml"
    if rules_path.exists():
        with open(rules_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            return cfg.get("banks", {})
    return {}


@st.cache_data
def _build_analytics_csv_targets() -> Dict:
    accounts_path = CONFIG_DIR / "accounts.yml"
    default_targets = {
        "Santander LikeU": ("santander", "firefly_likeu.csv"),
        "HSBC Mexico": ("hsbc", "firefly_hsbc.csv"),
    }
    if not accounts_path.exists():
        return default_targets
    try:
        cfg = yaml.safe_load(accounts_path.read_text(encoding="utf-8")) or {}
        targets = {}
        for entry in cfg.get("canonical_accounts", {}).values():
            if not isinstance(entry, dict):
                continue
            csv_out = entry.get("csv_output") or {}
            directory = csv_out.get("directory") or csv_out.get("dir")
            filename = csv_out.get("filename") or csv_out.get("name")
            bank_ids = entry.get("bank_ids", [])
            display = next(iter(bank_ids), directory or "unknown")
            if directory and filename:
                targets[display] = (directory, filename)
        return targets if targets else default_targets
    except:
        return default_targets


ANALYTICS_CSV_TARGETS = _build_analytics_csv_targets()
BANK_KEY = "bank_select"
COPY_FEEDBACK_KEY = "copy_feedback"


def _get_bank_context() -> Tuple[str, str, Dict]:
    banks_cfg = get_banks_config()
    bank_map = {cfg.get("display_name", bid): bid for bid, cfg in banks_cfg.items()}
    if not bank_map:
        bank_map = {t("bank_santander"): "santander_likeu", t("bank_hsbc"): "hsbc"}
    bank_options = list(bank_map.keys())
    if (
        BANK_KEY not in st.session_state
        or st.session_state[BANK_KEY] not in bank_options
    ):
        st.session_state[BANK_KEY] = bank_options[0]
    bank_label = st.session_state[BANK_KEY]
    bank_id = bank_map[bank_label]
    bank_cfg = banks_cfg.get(bank_id, {})
    return bank_label, bank_id, bank_cfg


@st.cache_resource
def get_import_use_case():
    from infrastructure.adapters.sqlite_transaction_repository import SqliteTransactionRepository
    from infrastructure.adapters.sqlite_import_repository import SqliteImportRepository
    from infrastructure.adapters.yaml_rules_repository import YamlRulesRepository
    from infrastructure.adapters.legacy_data_extractor_adapter import LegacyDataExtractorAdapter
    from application.use_cases.import_statement import ImportStatement
    from services.db_service import DatabaseService
    
    db_service = DatabaseService(SETTINGS.data_dir / "ledger.db")
    
    # Ports & Adapters
    txn_repo = SqliteTransactionRepository(db_service)
    import_repo = SqliteImportRepository(db_service)
    config_reader = YamlRulesRepository(
        rules_path=CONFIG_DIR / "rules.yml",
        accounts_path=CONFIG_DIR / "accounts.yml"
    )
    data_extractor = LegacyDataExtractorAdapter(rules_path=CONFIG_DIR / "rules.yml")
    
    return ImportStatement(
        config_reader=config_reader,
        data_extractor=data_extractor,
        transaction_repository=txn_repo,
        import_repository=import_repo
    )


def page_import():
    from ui.pages.import_page import render_import_page

    bank_label, bank_id, bank_cfg = _get_bank_context()
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
        nav_key="native_navigation",
        bank_key=BANK_KEY,
        import_use_case=get_import_use_case()
    )


def page_analytics():
    from ui.pages.analytics_page import render_analytics_dashboard

    render_analytics_dashboard(
        t=t,
        tc=tc,
        config_dir=CONFIG_DIR,
        data_dir=DATA_DIR,
        copy_feedback_key=COPY_FEEDBACK_KEY,
        ml_engine=get_ml_engine(),
    )


def page_manual():
    from ui.pages.manual_entry_page import render_manual_entry_page

    render_manual_entry_page(
        t=t,
        config_dir=CONFIG_DIR,
        user_id=st.session_state.get("active_user"),
        lang=st.session_state.lang,
    )


def page_settings():
    from ui.pages.settings_page import render_settings_page

    render_settings_page(t=t, active_user=st.session_state.get("active_user"))


# --- 4. MAIN APP LOGIC ---
def main():
    load_css(SRC_DIR / "ui" / "style.css")

    st.sidebar.title(t("sidebar_welcome"))
    lang_options = {"🇲🇽 ES": "es", "🇺🇸 EN": "en"}
    lang_keys = list(lang_options.keys())
    curr_idx = 0 if st.session_state.lang == "es" else 1
    selected_lang = st.sidebar.selectbox(
        cast(str, t("language_select")),
        options=lang_keys,
        index=curr_idx,
    )
    if lang_options[selected_lang] != st.session_state.lang:
        st.session_state.lang = lang_options[selected_lang]
        set_pref("lang", st.session_state.lang)
        st.rerun()

    banks_cfg = get_banks_config()
    bank_map = {cfg.get("display_name", bid): bid for bid, cfg in banks_cfg.items()}
    if not bank_map:
        bank_map = {t("bank_santander"): "santander_likeu", t("bank_hsbc"): "hsbc"}
    bank_options = list(bank_map.keys())
    if (
        BANK_KEY not in st.session_state
        or st.session_state[BANK_KEY] not in bank_options
    ):
        st.session_state[BANK_KEY] = bank_options[0]
    st.sidebar.selectbox(
        cast(str, t("select_bank")), options=bank_options, key=BANK_KEY
    )

    active_user = st.session_state.get("active_user")
    if active_user:
        st.sidebar.success(f"👤 {t('active_user')}: **{active_user}**")
    else:
        st.sidebar.info(f"👤 {t('no_active_user')}")
    st.sidebar.markdown(t("sidebar_desc"))
    st.sidebar.info(t("sidebar_info"))

    st.markdown(
        '<h1 class="premium-header">Ledger Smart Converter</h1>', unsafe_allow_html=True
    )
    st.markdown(
        f'<p style="color: var(--text-muted); font-size: 1.1rem; margin-top: -1rem;">{t("app_title")}</p>',
        unsafe_allow_html=True,
    )

    navigation = st.navigation(
        [
            st.Page(page_import, title=t("nav_import"), icon="💳"),
            st.Page(page_analytics, title=t("nav_analytics"), icon="📊"),
            st.Page(page_manual, title=t("nav_manual_entry"), icon="✍️"),
            st.Page(page_settings, title=t("nav_settings"), icon="⚙️"),
        ]
    )
    navigation.run()


if __name__ == "__main__":
    main()
