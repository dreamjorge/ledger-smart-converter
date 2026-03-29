import flet as ft
from pathlib import Path
from typing import Callable, Dict
import threading
from services import import_service as imp

def get_import_view(page: ft.Page, t: Callable, config: Dict):
    """
    Flet implementation of the Import Page.
    """
    # State
    state = {
        "selected_bank_id": "santander_likeu",
        "main_file_path": None,
        "pdf_file_path": None,
        "force_ocr": False,
        "loading": False,
        "results": None
    }

    # Helper to get bank config
    def get_bank_cfg():
        banks = {
            "santander_likeu": {"label": t("bank_santander"), "type": "xlsx"},
            "hsbc": {"label": t("bank_hsbc"), "type": "xml"}
        }
        return banks.get(state["selected_bank_id"])

    # UI Components
    status_text = ft.Text("", italic=True, color=ft.Colors.BLUE_400)
    progress_bar = ft.ProgressBar(width=400, color=ft.Colors.BLUE_400, visible=False)
    
    main_file_text = ft.Text(t("select_xlsx"), color=ft.Colors.GREY_400)
    pdf_file_text = ft.Text(t("select_pdf"), color=ft.Colors.GREY_400)

    # File Pickers
    def on_main_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            state["main_file_path"] = e.files[0].path
            main_file_text.value = f"✅ {e.files[0].name}"
            main_file_text.color = ft.Colors.GREEN_400
            page.update()

    def on_pdf_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            state["pdf_file_path"] = e.files[0].path
            pdf_file_text.value = f"✅ {e.files[0].name}"
            pdf_file_text.color = ft.Colors.GREEN_400
            page.update()

    main_picker = ft.FilePicker(on_result=on_main_file_result)
    pdf_picker = ft.FilePicker(on_result=on_pdf_file_result)
    page.overlay.extend([main_picker, pdf_picker])

    # Handlers
    def handle_process(e):
        if not state["main_file_path"] and not (state["force_ocr"] and state["pdf_file_path"]):
            page.snack_bar = ft.SnackBar(ft.Text("Please select a file first!"))
            page.snack_bar.open = True
            page.update()
            return

        state["loading"] = True
        progress_bar.visible = True
        status_text.value = t("processing")
        process_btn.disabled = True
        page.update()

        def _run():
            try:
                root_dir = Path.cwd()
                data_dir = root_dir / "data"
                temp_dir = root_dir / "temp" / "input"
                temp_dir.mkdir(parents=True, exist_ok=True)

                bank_cfg = get_bank_cfg()
                bank_id = state["selected_bank_id"]
                bank_label = bank_cfg["label"]

                out_csv, out_unknown, out_suggestions = imp.resolve_output_paths(
                    data_dir=data_dir,
                    bank_label=bank_label,
                    bank_id=bank_id,
                    analytics_targets={}
                )

                res = imp.run_import_script(
                    root_dir=root_dir,
                    src_dir=root_dir / "src",
                    bank_id=bank_id,
                    rules_path=root_dir / "config" / "rules.yml",
                    out_csv=out_csv,
                    out_unknown=out_unknown,
                    main_path=Path(state["main_file_path"]) if state["main_file_path"] else None,
                    pdf_path=Path(state["pdf_file_path"]) if state["pdf_file_path"] else None,
                    force_pdf_ocr=state["force_ocr"]
                )

                if res.returncode == 0:
                    status_text.value = t("process_complete")
                    status_text.color = ft.Colors.GREEN_400
                    results_col.controls = [
                        ft.Text(f"CSV Generated: {out_csv.name}", color=ft.Colors.GREEN_200),
                        ft.Text(f"Unknown Merchants: {out_unknown.name}", color=ft.Colors.ORANGE_200 if out_unknown.exists() else ft.Colors.GREY_400),
                    ]
                else:
                    status_text.value = t("error_processing")
                    status_text.color = ft.Colors.RED_400
                    results_col.controls = [ft.Text(res.stderr, color=ft.Colors.RED_200)]

            except Exception as ex:
                status_text.value = f"Error: {str(ex)}"
                status_text.color = ft.Colors.RED_400

            state["loading"] = False
            progress_bar.visible = False
            process_btn.disabled = False
            page.update()

        threading.Thread(target=_run, daemon=True).start()

    # View Construction
    process_btn = ft.ElevatedButton(
        t("process_files"),
        icon=ft.Icons.PLAY_ARROW,
        on_click=handle_process,
        bgcolor=ft.Colors.BLUE_700,
        color=ft.Colors.WHITE,
        height=50,
    )

    results_col = ft.Column(spacing=10)

    return ft.Column(
        [
            ft.Text(t("nav_import"), size=32, weight=ft.FontWeight.BOLD),
            ft.Text(t("sidebar_desc"), size=16, color=ft.Colors.GREY_400),
            ft.Divider(),
            
            ft.Row([
                ft.Dropdown(
                    label=t("select_bank"),
                    width=300,
                    options=[
                        ft.dropdown.Option("santander_likeu", t("bank_santander")),
                        ft.dropdown.Option("hsbc", t("bank_hsbc")),
                    ],
                    value=state["selected_bank_id"],
                    on_change=lambda e: (state.update({"selected_bank_id": e.data}), page.update()),
                ),
            ]),

            ft.Row([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.UPLOAD_FILE, size=40, color=ft.Colors.BLUE_400),
                            ft.Text(t("select_xlsx") if get_bank_cfg()["type"] == "xlsx" else t("select_xml"), weight=ft.FontWeight.BOLD),
                            ft.ElevatedButton("Browse", on_click=lambda _: main_picker.pick_files()),
                            main_file_text,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=20, width=280, height=180
                    )
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.PICTURE_AS_PDF, size=40, color=ft.Colors.RED_400),
                            ft.Text(t("select_pdf"), weight=ft.FontWeight.BOLD),
                            ft.ElevatedButton("Browse", on_click=lambda _: pdf_picker.pick_files()),
                            pdf_file_text,
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=20, width=280, height=180
                    )
                ),
            ], spacing=20),

            ft.Checkbox(
                label=t("use_ocr"),
                value=state["force_ocr"],
                on_change=lambda e: (state.update({"force_ocr": e.control.value}), page.update())
            ),

            ft.Container(height=10),
            process_btn,
            progress_bar,
            status_text,
            ft.Divider(),
            results_col,
        ],
        expand=True,
        spacing=20,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
