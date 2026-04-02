import flet as ft
from typing import Optional

def MetricCard(
    title: str,
    value: str,
    icon: str,
    color: str = ft.Colors.BLUE_400,
    help_text: Optional[str] = None,
) -> ft.Control:
    """
    A premium Metric Card component for the Flet dashboard.
    """
    return ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(icon, color=color, size=24),
                            ft.Text(title, size=16, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_400),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=10,
                    ),
                    ft.Text(value, size=28, weight=ft.FontWeight.BOLD),
                    ft.Text(help_text if help_text else "", size=12, italic=True, color=ft.Colors.GREY_600) if help_text else ft.Container(),
                ],
                spacing=5,
            ),
            padding=20,
            width=260,
        ),
        elevation=2,
    )

def ChartContainer(
    title: str,
    content: ft.Control,
    expand: bool = True,
    height: Optional[int] = 400,
) -> ft.Control:
    """
    A standard container for charts in the Flet analytics view.
    """
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=content,
                    expand=True,
                    height=height,
                    border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=10,
                    padding=10,
                ),
            ],
            spacing=10,
        ),
        expand=expand,
    )
