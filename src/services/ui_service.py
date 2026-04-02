# -*- coding: utf-8 -*-
"""UI Service for shared layout and data formatting.

This service provides UI-agnostic data formatting and transformation logic
to ensure consistency between different frontend frameworks (Streamlit, Flet).
"""
from typing import Any, Dict, List, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def format_currency(amount: float) -> str:
    """Format a number as currency."""
    return f"${amount:,.2f}"

def format_percentage(value: float) -> str:
    """Format a number as percentage."""
    return f"{value:.1f}%"

def get_coverage_pie_fig(stats: Dict[str, Any], t: Any) -> go.Figure:
    """Create a Plotly Figure for categorization coverage."""
    fig = px.pie(
        names=[t("metric_categorized"), t("uncategorized")],
        values=[stats["categorized"], stats["uncategorized"]],
        title=t("chart_coverage_title"),
        color_discrete_sequence=["#6366f1", "#475569"],
        hole=0.6,
        template="plotly_dark",
    )
    fig.update_layout(
        font_family="Outfit", 
        title_font_size=20, 
        margin=dict(t=80, b=40, l=40, r=40)
    )
    return fig

def get_type_bar_fig(stats: Dict[str, Any], t: Any) -> go.Figure:
    """Create a Plotly Figure for transaction types."""
    if not stats.get("type_counts"):
        return go.Figure()
        
    fig = px.bar(
        x=list(stats["type_counts"].keys()),
        y=list(stats["type_counts"].values()),
        title=t("chart_types_title"),
        labels={"x": t("chart_types_x"), "y": t("chart_types_y")},
        color=list(stats["type_counts"].keys()),
        color_discrete_sequence=["#6366f1", "#818cf8", "#94a3b8"],
        template="plotly_dark",
    )
    fig.update_layout(font_family="Outfit", title_font_size=20, showlegend=False)
    return fig

def get_spending_share_fig(stats: Dict[str, Any], t: Any, tc: Any) -> go.Figure:
    """Create a Plotly Figure for spending share by category."""
    if not stats.get("category_spending"):
        return go.Figure()
        
    fig = px.pie(
        names=[tc(n) for n in stats["category_spending"].keys()],
        values=list(stats["category_spending"].values()),
        hole=0.5,
        template="plotly_dark",
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(font_family="Outfit", showlegend=True, margin=dict(t=40, b=40, l=40, r=40))
    return fig

def get_category_count_fig(stats: Dict[str, Any], tc: Any) -> go.Figure:
    """Create a Plotly Figure for transaction counts by category."""
    if not stats.get("categories"):
        return go.Figure()
        
    categories_sorted = dict(sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True)[:10])
    fig = px.bar(
        x=list(categories_sorted.values()),
        y=[tc(n) for n in categories_sorted.keys()],
        orientation="h",
        labels={"x": "Transaction Count", "y": "Category"},
        color=list(categories_sorted.values()),
        color_continuous_scale="Blues",
    )
    fig.update_layout(showlegend=False, height=400)
    return fig

def get_category_spending_fig(stats: Dict[str, Any], tc: Any) -> go.Figure:
    """Create a Plotly Figure for spending amount by category."""
    if not stats.get("category_spending"):
        return go.Figure()
        
    spending_sorted = dict(sorted(stats["category_spending"].items(), key=lambda x: x[1], reverse=True)[:10])
    fig = px.bar(
        x=list(spending_sorted.values()),
        y=[tc(n) for n in spending_sorted.keys()],
        orientation="h",
        labels={"x": "Total Amount ($)", "y": "Category"},
        color=list(spending_sorted.values()),
        color_continuous_scale="Reds",
    )
    fig.update_layout(height=400)
    return fig

def get_monthly_trends_fig(stats: Dict[str, Any], t: Any, tc: Any) -> go.Figure:
    """Create a Plotly Figure for monthly spending trends."""
    if not stats.get("monthly_spending_trends"):
        return go.Figure()
        
    trends_data = []
    for month_year, categories in stats["monthly_spending_trends"].items():
        for category, amount in categories.items():
            trends_data.append({"Month": month_year, "Category": tc(category), "Amount": amount})
    
    trends_df = pd.DataFrame(trends_data)
    if trends_df.empty:
        return go.Figure()
        
    trends_df["Month"] = pd.to_datetime(trends_df["Month"])
    trends_df = trends_df.sort_values(by="Month")
    trends_df["Month"] = trends_df["Month"].dt.strftime("%Y-%m")

    fig = px.line(
        trends_df,
        x="Month",
        y="Amount",
        color="Category",
        title=t("monthly_spending_trends_chart_title"),
        labels={"Amount": "Total Spent ($)"},
        template="plotly_dark",
    )
    fig.update_layout(font_family="Outfit", title_font_size=20, hovermode="x unified")
    return fig

def get_bank_comparison_fig(stats_sant: Dict[str, Any], stats_hsbc: Dict[str, Any], tc: Any) -> go.Figure:
    """Create a grouped bar chart for bank comparison."""
    all_categories = set(stats_sant["category_spending"].keys()) | set(stats_hsbc["category_spending"].keys())

    comparison_data = []
    for cat in all_categories:
        comparison_data.append({
            "Category": tc(cat),
            "Santander": stats_sant["category_spending"].get(cat, 0),
            "HSBC": stats_hsbc["category_spending"].get(cat, 0),
        })

    if not comparison_data:
        return go.Figure()
        
    comp_df = pd.DataFrame(comparison_data)
    comp_df = comp_df.sort_values("Santander", ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Santander",
        x=comp_df["Category"],
        y=comp_df["Santander"],
        marker_color="#6366f1"
    ))
    fig.add_trace(go.Bar(
        name="HSBC",
        x=comp_df["Category"],
        y=comp_df["HSBC"],
        marker_color="#818cf8"
    ))

    fig.update_layout(
        barmode="group",
        template="plotly_dark",
        font_family="Outfit",
        title="Spending by Category (Both Banks)",
        xaxis_title="Category",
        yaxis_title="Amount (MXN)",
        height=500,
    )
    return fig
