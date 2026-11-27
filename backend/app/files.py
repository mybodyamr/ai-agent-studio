from pathlib import Path
from uuid import uuid4
from pypdf import PdfReader
from openpyxl import load_workbook
from .config import settings

ALLOWED = {".txt",".md",".csv",".json",".py",".js",".ts",".tsx",".html",".css",".pdf",".xlsx",".xlsm"}

def workspace():
    p=Path(settings.workspace_path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p

def safe_path(name: str):
    suffix=Path(name).suffix.lower()
    if suffix not in ALLOWED:
        raise ValueError("Unsupported file type.")
    return workspace() / f"{uuid4().hex}{suffix}"

def extract_text(path: Path):
    suffix=path.suffix.lower()
    if suffix in {".txt",".md",".csv",".json",".py",".js",".ts",".tsx",".html",".css"}:
        return path.read_text(encoding="utf-8", errors="replace")[:500_000]
    if suffix == ".pdf":
        reader=PdfReader(str(path))
        return "\n".join(p.extract_text() or "" for p in reader.pages)[:500_000]
    if suffix in {".xlsx",".xlsm"}:
        wb=load_workbook(path, read_only=True, data_only=True)
        rows=[]
        try:
            for ws in wb.worksheets:
                rows.append(f"## {ws.title}")
                for row in ws.iter_rows(values_only=True):
                    rows.append(" | ".join("" if v is None else str(v) for v in row))
        finally:
            wb.close()
        return "\n".join(rows)[:500_000]
    raise ValueError("Unsupported file type.")
