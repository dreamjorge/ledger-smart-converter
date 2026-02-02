import streamlit as st
import re
import subprocess
import os
import sys
import shutil
from pathlib import Path
import pandas as pd
import yaml
import plotly.express as px
import plotly.graph_objects as go
import common_utils as cu
import ml_categorizer as ml
import smart_matching as sm
from translations import TRANSLATIONS

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

# Page Config
st.set_page_config(
    page_title=t("page_title"),
    page_icon="💳",
    layout="wide"
)

# Constants
ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
SRC_DIR = ROOT_DIR / "src"
TEMP_DIR = ROOT_DIR / "temp_web_uploads"

# Ensure temp dir exists
TEMP_DIR.mkdir(exist_ok=True)

# Initialize ML Categorizer
@st.cache_resource
def get_ml_engine():
    engine = ml.TransactionCategorizer()
    if engine.load_model():
        return engine
    # If no model, try training one
    ml.train_global_model()
    engine.load_model()
    return engine

ML_ENGINE = get_ml_engine()

# ----------------------------
# Helper Functions
# ----------------------------

def save_uploaded_file(uploaded_file, subdir="uploads"):
    if uploaded_file is None:
        return None
    dest_dir = TEMP_DIR / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / uploaded_file.name
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest_path

def run_script(script_name, args):
    """Runs a python script as a subprocess and captures output."""
    cmd = [sys.executable, str(SRC_DIR / script_name)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    return result

def load_csv_if_exists(path):
    if path and Path(path).exists():
        return pd.read_csv(path)
    return None

def load_yaml_if_exists(path):
    if path and Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None

def calculate_categorization_stats(df):
    """Calculate Firefly-focused categorization statistics."""
    if df is None or df.empty:
        return None
    
    total = len(df)
    
    # Check for uncategorized (destination contains "Uncategorized")
    if 'destination_name' in df.columns:
        uncategorized = df['destination_name'].str.contains('Uncategorized', case=False, na=False).sum()
        categorized = total - uncategorized
    else:
        categorized = 0
        uncategorized = total
    
    # Category coverage (category_name populated)
    if 'category_name' in df.columns:
        has_category = df['category_name'].notna() & (df['category_name'] != '')
        category_populated = has_category.sum()
    else:
        category_populated = 0
    
    # Total Spending (Sum of withdrawals)
    total_spent = 0.0
    if 'amount' in df.columns and 'type' in df.columns:
        total_spent = df[df['type'] == 'withdrawal']['amount'].astype(float).sum()
    
    # Transaction types
    type_counts = df['type'].value_counts().to_dict() if 'type' in df.columns else {}
    
    # Extract main category from destination and sum amounts
    categories = {}
    category_spending = {}
    if 'destination_name' in df.columns and 'amount' in df.columns:
        for _, row in df.iterrows():
            dest = row['destination_name']
            amt = float(row['amount']) if pd.notna(row['amount']) else 0.0
            
            if pd.notna(dest) and ':' in str(dest):
                parts = str(dest).split(':')
                if len(parts) > 1 and parts[0] == 'Expenses':
                    cat = parts[1]
                    categories[cat] = categories.get(cat, 0) + 1
                    if row.get('type') == 'withdrawal':
                        category_spending[cat] = category_spending.get(cat, 0.0) + amt
    
    return {
        'total': total,
        'categorized': categorized,
        'uncategorized': uncategorized,
        'coverage_pct': (categorized / total * 100) if total > 0 else 0,
        'category_populated': category_populated,
        'category_pct': (category_populated / total * 100) if total > 0 else 0,
        'total_spent': total_spent,
        'type_counts': type_counts,
        'categories': categories,
        'category_spending': category_spending
    }

def render_analytics_dashboard():
    st.header(t("analytics_title"))
    
    # Load existing CSVs
    santander_csv = DATA_DIR / "santander" / "firefly_likeu.csv"
    hsbc_csv = DATA_DIR / "hsbc" / "firefly_hsbc.csv"
    
    df_sant = load_csv_if_exists(santander_csv)
    df_hsbc = load_csv_if_exists(hsbc_csv)
    
    if df_sant is None and df_hsbc is None:
        st.warning(t("no_csv_found"))
        return
    
    # Tab selection for comparison
    tabs = []
    if df_sant is not None:
        tabs.append("Santander")
    if df_hsbc is not None:
        tabs.append("HSBC")
    if df_sant is not None and df_hsbc is not None:
        tabs.append(t("tab_comparison"))
    
    selected_tabs = st.tabs(tabs)
    
    tab_idx = 0
    
    # Santander Tab
    if df_sant is not None:
        with selected_tabs[tab_idx]:
            st.subheader(t("bank_analytics_header", bank="Santander"))
            stats = calculate_categorization_stats(df_sant)
            render_bank_analytics(df_sant, stats, "Santander")
        tab_idx += 1
    
    # HSBC Tab
    if df_hsbc is not None:
        with selected_tabs[tab_idx]:
            st.subheader(t("bank_analytics_header", bank="HSBC"))
            stats = calculate_categorization_stats(df_hsbc)
            render_bank_analytics(df_hsbc, stats, "HSBC")
        tab_idx += 1
    
    # Comparison Tab
    if df_sant is not None and df_hsbc is not None:
        with selected_tabs[tab_idx]:
            st.subheader(t("bank_comparison"))
            render_comparison(df_sant, df_hsbc)

def render_bank_analytics(df, stats, bank_name):
    """Render analytics for a single bank."""
    if df is None or df.empty:
        st.error("No data available")
        return
    
    # Extract periods from tags
    periods = set()
    if 'tags' in df.columns:
        for tag_str in df['tags'].dropna():
            for tag in str(tag_str).split(','):
                if tag.startswith('period:'):
                    periods.add(tag.split(':')[1])
    
    sorted_periods = sorted(list(periods), reverse=True)
    selected_period = t("all")
    
    if sorted_periods:
        selected_period = st.selectbox(t("filter_period", bank=bank_name), [t("all")] + sorted_periods, key=f"{bank_name}_period_filter")
    
    # Filter data if needed
    if selected_period != t("all"):
        df_filtered = df[df['tags'].str.contains(f"period:{selected_period}", na=False)]
        stats = calculate_categorization_stats(df_filtered)
    else:
        df_filtered = df
        # stats is already passed from caller for "All"

    if stats is None:
        st.error(t("no_data_selection"))
        return
    
    # Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(t("metric_total_txns"), stats['total'], help=t("help_total_txns"))
    with col2:
        st.metric(t("metric_total_spent"), f"${stats['total_spent']:,.2f}", help=t("help_total_spent"))
    with col3:
        st.metric(t("metric_categorized"), f"{stats['categorized']} ({stats['coverage_pct']:.1f}%)", help=t("help_coverage"))
    with col4:
        st.metric(t("metric_category_field"), f"{stats['category_populated']} ({stats['category_pct']:.1f}%)")
    with col5:
        withdrawals = stats['type_counts'].get('withdrawal', 0)
        st.metric(t("metric_withdrawals"), withdrawals)
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        # Categorization Coverage Pie
        fig = px.pie(
            names=[t("metric_categorized"), t("uncategorized")],
            values=[stats['categorized'], stats['uncategorized']],
            title=t("chart_coverage_title"),
            color_discrete_sequence=['#00CC96', '#EF553B']
        )
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        # Transaction Types
        if stats['type_counts']:
            fig = px.bar(
                x=list(stats['type_counts'].keys()),
                y=list(stats['type_counts'].values()),
                title=t("chart_types_title"),
                labels={'x': t("chart_types_x"), 'y': t("chart_types_y")},
                color=list(stats['type_counts'].keys()),
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig, width='stretch')
    
    # Category Breakdown
    if stats['categories'] or stats['category_spending']:
        st.subheader(t("category_deep_dive"))
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Category Count Breakdown
            st.markdown(t("txns_by_category"))
            categories_sorted = dict(sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True)[:10])
            
            fig_count = px.bar(
                x=list(categories_sorted.values()),
                y=list(categories_sorted.keys()),
                orientation='h',
                labels={'x': 'Transaction Count', 'y': 'Category'},
                color=list(categories_sorted.values()),
                color_continuous_scale='Blues'
            )
            fig_count.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig_count, width='stretch')
            
        with col2:
            # Category Spending Breakdown
            st.markdown(t("money_by_category"))
            spending_sorted = dict(sorted(stats['category_spending'].items(), key=lambda x: x[1], reverse=True)[:10])
            
            fig_spent = px.bar(
                x=list(spending_sorted.values()),
                y=list(spending_sorted.keys()),
                orientation='h',
                labels={'x': 'Total Amount ($)', 'y': 'Category'},
                color=list(spending_sorted.values()),
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_spent, width='stretch')
            
        # Summary Table (Prominent)
        st.markdown(t("category_summary"))
        cat_data = []
        for cat in sorted(stats['categories'].keys()):
            cat_data.append({
                "Category": cat,
                "Transactions": stats['categories'].get(cat, 0),
                "Total Spent": f"${stats['category_spending'].get(cat, 0.0):,.2f}"
            })
        st.dataframe(pd.DataFrame(cat_data), width='stretch')
            
        # Drill-down: Detailed Transactions by Category
        st.markdown("---")
        st.subheader(t("drilldown_title"))
        selected_cat = st.selectbox(t("drilldown_select"), [t("all")] + sorted(list(stats['categories'].keys())), key=f"{bank_name}_drilldown_cat")
        
        display_df = df_filtered.copy()
        if selected_cat != t("all"):
            # Filter by matching the category part of destination_name
            display_df = display_df[display_df['destination_name'].str.contains(f":{selected_cat}", na=False)]
        
        # Format for display
        if not display_df.empty:
            st.markdown(t("showing_txns", count=len(display_df), cat=selected_cat))
            # Select relevant columns
            view_cols = ['date', 'description', 'amount', 'destination_name', 'tags']
            st.dataframe(display_df[view_cols], width='stretch')
        else:
            st.info(t("no_txns_found"))
            
    # --- Rule Correction Hub ---
    st.markdown("---")
    with st.expander(t("rule_hub_title"), expanded=False):
        st.subheader(t("rule_hub_subtitle"))
        st.markdown(t("rule_hub_desc"))
        st.info(t("rule_hub_tip"))
        
        # Get unique merchants from the current filtered dataframe
        if 'tags' in df_filtered.columns:
            merchants = set()
            for tags in df_filtered['tags'].dropna():
                for tag in str(tags).split(','):
                    if tag.startswith('merchant:'):
                        merchants.add(tag.split(':')[1])
            
            merchant_list = sorted(list(merchants))
            
            # --- Smart Search & Suggestions ---
            st.markdown(t("smart_lookup"))
            c_search, c_suggest = st.columns([2, 3])
            
            with c_search:
                search_term = st.text_input(t("fuzzy_search"), "", key=f"{bank_name}_fuzzy_search")
                if search_term:
                    matches = sm.find_similar_merchants(search_term, merchant_list, threshold=50)
                    if matches:
                        merchant_list = [m for m, score in matches]
                    else:
                        st.warning(t("no_similar_merchants"))

            selected_merchant = st.selectbox(t("select_merchant"), merchant_list, key=f"{bank_name}_fix_merchant")
            
            # Get ML Prediction
            ml_predictions = ML_ENGINE.predict(selected_merchant)
            suggested_cat_hub = None
            if ml_predictions:
                top_cat, confidence = ml_predictions[0]
                if confidence > 0.3:
                    st.success(t("ml_prediction", cat=top_cat, conf=confidence))
                    if ":" in top_cat:
                        suggested_cat_hub = top_cat.split(":")[-1]

            col1, col2 = st.columns(2)
            with col1:
                # Common category suggestions (Internal IDs)
                common_cats_internal = ["Groceries", "Restaurants", "Shopping", "Transport", "Subscriptions", "Entertainment", "Health", "Fees", "Online"]
                
                # Manual map to translations
                cat_translations = {c: t(f"cat_{c.lower()}") for c in common_cats_internal}
                
                # If ML suggested a category that's not in common_cats, add it temporarily
                if suggested_cat_hub and suggested_cat_hub not in common_cats_internal:
                    common_cats_internal.insert(0, suggested_cat_hub)
                    # Add translation if missing (fallback to itself)
                    if suggested_cat_hub not in cat_translations:
                        cat_translations[suggested_cat_hub] = suggested_cat_hub
                
                # Pre-select the ML suggested category if available
                default_ix = common_cats_internal.index(suggested_cat_hub) if suggested_cat_hub in common_cats_internal else 0
                
                # Display localized but value is internal
                selected_cat_display = st.selectbox(
                    t("select_category"), 
                    options=[cat_translations[c] for c in common_cats_internal],
                    index=default_ix, 
                    key=f"{bank_name}_fix_category"
                )
                # Map back to internal ID
                category = [k for k, v in cat_translations.items() if v == selected_cat_display][0]
            
            # Auto-suggest expense based on category
            # If ML has a full path like Expenses:Food:Groceries, use it directly if it matches the selected leaf category
            if ml_predictions and ml_predictions[0][0].endswith(f":{category}"):
                suggested_expense = ml_predictions[0][0]
            else:
                suggested_expense = f"Expenses:Food:{category}" if category in ["Groceries", "Restaurants"] else \
                                    f"Expenses:Transport:{category}" if category in ["Transport"] else \
                                    f"Expenses:Entertainment:{category}" if category in ["Entertainment", "Subscriptions"] else \
                                    f"Expenses:Shopping:{category}" if category in ["Shopping", "Online"] else \
                                    f"Expenses:Fees:{category}" if category in ["Fees"] else \
                                    f"Expenses:{category}"
            
            expense_account = st.text_input(t("confirm_destination"), suggested_expense, key=f"{bank_name}_fix_expense")
            
            # Simple regex suggestion
            safe_pattern = re.escape(selected_merchant.replace("_", " "))
            regex_pattern = st.text_input(t("regex_pattern"), safe_pattern, key=f"{bank_name}_fix_regex")
            
            if st.button(t("save_rule"), type="primary", key=f"{bank_name}_save_rule"):
                # Path to rules.yml
                rules_path = CONFIG_DIR / "rules.yml"
                
                # Use cu helper to update YAML
                cu.add_rule_to_yaml(rules_path, selected_merchant, regex_pattern, expense_account, category.lower())
                
                # Feedback loop: Retrain ML model with new data
                with st.spinner(t("teaching_ai")):
                    ml.train_global_model()
                    st.cache_resource.clear() # Force reload of the model
                
                st.success(t("rule_saved", merchant=selected_merchant))
                st.info(t("regenerating"))
                
                # Re-run the appropriate import script
                script = "import_likeu_firefly.py" if bank_name == "Santander" else "import_hsbc_cfdi_firefly.py"
                
                # We need to know which file was used. 
                # This is tricky because the files are in DATA_DIR.
                # For now, we'll try to find the "latest" processed file or assume standard names.
                st.warning(t("reprocess_warning"))
                st.balloons()

