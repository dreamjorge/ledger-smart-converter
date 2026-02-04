#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple feedback loop that compares the OCR-derived PDF transactions against the XML
reference, capturing mismatches and raw OCR lines so you can tune the extraction logic.
"""

import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdf_utils as pu
from import_hsbc_cfdi_firefly import (
    TxnRaw,
    apply_xml_reference_to_pdf,
    extract_movimientos,
    get_addenda,
    get_datos_generales,
)


AMOUNT_RX = re.compile(r"([-+]?\d[\d\.,]*[.,]\d{2})")


def serialize_txn(txn: TxnRaw) -> Dict[str, Any]:
    return {
        "date": txn.date,
        "amount": txn.amount,
        "description": txn.description,
        "rfc": txn.rfc,
        "source": txn.source,
        "page": txn.page,
        "line": txn.source_line,
    }


def parse_xml_reference(xml_path: Path) -> Tuple[List[TxnRaw], Dict[str, str]]:
    text = xml_path.read_text(encoding="utf-8", errors="ignore")
    root = ET.fromstring(text)
    addenda = get_addenda(root)
    if addenda is None:
        raise ValueError("No cfdi:Addenda found in the XML.")
    datos = get_datos_generales(addenda)
    txns = extract_movimientos(addenda)
    return txns, datos


def build_pdf_txns(pdf_rows: List[Dict[str, Any]], year: int) -> List[TxnRaw]:
    out: List[TxnRaw] = []
    for row in pdf_rows:
        iso = pu.parse_mx_date(row["raw_date"], year=year)
        if not iso:
            continue
        out.append(TxnRaw(
            date=iso,
            description=row["description"],
            amount=row["amount"],
            rfc="",
            account_hint="",
            source="pdf",
            page=row.get("page", 0),
            source_line=row.get("line", "").strip(),
        ))
    return out


def detect_amount_in_line(text: str) -> Optional[float]:
    m = AMOUNT_RX.search(text)
    if not m:
        return None
    candidate = m.group(1).replace(" ", "")
    if candidate.count(",") and candidate.count("."):
        if candidate.rfind(",") > candidate.rfind("."):
            candidate = candidate.replace(".", "").replace(",", ".")
        else:
            candidate = candidate.replace(",", "")
    else:
        candidate = candidate.replace(",", "")
    try:
        return float(candidate)
    except ValueError:
        return None


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate OCR feedback between HSBC PDF and XML.")
    ap.add_argument("--pdf", required=True, help="Ruta al estado de cuenta en PDF.")
    ap.add_argument("--xml", required=True, help="CFDI XML para referencia.")
    ap.add_argument("--out-dir", default="data/hsbc/feedback", help="Directorio para volcar los reportes.")
    ap.add_argument("--force-year", type=int, help="Sobrescribe el año usado para parsear fechas OCR.")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    xml_path = Path(args.xml)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return 2
    if not xml_path.exists():
        print(f"ERROR: XML not found: {xml_path}")
        return 2

    pdf_meta = pu.extract_pdf_metadata(pdf_path)
    year = args.force_year or datetime.now().year
    if "cutoff_date" in pdf_meta:
        m = re.search(r"(\d{4})", pdf_meta["cutoff_date"])
        if m:
            year = int(m.group(1))

    pdf_rows = pu.extract_transactions_from_pdf(pdf_path, use_ocr=True)
    pdf_txns = build_pdf_txns(pdf_rows, year=year)
    xml_txns, xml_meta = parse_xml_reference(xml_path)
    _, summary = apply_xml_reference_to_pdf(pdf_txns, xml_txns)

    raw_lines = pu.collect_pdf_lines(pdf_path, use_ocr=True)
    annotated_lines = []
    for line in raw_lines:
        amt = detect_amount_in_line(line["text"])
        annotated_lines.append({
            "page": line["page"],
            "method": line["method"],
            "text": line["text"],
            "amount": amt,
        })

    feedback = {
        "metadata": {
            "pdf_file": str(pdf_path.resolve()),
            "xml_file": str(xml_path.resolve()),
            "rules": "config/rules.yml",
            "xml_summary": xml_meta,
            "pdf_summary": {
                "rows_extracted": len(pdf_rows),
                "transactions": len(pdf_txns),
            },
        },
        "summary": {
            "matched": summary["matched"],
            "total_pdf": summary["total_pdf"],
            "total_xml": summary["total_xml"],
            "differences": summary["differences"],
        },
        "pdf_only": [serialize_txn(txn) for txn in summary["pdf_only"]],
        "xml_only": [serialize_txn(txn) for txn in summary["xml_only"]],
        "raw_lines": annotated_lines,
    }

    summary_path = out_dir / "feedback_summary.json"
    summary_path.write_text(json.dumps(feedback, indent=2, ensure_ascii=False), encoding="utf-8")

    if feedback["pdf_only"]:
        write_csv(out_dir / "pdf_only.csv", feedback["pdf_only"], ["date", "amount", "page", "description", "line"])
    if feedback["xml_only"]:
        write_csv(out_dir / "xml_only.csv", feedback["xml_only"], ["date", "amount", "page", "description", "line"])
    if annotated_lines:
        write_csv(out_dir / "raw_lines.csv", annotated_lines, ["page", "method", "amount", "text"])

    print(f"Feedback report written to {summary_path}")
    print(f"  PDF-only rows: {len(feedback['pdf_only'])}")
    print(f"  XML-only rows: {len(feedback['xml_only'])}")
    print(f"  Raw OCR lines captured: {len(annotated_lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
