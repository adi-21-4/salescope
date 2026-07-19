from pathlib import Path

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class UnsupportedFileTypeError(Exception):
    pass


def file_type_from_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Unsupported file type: {ext or '(none)'}")
    return "csv" if ext == ".csv" else "xlsx"


def parse_file(path: Path, file_type: str) -> pd.DataFrame:
    """Read a raw upload into a DataFrame with every column as string.

    dtype=str keeps pandas from guessing types before column_detector.py (M2) gets
    a chance to sniff each column's role — a premature int64/float64 cast here would
    throw away formatting information (e.g. currency symbols, leading zeros in SKUs)
    that the detection heuristics rely on.
    """
    if file_type == "csv":
        return pd.read_csv(path, dtype=str, keep_default_na=True)
    return pd.read_excel(path, dtype=str, engine="openpyxl")