def render_comparison(df_sant, df_hsbc):
    """Render comparison between Santander and HSBC."""
    stats_sant = calculate_categorization_stats(df_sant)
    stats_hsbc = calculate_categorization_stats(df_hsbc)
    
    # Comparison Metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### Santander")
        st.metric(t("metric_total_txns"), stats_sant['total'], help=t("help_total_txns"))
        st.metric(t("metric_total_spent"), f"${stats_sant['total_spent']:,.2f}", help=t("help_total_spent"))
        st.metric(t("metric_categorized"), f"{stats_sant['coverage_pct']:.1f}%", help=t("help_coverage"))
    
    with col2:
        st.markdown(f"### HSBC")
        st.metric(t("metric_total_txns"), stats_hsbc['total'], help=t("help_total_txns"))
        st.metric(t("metric_total_spent"), f"${stats_hsbc['total_spent']:,.2f}", help=t("help_total_spent"))
        st.metric(t("metric_categorized"), f"{stats_hsbc['coverage_pct']:.1f}%", help=t("help_coverage"))
    
    # Side-by-side coverage chart
    fig = go.Figure(data=[
        go.Bar(name=t("metric_categorized"), x=['Santander', 'HSBC'], 
               y=[stats_sant['categorized'], stats_hsbc['categorized']], marker_color='#00CC96'),
        go.Bar(name=t("uncategorized"), x=['Santander', 'HSBC'], 
               y=[stats_sant['uncategorized'], stats_hsbc['uncategorized']], marker_color='#EF553B')
    ])
    fig.update_layout(barmode='stack', title=t("chart_coverage_title"))
    st.plotly_chart(fig, width='stretch')

