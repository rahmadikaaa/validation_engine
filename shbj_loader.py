"""
shbj_loader.py — SHBJ 2025 Historical Data Loader for SIPVAL.

Loads the SHBJ 2025 kertas kerja CSV from data/ folder.
Provides matching functions for Item Detail budget comparison.

Column mapping from the real SHBJ 2025 file:
  - 'ID'             → item code
  - 'Nama Barang'    → item name (primary match key)
  - 'Spesifikasi'    → specification (secondary match key)
  - 'Satuan'         → unit of measure
  - ' Harga Satuan'  → SHBJ reference price (note: leading space in column name)
  - ' Est. Harga 2025' → estimated price for 2025 (note: leading space)
  - 'Kategori'       → category (fallback match)
  - 'Sub kategori'   → subcategory (fallback match)
  - 'Keterangan'     → e.g. "TAHAP 2 FINAL"

Matching priority:
  1. Exact normalized item name + specification keyword
  2. Exact normalized item name (any spec)
  3. Category fallback (first item in same category)
  → If none match: return None (no fabrication)
"""

import os
import re
import pandas as pd
from typing import Optional, Dict, Any, Tuple

SHBJ_CSV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "KERTAS KERJA FINAL SHBJ DKI JAKARTA 2025 (13-06-2025) - SEND - Copy.csv",
)

# -----------------------------------------------------------------
# Internal: price string parser
# -----------------------------------------------------------------

