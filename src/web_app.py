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

# Page Config
st.set_page_config(
    page_title="Bank Importer",
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
    """Render the analytics dashboard page."""
    st.header("📊 Analytics Dashboard")
    
    # Load existing CSVs
    santander_csv = DATA_DIR / "santander" / "firefly_likeu.csv"
    hsbc_csv = DATA_DIR / "hsbc" / "firefly_hsbc.csv"
    
    df_sant = load_csv_if_exists(santander_csv)
    df_hsbc = load_csv_if_exists(hsbc_csv)
    
    if df_sant is None and df_hsbc is None:
        st.warning("No CSV files found. Please process files first using the Import tab.")
        return
    
    # Tab selection for comparison
    tabs = []
    if df_sant is not None:
        tabs.append("Santander")
    if df_hsbc is not None:
        tabs.append("HSBC")
    if df_sant is not None and df_hsbc is not None:
        tabs.append("Comparison")
    
    selected_tabs = st.tabs(tabs)
    
    tab_idx = 0
    
    # Santander Tab
    if df_sant is not None:
        with selected_tabs[tab_idx]:
            st.subheader("Santander LikeU")
            stats = calculate_categorization_stats(df_sant)
            render_bank_analytics(df_sant, stats, "Santander")
        tab_idx += 1
    
    # HSBC Tab
    if df_hsbc is not None:
        with selected_tabs[tab_idx]:
            st.subheader("HSBC Mexico")
            stats = calculate_categorization_stats(df_hsbc)
            render_bank_analytics(df_hsbc, stats, "HSBC")
        tab_idx += 1
    
    # Comparison Tab
    if df_sant is not None and df_hsbc is not None:
        with selected_tabs[tab_idx]:
            st.subheader("Bank Comparison")
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
    selected_period = "All"
    
    if sorted_periods:
        selected_period = st.selectbox(f"Filter by Statement Period ({bank_name})", ["All"] + sorted_periods, key=f"{bank_name}_period_filter")
    
    # Filter data if needed
    if selected_period != "All":
        df_filtered = df[df['tags'].str.contains(f"period:{selected_period}", na=False)]
        stats = calculate_categorization_stats(df_filtered)
    else:
        df_filtered = df
        # stats is already passed from caller for "All"

    if stats is None:
        st.error("No data available for this selection")
        return
    
    # Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Transactions", stats['total'])
    with col2:
        st.metric("Total Spent", f"${stats['total_spent']:,.2f}")
    with col3:
        st.metric("Categorized", f"{stats['categorized']} ({stats['coverage_pct']:.1f}%)")
    with col4:
        st.metric("Category Field", f"{stats['category_populated']} ({stats['category_pct']:.1f}%)")
    with col5:
        withdrawals = stats['type_counts'].get('withdrawal', 0)
        st.metric("Withdrawals", withdrawals)
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        # Categorization Coverage Pie
        fig = px.pie(
            names=['Categorized', 'Uncategorized'],
            values=[stats['categorized'], stats['uncategorized']],
            title='Categorization Coverage',
            color_discrete_sequence=['#00CC96', '#EF553B']
        )
        st.plotly_chart(fig, width='stretch')
    
    with col2:
        # Transaction Types
        if stats['type_counts']:
            fig = px.bar(
                x=list(stats['type_counts'].keys()),
                y=list(stats['type_counts'].values()),
                title='Transaction Types',
                labels={'x': 'Type', 'y': 'Count'},
                color=list(stats['type_counts'].keys()),
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig, width='stretch')
    
    # Category Breakdown
    if stats['categories'] or stats['category_spending']:
        st.subheader("Category Deep Dive")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Category Count Breakdown
            st.markdown("##### Transactions by Category")
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
            st.markdown("##### Money Spent by Category")
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
        st.markdown("##### Category Summary")
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
        st.subheader("🔍 Transaction Drill-down")
        selected_cat = st.selectbox("Select a Category to view details", ["All"] + sorted(list(stats['categories'].keys())), key=f"{bank_name}_drilldown_cat")
        
        display_df = df_filtered.copy()
        if selected_cat != "All":
            # Filter by matching the category part of destination_name
            display_df = display_df[display_df['destination_name'].str.contains(f":{selected_cat}", na=False)]
        
        # Format for display
        if not display_df.empty:
            st.markdown(f"**Showing {len(display_df)} transactions for: `{selected_cat}`**")
            # Select relevant columns
            view_cols = ['date', 'description', 'amount', 'destination_name', 'tags']
            st.dataframe(display_df[view_cols], width='stretch')
        else:
            st.info("No transactions found for this category.")
            
    # --- Rule Correction Hub ---
    st.markdown("---")
    with st.expander("🛠️ Rule Correction Hub", expanded=False):
        st.subheader("Progressive Rule Learning")
        st.markdown("""
        Use this tool to **permanently fix** miscategorized transactions found in the analytics above.
        
        **Workflow:**
        1. **Identify**: Find a transaction in the *Drill-down* table that has the wrong Category or Destination.
        2. **Configure**: Select that merchant below and provide the correct details.
        3. **Save**: Click 'Save Rule'. This updates your global `config/rules.yml` file immediately.
        4. **Refresh**: Go back to the **Import Files** tab and re-process your statement to apply the new rules.
        """)
        st.info("💡 **Note**: New rules are added to the top of the file to ensure they take priority over more general rules.")
        
        # Get unique merchants from the current filtered dataframe
        if 'tags' in df_filtered.columns:
            merchants = set()
            for tags in df_filtered['tags'].dropna():
                for tag in str(tags).split(','):
                    if tag.startswith('merchant:'):
                        merchants.add(tag.split(':')[1])
            
            merchant_list = sorted(list(merchants))
            
            col1, col2 = st.columns(2)
            with col1:
                selected_merchant = st.selectbox("1. Select Merchant to fix", merchant_list, key=f"{bank_name}_fix_merchant")
            
            with col2:
                # Common category suggestions
                common_cats = ["Groceries", "Restaurants", "Shopping", "Transport", "Subscriptions", "Entertainment", "Health", "Fees", "Online"]
                category = st.selectbox("2. Select Correct Category", common_cats, key=f"{bank_name}_fix_category")
            
            # Auto-suggest expense based on category
            suggested_expense = f"Expenses:Food:{category}" if category in ["Groceries", "Restaurants"] else \
                                f"Expenses:Transport:{category}" if category in ["Transport"] else \
                                f"Expenses:Entertainment:{category}" if category in ["Entertainment", "Subscriptions"] else \
                                f"Expenses:Shopping:{category}" if category in ["Shopping", "Online"] else \
                                f"Expenses:Fees:{category}" if category in ["Fees"] else \
                                f"Expenses:{category}"
            
            expense_account = st.text_input("3. Confirm Destination Account", suggested_expense, key=f"{bank_name}_fix_expense")
            
            # Simple regex suggestion
            safe_pattern = re.escape(selected_merchant.replace("_", " "))
            regex_pattern = st.text_input("4. Regex Pattern (broad to catch variants)", safe_pattern, key=f"{bank_name}_fix_regex")
            
            if st.button("💾 Save Rule & Regenerate Data", type="primary", key=f"{bank_name}_save_rule"):
                # Path to rules.yml
                rules_path = CONFIG_DIR / "rules.yml"
                
                # Use cu helper to update YAML
                cu.add_rule_to_yaml(rules_path, selected_merchant, regex_pattern, expense_account, category.lower())
                
                st.success(f"Rule for `{selected_merchant}` saved to `rules.yml`!")
                st.info("Regenerating data... please wait.")
                
                # Re-run the appropriate import script
                script = "import_likeu_firefly.py" if bank_name == "Santander" else "import_hsbc_cfdi_firefly.py"
                
                # We need to know which file was used. 
                # This is tricky because the files are in DATA_DIR.
                # For now, we'll try to find the "latest" processed file or assume standard names.
                st.warning("Please go back to the 'Import Files' tab and re-process your latest statement to see the changes reflected.")
                st.balloons()

def render_comparison(df_sant, df_hsbc):
    """Render comparison between Santander and HSBC."""
    stats_sant = calculate_categorization_stats(df_sant)
    stats_hsbc = calculate_categorization_stats(df_hsbc)
    
    # Comparison Metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Santander")
        st.metric("Transactions", stats_sant['total'])
        st.metric("Total Spent", f"${stats_sant['total_spent']:,.2f}")
        st.metric("Coverage", f"{stats_sant['coverage_pct']:.1f}%")
    
    with col2:
        st.markdown("### HSBC")
        st.metric("Transactions", stats_hsbc['total'])
        st.metric("Total Spent", f"${stats_hsbc['total_spent']:,.2f}")
        st.metric("Coverage", f"{stats_hsbc['coverage_pct']:.1f}%")
    
    # Side-by-side coverage chart
    fig = go.Figure(data=[
        go.Bar(name='Categorized', x=['Santander', 'HSBC'], 
               y=[stats_sant['categorized'], stats_hsbc['categorized']], marker_color='#00CC96'),
        go.Bar(name='Uncategorized', x=['Santander', 'HSBC'], 
               y=[stats_sant['uncategorized'], stats_hsbc['uncategorized']], marker_color='#EF553B')
    ])
    fig.update_layout(barmode='stack', title='Categorization Comparison')
    st.plotly_chart(fig, width='stretch')

def main():
    st.title("💳 Credit Card Importer")
    
    # Sidebar: Config
    st.sidebar.header("Configuration")
    
    # Page Navigation
    page = st.sidebar.radio("Navigate", ["Import Files", "Analytics Dashboard"])
    
    st.sidebar.markdown("---")
    
    # Bank Selection
    bank = st.sidebar.selectbox("Select Bank", ["Santander LikeU", "HSBC Mexico"])
    
    # Rules File
    rules_path = CONFIG_DIR / "rules.yml"
    if rules_path.exists():
        st.sidebar.success(f"Loaded rules: {rules_path.name}")
    else:
        st.sidebar.error("Rules file not found in config/rules.yml")

    # Mode
    st.sidebar.markdown("---")
    st.sidebar.info("This tool runs the import scripts and lets you download the results.")
    
    # Route to pages
    if page == "Analytics Dashboard":
        render_analytics_dashboard()
        return

    # ----------------------------
    # Main Content
    # ----------------------------
    
    st.header(f"Import: {bank}")
    
    uploaded_main = None
    uploaded_pdf = None
    
    col1, col2 = st.columns(2)
    
    with col1:
        if bank == "Santander LikeU":
            uploaded_main = st.file_uploader("Upload Excel Statement (XLSX)", type=["xlsx"])
        else: # HSBC
            uploaded_main = st.file_uploader("Upload XML Statement (XML)", type=["xml"])
            
    with col2:
        uploaded_pdf = st.file_uploader("Upload PDF Statement (Optional - for validation)", type=["pdf"])
    
    force_pdf_ocr = False
    if uploaded_pdf:
        force_pdf_ocr = st.checkbox("🔍 Use PDF as primary data source (OCR)", value=False, help="Enable this if you want to extract transactions directly from the PDF using Tesseract OCR.")

    if uploaded_main or (force_pdf_ocr and uploaded_pdf):
        if st.button("🚀 Process Files", type="primary"):
            with st.spinner("Processing..."):
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
                    st.success("Processing Complete!")
                    
                    # Show logs
                    with st.expander("View Logs / PDF Extraction", expanded=pdf_path is not None):
                        st.code(res.stdout, language="text")
                    
                    # Tabs for outputs
                    tab1, tab2, tab3 = st.tabs(["Firefly CSV", "Unknown Merchants", "Suggestions"])
                    
                    with tab1:
                        df_csv = load_csv_if_exists(out_csv)
                        if df_csv is not None:
                            st.dataframe(df_csv, width='stretch')
                            with open(out_csv, "rb") as f:
                                st.download_button("Download CSV", f, "firefly_import.csv", "text/csv")
                        else:
                            st.warning("No CSV generated (file empty?)")

                    with tab2:
                        df_unk = load_csv_if_exists(out_unknown)
                        if df_unk is not None:
                            st.dataframe(df_unk, width='stretch')
                        else:
                            st.info("No unknown merchants found.")
                            
                    with tab3:
                        if out_suggestions.exists():
                            with open(out_suggestions, "r", encoding="utf-8") as f:
                                sugg_content = f.read()
                            st.code(sugg_content, language="yaml")
                            st.download_button("Download Suggestions YAML", sugg_content, "suggestions.yml", "text/yaml")
                        else:
                            st.info("No suggestions generated.")
                            
                else:
                    st.error("Error Processing File")
                    st.error(res.stderr)
                    st.code(res.stdout, language="text")

    st.markdown("---")
    st.caption(f"Working Directory: {ROOT_DIR}")

if __name__ == "__main__":
    main()