def main():
    st.title(t("app_title"))
    
    # Sidebar: Language Selection
    lang_options = {"🇺🇸 English": "en", "🇲🇽 Español": "es"}
    
    selected_lang_label = st.sidebar.selectbox(
        t("language_select"), 
        options=list(lang_options.keys()),
        index=0 if st.session_state.lang == "en" else 1,
        key="lang_selector"
    )
    
    # Update lang if changed
    new_lang = lang_options[selected_lang_label]
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.rerun()

    # Sidebar: Config
    st.sidebar.title(t("sidebar_welcome"))
    st.sidebar.markdown(t("sidebar_desc"))
    st.sidebar.header(t("config"))
    
    # Page Navigation
    page = st.sidebar.radio(t("navigate"), [t("nav_import"), t("nav_analytics")])
    
    st.sidebar.markdown("---")
    
    # Bank Selection
    bank_map = {
        t("bank_santander"): "Santander LikeU",
        t("bank_hsbc"): "HSBC Mexico"
    }
    bank_label = st.sidebar.selectbox(t("select_bank"), options=list(bank_map.keys()))
    bank = bank_map[bank_label]
    
    # Rules File
    rules_path = CONFIG_DIR / "rules.yml"
    if rules_path.exists():
        st.sidebar.success(f"{t('loaded_rules')}: {rules_path.name}")
    else:
        st.sidebar.error(t("no_rules"))

    # Mode
    st.sidebar.markdown("---")
    st.sidebar.info(t("sidebar_info"))
    
    # Route to pages
    if page == t("nav_analytics"):
        render_analytics_dashboard()
        return

    # ----------------------------
    # Main Content
    # ----------------------------
    
    with st.expander(t("quick_start"), expanded=bank == "Santander LikeU"):
        st.write(t("welcome_bank", bank=bank))
        st.write(t("steps_desc"))
        
        file_type_label = "Excel" if bank == "Santander LikeU" else "XML"
        st.markdown(t("step_1", file_type=file_type_label))
        st.markdown(t("step_2"))
        st.markdown(t("step_3"))
        st.markdown(t("step_4"))
        
        if bank == "Santander LikeU":
            st.info(t("tip_santander"))
        else:
            st.info(t("tip_hsbc"))

    st.header(t("import_header", bank=bank))
    
    uploaded_main = None
    uploaded_pdf = None
    
    col1, col2 = st.columns(2)
    
    with col1:
        if bank == "Santander LikeU":
            uploaded_main = st.file_uploader(t("select_xlsx"), type=["xlsx"], help=t("help_xlsx"))
        else: # HSBC
            uploaded_main = st.file_uploader(t("select_xml"), type=["xml", "csv", "xlsx"], help=t("help_xml"))
            
    with col2:
        uploaded_pdf = st.file_uploader(t("select_pdf"), type=["pdf"], help=t("help_pdf"))
    
    force_pdf_ocr = False
    if uploaded_pdf:
        force_pdf_ocr = st.checkbox(t("use_ocr"), value=False, help=t("help_ocr"))

    if uploaded_main or (force_pdf_ocr and uploaded_pdf):
        if st.button(t("process_files"), type="primary"):
            with st.spinner(t("processing")):
                # 1. Save files
                main_path = save_uploaded_file(uploaded_main, "input")
                pdf_path = save_uploaded_file(uploaded_pdf, "input")
                
                # Output paths
                output_base = TEMP_DIR / "output"
                output_base.mkdir(parents=True, exist_ok=True)
                
                out_csv = output_base / "firefly_import.csv"
                out_unknown = output_base / "unknown_merchants.csv"
                out_suggestions = output_base / "rules_suggestions.yml"
                
                # 2. Construct Script Arguments
                args = []
                script = ""
                
                if bank == "Santander LikeU":
                    script = "import_likeu_firefly.py"
                    args.extend(["--xlsx", str(main_path)])
                else:
                    script = "import_hsbc_cfdi_firefly.py"
                    args.extend(["--xml", str(main_path)])
                
                args.extend(["--rules", str(rules_path)])
                args.extend(["--out", str(out_csv)])
                args.extend(["--unknown-out", str(out_unknown)])
                args.extend(["--suggestions-out", str(out_suggestions)])
                
                if pdf_path:
                    args.extend(["--pdf", str(pdf_path)])
                    if force_pdf_ocr:
                        args.append("--pdf-source")
                
                # 3. Run
                res = run_script(script, args)
                
                # 4. Display Results
                if res.returncode == 0:
                    st.success(t("process_complete"))
                    
                    st.info(f"""
                    {t('next_steps_title')}
                    {t('next_step_1')}
                    {t('next_step_2')}
                    {t('next_step_3')}
                    {t('next_step_4')}
                    """)
                    
                    # Show logs
                    with st.expander(t("view_logs"), expanded=pdf_path is not None):
                        st.code(res.stdout, language="text")
                    
                    # Tabs for outputs
                    tab1, tab2, tab3 = st.tabs([t("tab_csv"), t("tab_unknown"), t("tab_suggestions")])
                    
                    with tab1:
                        df_csv = load_csv_if_exists(out_csv)
                        if df_csv is not None:
                            st.dataframe(df_csv, width='stretch')
                            with open(out_csv, "rb") as f:
                                st.download_button(t("download_csv"), f, "firefly_import.csv", "text/csv")
                        else:
                            st.warning(t("no_csv"))

                    with tab2:
                        df_unk = load_csv_if_exists(out_unknown)
                        if df_unk is not None:
                            st.dataframe(df_unk, width='stretch')
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
    st.caption(f"{t('working_dir')}: {ROOT_DIR}")

if __name__ == "__main__":
    main()
