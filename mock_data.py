"""
mock_data.py — Centralized mock data for SIPVAL demo.
Provides vendor registry, budget history, price trends, and transaction data.
All data is deterministic (hash-based) so demos are reproducible.
"""

import hashlib
import pandas as pd
from typing import Dict, Any, List, Optional


# ============================================================
# Mock Vendor Registry
# ============================================================

MOCK_VENDORS = [
    {
        "nama": "PT Sumber Jaya Abadi",
        "lokasi": "Jakarta Pusat",
        "npwp": "01.234.567.8-001.000",
        "kontak": "021-3456789",
        "email": "procurement@sumberjaya.co.id",
        "kategori": "Suku Cadang & Alat Angkutan",
        "status": "Aktif",
        "reliability": 92,
    },
    {
        "nama": "CV Mitra Teknik Sejahtera",
        "lokasi": "Bandung",
        "npwp": "02.345.678.9-423.000",
        "kontak": "022-7891234",
        "email": "sales@mitratek.co.id",
        "kategori": "Peralatan & Mesin",
        "status": "Aktif",
        "reliability": 87,
    },
    {
        "nama": "PT Indo Baja Utama",
        "lokasi": "Surabaya",
        "npwp": "03.456.789.0-615.000",
        "kontak": "031-5678901",
        "email": "info@indobaja.com",
        "kategori": "Material & Konstruksi",
        "status": "Aktif",
        "reliability": 95,
    },
    {
        "nama": "PT Karya Mandiri Perkasa",
        "lokasi": "Jakarta Selatan",
        "npwp": "04.567.890.1-002.000",
        "kontak": "021-7890123",
        "email": "order@karyamandiri.co.id",
        "kategori": "Alat Kebersihan & Lingkungan",
        "status": "Aktif",
        "reliability": 89,
    },
    {
        "nama": "CV Tekno Supply Indonesia",
        "lokasi": "Tangerang",
        "npwp": "05.678.901.2-513.000",
        "kontak": "021-5551234",
        "email": "cs@teknosupply.id",
        "kategori": "Perlengkapan Kantor",
        "status": "Aktif",
        "reliability": 84,
    },
    {
        "nama": "PT Bumi Perkasa Jaya",
        "lokasi": "Bekasi",
        "npwp": "06.789.012.3-431.000",
        "kontak": "021-8901234",
        "email": "procurement@bumiperkasa.co.id",
        "kategori": "Suku Cadang & Alat Angkutan",
        "status": "Aktif",
        "reliability": 91,
    },
    {
        "nama": "UD Makmur Sentosa",
        "lokasi": "Semarang",
        "npwp": "07.890.123.4-503.000",
        "kontak": "024-6789012",
        "email": "admin@makmursentosa.com",
        "kategori": "Umum",
        "status": "Aktif",
        "reliability": 78,
    },
]


def _stable_hash(text: str, seed: int = 0) -> int:
    """Deterministic hash for consistent mock data generation."""
    raw = f"{text}::{seed}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def get_vendor_for_item(item_name: str) -> Dict[str, Any]:
    """Assign a deterministic mock vendor to an item."""
    idx = _stable_hash(item_name) % len(MOCK_VENDORS)
    return MOCK_VENDORS[idx].copy()


