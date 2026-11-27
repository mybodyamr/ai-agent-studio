from pathlib import Path
from uuid import uuid4
from io import BytesIO
from zipfile import ZipFile, BadZipFile
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

def validate_file_content(name: str, data: bytes):
    suffix=Path(name).suffix.lower()
    if not data:
        raise ValueError("The uploaded file is empty.")
    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("The file content does not match a PDF.")
    elif suffix in {".xlsx", ".xlsm"}:
        if not data.startswith(b"PK\x03\x04"):
            raise ValueError("The file content does not match an Excel workbook.")
        try:
            with ZipFile(BytesIO(data)) as archive:
                items=archive.infolist()
                total=sum(item.file_size for item in items)
                if len(items)>2000 or total>50_000_000:
                    raise ValueError("Excel archive expands beyond the safe processing limit.")
                if any(item.file_size > 0 and item.file_size / max(item.compress_size,1) > 100 for item in items):
                    raise ValueError("Excel archive compression ratio is too high.")
                names=set(archive.namelist())
                if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                    raise ValueError("The uploaded ZIP is not a valid Excel workbook.")
        except BadZipFile:
            raise ValueError("The Excel workbook archive is invalid.")
    elif b"\x00" in data:
        raise ValueError("Binary content is not allowed for text file types.")

def extract_text(path: Path):
    suffix=path.suffix.lower()
    if suffix in {".txt",".md",".csv",".json",".py",".js",".ts",".tsx",".html",".css"}:
        return path.read_text(encoding="utf-8", errors="replace")[:500_000]
    if suffix == ".pdf":
        reader=PdfReader(str(path))
        if len(reader.pages)>500:
            raise ValueError("PDF exceeds the 500-page processing limit.")
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
