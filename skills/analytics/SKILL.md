---
name: analytics-dashboard
description: Use this skill for developing Streamlit dashboard features, updating analytics services, and optimizing data aggregation queries.
---

# Analytics Skill

## Mandates for Token Efficiency

1. **Context First**: Always read `docs/context/ui.qmd` and `docs/context/services.qmd` before modifying dashboards.
2. **Precision Navigation**: Use `codegraph_search "analytics"` and `codegraph_node "AnalyticsService"` to locate logic.

## Workflow: UI/Analytics Updates

1. **Services Layer**: If data aggregation logic changes, update `src/services/analytics_service.py`.
2. **Data Access**: If fetching logic changes (CSV loading), update `src/services/data_service.py`.
3. **UI Page**: Update `src/ui/pages/analytics_page.py` or components in `src/ui/components/`.
4. **Translations**: Use `t()` from `src.translations` for all UI text.

## Related Agents
- **Analytics Agent**: Specialist in data visualization and business metrics.
