import flet as ft
from pathlib import Path
from typing import Callable, Dict
import threading
from services import import_service as imp
from services.import_service import get_banks_from_config

def get_import_view(page: ft.Page, t: Callable, config: Dict):
    """
    Flet implementation of the Import Page.
    """
    root_dir = Path.cwd()
    banks_cfg = get_banks_from_config(root_dir / "config" / "rules.yml")
    first_bank_id = next(iter(banks_cfg), "santander_likeu")

    # State
    state = {
        "selected_bank_id": first_bank_id,
        "main_file_path": None,
        "pdf_file_path": None,
        "force_ocr": False,
        "loading": False,
        "results": None,
        "duplicate_rows": [],
        "dedup_decisions": {},
    }

    def _build_dedup_table(duplicate_rows, state, t, page):
        """Build a DataTable showing duplicate rows with per-row decision dropdowns."""
        action_options = [
            ft.dropdown.Option("skip", t("dedup_action_skip")),
            ft.dropdown.Option("overwrite", t("dedup_action_overwrite")),
            ft.dropdown.Option("keep_both", t("dedup_action_keep_both")),
        ]

        rows = []
        for row in duplicate_rows[:50]:
            h = row.get("source_hash", "")
            state["dedup_decisions"].setdefault(h, "skip")

            def make_on_change(hash_key):
                return lambda e: state["dedup_decisions"].update({hash_key: e.control.value})

            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(row.get("date", "")), size=12)),
                ft.DataCell(ft.Text(str(row.get("description", ""))[:40], size=12)),
                ft.DataCell(ft.Text(f"{row.get('amount', '')}", size=12)),
                ft.DataCell(ft.Dropdown(
                    options=action_options,
                    value="skip",
                    width=160,
                    on_select=make_on_change(h),
                )),
            ]))

        def handle_apply_decisions(e):
            try:
                from services.dedup_service import resolve_duplicates
                from services.db_service import DatabaseService
                from settings import load_settings
                settings = load_settings()
                db = DatabaseService(db_path=settings.data_dir / "ledger.db")
                counts = resolve_duplicates(
                    db=db,
                    duplicate_rows=state["duplicate_rows"],
                    decisions=state["dedup_decisions"],
                )
                page.snack_bar = ft.SnackBar(ft.Text(t(
                    "dedup_resolved",
                    overwritten=counts["overwritten"],
                    kept_both=counts["kept_both"],
                    skipped=counts["skipped"],
                )))
                page.snack_bar.open = True
                state["duplicate_rows"] = []
                state["dedup_decisions"] = {}
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"))
                page.snack_bar.open = True
                page.update()

        return ft.Column([
            ft.Text(t("dedup_review_title"), weight=ft.FontWeight.BOLD),
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Date")),
                    ft.DataColumn(ft.Text("Description")),
                    ft.DataColumn(ft.Text("Amount")),
                    ft.DataColumn(ft.Text("Decision")),
                ],
                rows=rows,
            ),
            ft.ElevatedButton(
                t("dedup_apply_decisions"),
                icon=ft.Icons.CHECK_CIRCLE,
                on_click=handle_apply_decisions,
                bgcolor=ft.Colors.ORANGE_700,
                color=ft.Colors.WHITE,
            ),
        ], spacing=10)

    # Helper to get bank config for the currently selected bank
    def get_bank_cfg():
        entry = banks_cfg.get(state["selected_bank_id"], {})
        return {
            "label": entry.get("display_name", state["selected_bank_id"]),
            "type": entry.get("type", "xlsx"),
        }

    def _quick_start_content() -> ft.Control:
        bank_cfg = get_bank_cfg()
        bank_label = bank_cfg["label"]
        file_type_label = "Excel" if bank_cfg["type"] == "xlsx" else "XML"
        tip_key = "tip_santander" if state["selected_bank_id"] == "santander_likeu" else "tip_hsbc"

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(t("quick_start"), size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(t("welcome_bank", bank=bank_label)),
                    ft.Text(t("steps_desc"), color=ft.Colors.GREY_400),
                    ft.Text(t("step_1", file_type=file_type_label)),
                    ft.Text(t("step_2")),
                    ft.Text(t("step_3")),
                    ft.Text(t("step_4")),
                    ft.Container(
                        content=ft.Text(t(tip_key), color=ft.Colors.BLUE_200),
                        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                        border_radius=10,
                        padding=12,
                    ),
                ],
                spacing=8,
            ),
            padding=16,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border_radius=12,
        )

    # UI Components
    status_text = ft.Text("", italic=True, color=ft.Colors.BLUE_400)
    progress_bar = ft.ProgressBar(width=400, color=ft.Colors.BLUE_400, visible=False)
    
    main_file_text = ft.Text(t("select_xlsx"), color=ft.Colors.GREY_400)
    pdf_file_text = ft.Text(t("select_pdf"), color=ft.Colors.GREY_400)

    # File Pickers
    main_picker = ft.FilePicker()
    pdf_picker = ft.FilePicker()
    page.services.extend([main_picker, pdf_picker])

    async def handle_pick_main(_):
        files = await main_picker.pick_files(allow_multiple=False)
        if files:
            state["main_file_path"] = files[0].path
            main_file_text.value = f"✅ {files[0].name}"
            main_file_text.color = ft.Colors.GREEN_400
            page.update()

    async def handle_pick_pdf(_):
        files = await pdf_picker.pick_files(allow_multiple=False)
        if files:
            state["pdf_file_path"] = files[0].path
            pdf_file_text.value = f"✅ {files[0].name}"
            pdf_file_text.color = ft.Colors.GREEN_400
            page.update()

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

                    new_controls = [
                        ft.Text(f"CSV Generated: {out_csv.name}", color=ft.Colors.GREEN_200),
                        ft.Text(f"Unknown Merchants: {out_unknown.name}", color=ft.Colors.ORANGE_200 if out_unknown.exists() else ft.Colors.GREY_400),
                    ]

                    # Run deduplication migration
                    if out_csv.exists():
                        try:
                            from csv_to_db_migrator import migrate_csvs_to_db_with_dedup
                            from settings import load_settings
                            settings = load_settings()
                            dedup_summary, duplicate_rows = migrate_csvs_to_db_with_dedup(
                                db_path=settings.data_dir / "ledger.db",
                                data_dir=data_dir,
                                accounts_path=root_dir / "config" / "accounts.yml",
                                csv_paths=[out_csv],
                            )
                            inserted = dedup_summary.get("rows_inserted", 0)
                            new_controls.append(
                                ft.Text(t("dedup_rows_inserted", n=inserted), color=ft.Colors.BLUE_200)
                            )
                            state["duplicate_rows"] = duplicate_rows
                            if duplicate_rows:
                                new_controls.append(
                                    ft.Text(t("dedup_rows_skipped", n=len(duplicate_rows)), color=ft.Colors.ORANGE_400)
                                )
                                new_controls.append(_build_dedup_table(duplicate_rows, state, t, page))
                        except Exception as dedup_exc:
                            new_controls.append(
                                ft.Text(f"DB sync warning: {dedup_exc}", color=ft.Colors.GREY_400, size=12)
                            )

                    results_col.controls = new_controls
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
            ft.Text(t("import_header", bank=get_bank_cfg()["label"]), size=32, weight=ft.FontWeight.BOLD),
            ft.Text(t("sidebar_desc"), size=16, color=ft.Colors.GREY_400),
            _quick_start_content(),
            ft.Divider(),
            
            ft.Row([
                ft.Dropdown(
                    label=t("select_bank"),
                    width=300,
                    options=[
                        ft.dropdown.Option(bid, bcfg["display_name"])
                        for bid, bcfg in banks_cfg.items()
                    ],
                    value=state["selected_bank_id"],
                    on_select=lambda e: (state.update({"selected_bank_id": e.control.value}), page.update()),
                ),
            ]),

            ft.Row([
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.UPLOAD_FILE, size=40, color=ft.Colors.BLUE_400),
                            ft.Text(t("select_xlsx") if get_bank_cfg()["type"] == "xlsx" else t("select_xml"), weight=ft.FontWeight.BOLD),
                            ft.ElevatedButton("Browse", on_click=handle_pick_main),
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
                            ft.ElevatedButton("Browse", on_click=handle_pick_pdf),
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
            ft.Text(f"{t('working_dir')}: {root_dir}", size=12, color=ft.Colors.GREY_500),
        ],
        expand=True,
        spacing=20,
        scroll=ft.ScrollMode.ADAPTIVE,
    )