def get_budget_history(
    item_name: str,
    harga_2025: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Generate realistic 2024 vs 2025 budget history for an item.
    
    2024 price = 88-96% of 2025 price (simulating annual increase).
    """
    if harga_2025 is None or pd.isna(harga_2025):
        harga_2025 = float(_stable_hash(item_name, seed=99) % 4_000_000 + 200_000)

    harga_2025 = float(harga_2025)

    # Deterministic inflation factor per item (4-12% year-over-year)
    factor_seed = _stable_hash(item_name, seed=42)
    inflation_pct = 4.0 + (factor_seed % 80) / 10.0  # 4.0% – 12.0%
    harga_2024 = round(harga_2025 / (1 + inflation_pct / 100), 0)

    # Even older: 2023
    factor_seed_23 = _stable_hash(item_name, seed=23)
    inflation_23 = 3.0 + (factor_seed_23 % 90) / 10.0
    harga_2023 = round(harga_2024 / (1 + inflation_23 / 100), 0)

    return [
        {
            "tahun": 2023,
            "harga_satuan": harga_2023,
            "sumber": "SHBJ DKI Jakarta",
            "keterangan": "Anggaran APBD TA 2023",
        },
        {
            "tahun": 2024,
            "harga_satuan": harga_2024,
            "sumber": "SHBJ DKI Jakarta",
            "keterangan": "Anggaran APBD TA 2024",
        },
        {
            "tahun": 2025,
            "harga_satuan": harga_2025,
            "sumber": "SHBJ DKI Jakarta",
            "keterangan": "Anggaran APBD TA 2025 (Aktif)",
        },
    ]


def get_price_trend_df(item_name: str, harga_2025: Optional[float] = None) -> pd.DataFrame:
    """Return a DataFrame with 3-year price trend for charting."""
    history = get_budget_history(item_name, harga_2025)
    return pd.DataFrame(history)


def get_vendor_transactions(vendor_name: str, items_df: pd.DataFrame = None) -> List[Dict[str, Any]]:
    """Generate mock transaction history for a vendor.
    
    Creates 3-6 historical transactions per vendor.
    """
    transactions = []
    seed_base = _stable_hash(vendor_name, seed=77)
    n_transactions = 3 + (seed_base % 4)  # 3-6 transactions

    sample_items = [
        "Ban Tubeless 265/60 R18", "Bak Kontainer Sampah 10 m3",
        "Mesin Potong Plat Bevel", "Ban Gerobak Motor 4.00-8",
        "Pompa Air Submersible", "Kompresor Angin 2HP",
        "Selang Pemadam 2.5 inch", "Genset Portable 5000W",
        "Aki Kering 12V 70Ah", "Filter Oli Hydraulic",
    ]

    for i in range(n_transactions):
        h = _stable_hash(f"{vendor_name}_{i}", seed=88)
        item_idx = h % len(sample_items)
        year = 2023 + (h % 3)  # 2023-2025
        price = (h % 4_500_000) + 150_000

        transactions.append({
            "tahun": year,
            "nama_barang": sample_items[item_idx],
            "harga_satuan": price,
            "satuan": "unit" if h % 3 == 0 else ("pcs" if h % 3 == 1 else "set"),
            "jumlah": 1 + (h % 20),
            "total_nilai": price * (1 + (h % 20)),
            "status_kontrak": "Selesai" if year < 2025 else "Aktif",
            "lokasi": ["Jakarta", "Bandung", "Surabaya", "Semarang", "Tangerang"][h % 5],
        })

    transactions.sort(key=lambda x: x["tahun"], reverse=True)
    return transactions


def get_vendor_summary(result_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Build vendor summary cards from validation results.
    
    Enriches vendor names from result_df with full mock vendor details.
    """
    if result_df.empty or "vendor" not in result_df.columns:
        return []

    summaries = []
    vendor_groups = result_df.groupby("vendor")

    for vendor_name, group in vendor_groups:
        # Try to find matching mock vendor
        vendor_info = None
        for v in MOCK_VENDORS:
            if v["nama"].lower() in str(vendor_name).lower() or str(vendor_name).lower() in v["nama"].lower():
                vendor_info = v.copy()
                break

        if vendor_info is None:
            vendor_info = get_vendor_for_item(str(vendor_name))
            vendor_info["nama"] = str(vendor_name)

        vendor_info["items_supplied"] = len(group)
        vendor_info["total_nilai"] = group["comparison_price"].sum() if "comparison_price" in group.columns else 0

        # Determine statuses
        if "status" in group.columns:
            vendor_info["valid_count"] = len(group[group["status"].isin(["MATCH", "VALID"])])
            vendor_info["partial_count"] = len(group[group["status"] == "PARTIAL_MATCH"])
            vendor_info["invalid_count"] = len(group[~group["status"].isin(["MATCH", "VALID", "PARTIAL_MATCH"])])
        else:
            vendor_info["valid_count"] = 0
            vendor_info["partial_count"] = 0
            vendor_info["invalid_count"] = 0

        summaries.append(vendor_info)

    summaries.sort(key=lambda x: x["items_supplied"], reverse=True)
    return summaries


def format_currency(value: float) -> str:
    """Format a number as Indonesian Rupiah."""
    try:
        val = float(value)
        if val >= 1_000_000_000:
            return f"Rp {val / 1_000_000_000:,.1f} M"
        elif val >= 1_000_000:
            return f"Rp {val / 1_000_000:,.1f} Jt"
        elif val >= 1_000:
            return f"Rp {val:,.0f}"
        else:
            return f"Rp {val:,.0f}"
    except (ValueError, TypeError):
        return "N/A"


def format_currency_full(value: float) -> str:
    """Format as full Rupiah string without abbreviation."""
    try:
        return f"Rp {float(value):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "N/A"
