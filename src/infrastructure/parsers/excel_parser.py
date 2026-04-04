import pandas as pd
from pathlib import Path
from typing import List

from infrastructure.parsers.base_parser import StatementParser
from infrastructure.parsers.models import TxnRaw, parse_iso_date
from date_utils import parse_spanish_date as parse_es_date
import common_utils as cu

class ExcelParser(StatementParser):
    """Parser for Excel/CSV statement files."""
    
    def parse(self, file_path: Path, bank_type: str = "generic") -> List[TxnRaw]:
        # Implementation depends on the configured bank format type
        if bank_type == "xlsx":
            return self._load_xlsx(file_path)
        else:
            return self._load_generic(file_path)
            
    def _load_xlsx(self, path: Path) -> List[TxnRaw]:
        df = pd.read_excel(path, header=None)
        # Find header row (generic: look for "FECHA")
        header_idx = 0
        for i in range(min(20, len(df))):
            if any("FECHA" in str(v).upper() for v in df.iloc[i]):
                header_idx = i
                break
        
        df.columns = [str(c).strip().lower() for c in df.iloc[header_idx]]
        df = df.iloc[header_idx+1:].dropna(subset=["fecha", "concepto", "importe"], how="any")
        
        out = []
        for _, r in df.iterrows():
            date = parse_es_date(str(r["fecha"]))
            amt = cu.parse_money(r["importe"])
            if date and amt is not None:
                out.append(TxnRaw(
                    date=date, 
                    description=str(r["concepto"]).strip(), 
                    amount=amt
                ))
        return out

    def _load_generic(self, path: Path) -> List[TxnRaw]:
        df = pd.read_excel(path) if path.suffix.lower() in [".xlsx", ".xls"] else pd.read_csv(path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Heuristic mapping
        col_map = {}
        for c in df.columns:
            if any(k in c for k in ["fecha", "date"]): col_map["date"] = c
            if any(k in c for k in ["desc", "concepto", "descripcion"]): col_map["desc"] = c
            if any(k in c for k in ["importe", "amount", "monto"]): col_map["amt"] = c
            
        if "date" not in col_map or "desc" not in col_map: return []
        
        out = []
        for _, r in df.iterrows():
            date = parse_iso_date(str(r[col_map["date"]])) or parse_es_date(str(r[col_map["date"]]))
            amt = cu.parse_money(r[col_map["amt"]]) if "amt" in col_map else 0.0
            if date and amt is not None:
                out.append(TxnRaw(date=date, description=str(r[col_map["desc"]]), amount=amt))
        return out