def _parse_rp(s: Any) -> Optional[float]:
    """Parse an Indonesian Rupiah string like ' Rp10.341 ' into a float."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    text = str(s).strip()
    if not text or text.lower() in ("nan", "-", ""):
        return None
    # Remove Rp, whitespace, non-numeric except dot and comma
    text = re.sub(r"[Rp\s]", "", text)
    # Indonesian format: dots as thousand sep, comma as decimal
    # e.g. "1.234.567" or "1.234,56"
    # Strategy: remove all dots first, then replace comma with dot
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_name(s: Any) -> str:
    """Lowercase, strip, collapse whitespace for fuzzy matching."""
    return re.sub(r"\s+", " ", str(s).lower().strip())


# -----------------------------------------------------------------
# Load SHBJ
# -----------------------------------------------------------------

def load_shbj_data() -> pd.DataFrame:
    """Load and preprocess the SHBJ 2025 CSV.
    
    Returns an empty DataFrame with correct columns if the file is missing.
    """
    if not os.path.exists(SHBJ_CSV_PATH):
        return pd.DataFrame(columns=[
            "ID", "Nama Barang", "Spesifikasi", "Satuan",
            "harga_satuan_parsed", "est_harga_2025_parsed",
            "Kategori", "Sub kategori", "nama_norm", "Keterangan",
        ])

    df = pd.read_csv(
        SHBJ_CSV_PATH,
        encoding="latin1",
        sep=";",
        low_memory=False,
        dtype=str,          # read everything as str to avoid mixed-type issues
    )

    # Strip all column names of leading/trailing whitespace
    df.columns = df.columns.str.strip()

    # Strip all string cell values
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    # Parse the key price columns
    df["harga_satuan_parsed"] = df["Harga Satuan"].apply(_parse_rp)
    df["est_harga_2025_parsed"] = df["Est. Harga 2025"].apply(_parse_rp)

    # Normalized name for matching
    df["nama_norm"] = df["Nama Barang"].apply(_normalize_name)

    # Keep only rows that have at least a name
    df = df[df["Nama Barang"].notna() & (df["Nama Barang"].str.strip() != "")]

    return df.reset_index(drop=True)


# -----------------------------------------------------------------
# Matching
# -----------------------------------------------------------------

def _spec_keywords(spec_text: Any) -> set:
    """Extract meaningful keywords from a specification string."""
    text = str(spec_text).lower()
    # Extract numbers (dimensions like 265/60, R18, 4.00-8, etc.)
    numbers = set(re.findall(r"[\d.,/\-]+", text))
    # Extract significant words (>= 3 chars, skip common filler)
    skip = {"dan", "atau", "untuk", "dengan", "yang", "dari", "nan", "ukuran", "uk", "uk."}
    words = {w for w in re.findall(r"[a-z]{3,}", text) if w not in skip}
    return numbers | words


def find_shbj_match(
    item_name: str,
    item_spec: str = "",
    item_satuan: str = "",
    item_kategori: str = "",
    shbj_df: pd.DataFrame = None,
) -> Optional[Dict[str, Any]]:
    """Find the best SHBJ 2025 row matching a procurement item.
    
    Returns a dict with matching data, or None if no match found.
    Never fabricates values.
    """
    if shbj_df is None or shbj_df.empty:
        return None

    # ---- Strip spec prefix from combined field ----
    raw_name = str(item_name)
    if "Spesifikasi:" in raw_name:
        parts = raw_name.split("Spesifikasi:", 1)
        item_name = parts[0].strip()
        if not item_spec:
            item_spec = parts[1].strip()

    name_norm = _normalize_name(item_name)
    spec_kw = _spec_keywords(item_spec)
    satuan_norm = _normalize_name(item_satuan)
    kategori_norm = _normalize_name(item_kategori)

    # ---- Pass 1: Exact name + spec keyword overlap + same satuan ----
    name_mask = shbj_df["nama_norm"] == name_norm
    candidates = shbj_df[name_mask].copy()

    if not candidates.empty and spec_kw:
        def spec_score(row):
            row_kw = _spec_keywords(row.get("Spesifikasi", ""))
            if not row_kw:
                return 0
            return len(spec_kw & row_kw) / max(len(spec_kw), 1)

        candidates["_spec_score"] = candidates.apply(spec_score, axis=1)

        # Filter by satuan if possible
        if satuan_norm:
            sat_mask = candidates["Satuan"].apply(_normalize_name) == satuan_norm
            sat_candidates = candidates[sat_mask]
            if not sat_candidates.empty:
                candidates = sat_candidates

        best = candidates.sort_values("_spec_score", ascending=False).iloc[0]
        result = _build_result(best, match_type="exact_name_spec")
        if result:
            return result

    # ---- Pass 2: Exact name, any spec ----
    if not candidates.empty:
        # Prefer rows that have Est Harga 2025
        has_est = candidates[candidates["est_harga_2025_parsed"].notna()]
        pool = has_est if not has_est.empty else candidates
        best = pool.iloc[0]
        result = _build_result(best, match_type="exact_name")
        if result:
            return result

    # ---- Pass 3: Category fallback ----
    if kategori_norm:
        kat_mask = shbj_df["Kategori"].apply(_normalize_name) == kategori_norm
        kat_candidates = shbj_df[kat_mask & shbj_df["est_harga_2025_parsed"].notna()]
        if not kat_candidates.empty:
            best = kat_candidates.iloc[0]
            result = _build_result(best, match_type="category_fallback")
            if result:
                return result

    return None


def _build_result(row: pd.Series, match_type: str) -> Optional[Dict[str, Any]]:
    """Build a clean result dict from a SHBJ row."""
    harga_shbj = row.get("harga_satuan_parsed")
    est_2025 = row.get("est_harga_2025_parsed")

    # Need at least one price to be useful
    if harga_shbj is None and est_2025 is None:
        return None

    return {
        "match_type": match_type,
        "shbj_id": row.get("ID", ""),
        "shbj_nama": row.get("Nama Barang", ""),
        "shbj_spesifikasi": row.get("Spesifikasi", ""),
        "shbj_satuan": row.get("Satuan", ""),
        "shbj_kategori": row.get("Kategori", ""),
        "harga_satuan_shbj": harga_shbj,         # SHBJ reference price
        "est_harga_2025": est_2025,               # Estimated 2025 price
        "keterangan": row.get("Keterangan", ""),
    }


# -----------------------------------------------------------------
# Coverage stats
# -----------------------------------------------------------------

def compute_coverage(proc_df: pd.DataFrame, shbj_df: pd.DataFrame) -> Dict[str, Any]:
    """Compute what % of proc items can be matched to SHBJ 2025.
    
    Fast approach: just check name matching, no full spec resolution.
    """
    if proc_df.empty or shbj_df.empty:
        return {"matched": 0, "total": 0, "pct": 0.0}

    # Determine name column
    if "Nama Barang dan Spesifikasi" in proc_df.columns:
        col = "Nama Barang dan Spesifikasi"
    elif "nama_barang" in proc_df.columns:
        col = "nama_barang"
    else:
        return {"matched": 0, "total": 0, "pct": 0.0}

    shbj_names = set(shbj_df["nama_norm"].tolist())
    total = 0
    matched = 0

    for raw in proc_df[col].dropna():
        name = str(raw).split("Spesifikasi:")[0].strip()
        norm = _normalize_name(name)
        total += 1
        if norm in shbj_names:
            matched += 1

    pct = round((matched / total) * 100, 1) if total > 0 else 0.0
    return {"matched": matched, "total": total, "pct": pct}


# -----------------------------------------------------------------
# Potential Savings scan
# -----------------------------------------------------------------

def compute_potential_savings(proc_df: "pd.DataFrame", shbj_df: "pd.DataFrame") -> "Dict[str, Any]":
    """Compute potential budget savings by comparing procurement prices to SHBJ 2025.

    For each item where harga_pengadaan > harga_shbj_2025, the positive delta
    is counted as potential savings.  Items with no SHBJ match or invalid prices
    are skipped silently.

    Returns:
        {
            "total_savings": float,      # sum of over-budget deltas (Rp)
            "items_over_budget": int,    # count of over-budget items
            "total_budget": float,       # sum of all valid procurement prices
            "items_checked": int,        # total items with a valid price
        }
    """
    if proc_df.empty or shbj_df.empty:
        return {"total_savings": 0.0, "items_over_budget": 0,
                "total_budget": 0.0, "items_checked": 0}

    # Determine columns
    if "Nama Barang dan Spesifikasi" in proc_df.columns:
        nama_col  = "Nama Barang dan Spesifikasi"
        harga_col = "Harga Satuan"
        sat_col   = "Satuan"
        kat_col   = "Kategori"
    elif "nama_barang" in proc_df.columns:
        nama_col  = "nama_barang"
        harga_col = "harga_satuan"
        sat_col   = "satuan"
        kat_col   = "kategori"
    else:
        return {"total_savings": 0.0, "items_over_budget": 0,
                "total_budget": 0.0, "items_checked": 0}

    if nama_col not in proc_df.columns or harga_col not in proc_df.columns:
        return {"total_savings": 0.0, "items_over_budget": 0,
                "total_budget": 0.0, "items_checked": 0}

    total_savings    = 0.0
    total_budget     = 0.0
    items_over_budget = 0
    items_checked    = 0

    for _, row in proc_df.iterrows():
        raw_name = str(row.get(nama_col, ""))
        if not raw_name or raw_name in ("nan", ""):
            continue

        # Parse harga pengadaan
        harga_numeric = _parse_rp(str(row.get(harga_col, "")))
        if harga_numeric is None or harga_numeric <= 0:
            continue

        total_budget += harga_numeric
        items_checked += 1

        sat = str(row.get(sat_col, "")) if sat_col in proc_df.columns else ""
        kat = str(row.get(kat_col, "")) if kat_col in proc_df.columns else ""

        # Find SHBJ 2025 match (spec left empty for speed)
        match = find_shbj_match(
            item_name=raw_name,
            item_spec="",
            item_satuan=sat,
            item_kategori=kat,
            shbj_df=shbj_df,
        )
        if match is None:
            continue

        harga_shbj = match.get("est_harga_2025") or match.get("harga_satuan_shbj")
        if harga_shbj is None or harga_shbj <= 0:
            continue

        if harga_numeric > harga_shbj:
            total_savings    += harga_numeric - harga_shbj
            items_over_budget += 1

    return {
        "total_savings":     total_savings,
        "items_over_budget": items_over_budget,
        "total_budget":      total_budget,
        "items_checked":     items_checked,
    }

