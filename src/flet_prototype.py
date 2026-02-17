import flet as ft
from pathlib import Path
import sys

# Add src to path if needed to reuse logic
sys.path.append(str(Path(__file__).parent))

# Dummy translations for the prototype (simplified)
T = {
    "en": {
        "page_title": "Ledger Smart Converter",
        "nav_import": "Import Files",
        "nav_analytics": "Analytics Dashboard",
        "select_bank": "Select Bank",
        "process_files": "Process Files",
        "upload_pdf": "Upload PDF Statement",
        "upload_data": "Upload Data File (XML/XLSX)",
        "use_ocr": "Use OCR for PDF",
        "ready": "Ready to process",
    },
    "es": {
        "page_title": "Convertidor Inteligente",
        "nav_import": "Importar Archivos",
        "nav_analytics": "Panel de Control",
        "select_bank": "Seleccionar Banco",
        "process_files": "Procesar Archivos",
        "upload_pdf": "Subir Estado de Cuenta PDF",
        "upload_data": "Subir Archivo de Datos (XML/XLSX)",
        "use_ocr": "Usar OCR para PDF",
        "ready": "Listo para procesar",
    }
}

def main(page: ft.Page):
    page.title = "Ledger Smart Converter (Flet Prototype)"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 40
    page.spacing = 20
    
    # State
    lang = "en"
    
    def t(key):
        return T[lang].get(key, key)

    # File upload state
    pdf_file_name = ft.Text("", size=12, color=ft.Colors.GREY_400)
    data_file_name = ft.Text("", size=12, color=ft.Colors.GREY_400)
    
    def pick_pdf_file(e):
        pdf_file_name.value = "📄 Click 'Select File' to choose PDF"
        status_text.value = "Ready to select PDF file"
        page.update()
    
    def pick_data_file(e):
        data_file_name.value = "📊 Click 'Select File' to choose data file"
        status_text.value = "Ready to select data file"
        page.update()

    # UI Components
    header = ft.Row(
        [
            ft.Text(t("page_title"), size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400),
            ft.VerticalDivider(),
            ft.Text("Flet Prototype", size=16, color=ft.Colors.GREY_500),
        ],
        alignment=ft.MainAxisAlignment.START,
    )

    bank_dropdown = ft.Dropdown(
        width=300,
        label=t("select_bank"),
        options=[
            ft.dropdown.Option("Santander LikeU"),
            ft.dropdown.Option("HSBC Mexico"),
        ],
        value="Santander LikeU",
    )

    # Interaction logic
    def on_process_click(e):
        process_btn.disabled = True
        progress_bar.visible = True
        status_text.value = "Analyzing files with AI..."
        page.update()
        
        # Simulate work
        import time
        time.sleep(1.5)
        
        status_text.value = "Success! Transactions extracted."
        progress_bar.visible = False
        process_btn.disabled = False
        page.update()

    process_btn = ft.Button(
        content=ft.Text(t("process_files")),
        icon=ft.Icons.AUTO_FIX_HIGH,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.BLUE_700,
            padding=20,
        ),
        on_click=on_process_click
    )

    progress_bar = ft.ProgressBar(width=400, color="blue", visible=False)
    status_text = ft.Text(t("ready"), italic=True, color=ft.Colors.GREY_400)

    # Layout Sections
    import_content = ft.Column(
        [
            bank_dropdown,
            ft.Divider(),
            ft.Row([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.PICTURE_AS_PDF, size=40, color=ft.Colors.RED_400),
                            ft.Text(t("upload_pdf"), weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                            ft.Button(
                                content=ft.Text("Select File"),
                                on_click=pick_pdf_file,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700)
                            ),
                            pdf_file_name,
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        padding=20, width=250, height=180
                    ),
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.TABLE_CHART, size=40, color=ft.Colors.GREEN_400),
                            ft.Text(t("upload_data"), weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                            ft.Button(
                                content=ft.Text("Select File"),
                                on_click=pick_data_file,
                                style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700)
                            ),
                            data_file_name,
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        padding=20, width=250, height=180
                    ),
                ),
            ], spacing=20),
            ft.Checkbox(label=t("use_ocr"), value=False),
            ft.Container(height=20),
            process_btn,
            progress_bar,
            status_text,
        ],
        spacing=20,
    )

    analytics_content = ft.Container(content=ft.Text("Analytics prototype goes here..."), padding=20)
    
    tabs = ft.Tabs(
        length=2,
        content=ft.Column(
            [
                ft.TabBar(
                    tabs=[
                        ft.Tab(label=t("nav_import"), icon=ft.Icons.UPLOAD_FILE),
                        ft.Tab(label=t("nav_analytics"), icon=ft.Icons.INSERT_CHART),
                    ],
                ),
                ft.TabBarView(
                    controls=[
                        import_content,
                        analytics_content,
                    ],
                    expand=True,
                ),
            ],
            expand=True,
        ),
        expand=True,
    )

    page.add(header, tabs)

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
