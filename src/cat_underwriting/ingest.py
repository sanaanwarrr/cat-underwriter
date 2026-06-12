from __future__ import annotations

from pathlib import Path
import json

import pandas as pd


def read_document(path: str | Path) -> str:
    """Read common underwriting submission files into text/markdown.

    Order of preference:
    1. Microsoft MarkItDown, if installed.
    2. Simple local readers for .txt/.md/.csv/.xlsx/.pdf.

    This keeps the MVP runnable even before optional document AI dependencies are installed.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    markitdown_text = _try_markitdown(file_path)
    if markitdown_text:
        return markitdown_text

    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        return file_path.read_text(encoding="utf-8")

    if suffix == ".csv":
        df = pd.read_csv(file_path)
        return df.to_markdown(index=False)

    if suffix in {".xlsx", ".xls"}:
        sheets = pd.read_excel(file_path, sheet_name=None)
        parts = []
        for sheet_name, df in sheets.items():
            parts.append(f"# Sheet: {sheet_name}\n" + df.to_markdown(index=False))
        return "\n\n".join(parts)

    if suffix == ".json":
        return json.dumps(json.loads(file_path.read_text(encoding="utf-8")), indent=2)

    if suffix == ".pdf":
        return _read_pdf(file_path)

    raise ValueError(
        f"Unsupported file type {suffix}. Install markitdown/docling for broader support."
    )


def _try_markitdown(path: Path) -> str | None:
    try:
        from markitdown import MarkItDown  # type: ignore

        result = MarkItDown().convert(str(path))
        return result.text_content
    except Exception:
        return None


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("Install pypdf or markitdown to read PDFs") from exc

    reader = PdfReader(str(path))
    pages = []
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(f"\n\n--- Page {idx} ---\n{text}")
    return "".join(pages).strip()
