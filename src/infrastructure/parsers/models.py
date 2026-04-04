from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class TxnRaw:
    date: str
    description: str
    amount: float
    rfc: str = ""
    account_hint: str = ""
    source: str = "data"
    page: int = 0
    source_line: str = ""

def parse_iso_date(s: str) -> str:
    s = (s or "").strip()
    if not s: return ""
    try:
        dt = datetime.fromisoformat(s)
        return dt.date().isoformat()
    except ValueError:
        return s[:10]
