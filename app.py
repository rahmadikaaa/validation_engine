# app.py
"""SIPVAL — Sistem Validasi Pengadaan (AI-Assisted Procurement Validation Dashboard).

Enterprise-grade Streamlit dashboard for procurement item validation.
Features:
- Auto-load SHBJ data on startup
- Upload procurement items (CSV or Excel) as fallback
- AI-powered validation with reasoning engine
- Budget history 2024-2025
- Vendor history & analytics
- DOCX justification export

Backend logic (cognition/) is NOT modified — this file only handles UI/UX.
"""

import os
import streamlit as st
import pandas as pd
from typing import List, Dict, Any

# Backend imports (UNCHANGED)
from cognition.reasoning_engine import run_reasoning
from cognition.candidate_generator import generate_placeholder_candidates

# UI imports
from ui_styles import inject_enterprise_css
from ui_components import (
    render_status_badge,
    render_status_text,
    render_kpi_card,
    render_score_bar,
    render_page_header,
    render_reasoning_cards,
    render_candidate_card,
    render_vendor_card,
    render_info_card,
    render_system_status,
    generate_justification_text,
    generate_justification_docx,
    # Drawer helpers
    render_spec_grid,
    render_validation_checklist,
    render_candidate_comparison_table,
    render_procurement_reasoning_block,
    render_deviation_warning,
    _calc_deviation,
)
from mock_data import (
    get_vendor_for_item,
    get_budget_history,
    get_price_trend_df,
    get_vendor_transactions,
    get_vendor_summary,
    format_currency,
    format_currency_full,
    MOCK_VENDORS,
)
from shbj_loader import (
    load_shbj_data,
    find_shbj_match,
    compute_coverage,
    compute_potential_savings,
)


# ============================================================
# Page Config
# ============================================================

st.set_page_config(
    page_title="SIPVAL — Sistem Validasi Pengadaan",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject enterprise CSS
inject_enterprise_css()


# ============================================================
# Session State Init
# ============================================================

if "proc_df" not in st.session_state:
    st.session_state.proc_df = pd.DataFrame()
if "result_df" not in st.session_state:
    st.session_state.result_df = pd.DataFrame()
if "validation_run" not in st.session_state:
    st.session_state.validation_run = False
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None
if "selected_item_name" not in st.session_state:
    st.session_state.selected_item_name = None
if "auto_loaded" not in st.session_state:
    st.session_state.auto_loaded = False
if "shbj_df" not in st.session_state:
    st.session_state.shbj_df = pd.DataFrame()
if "shbj_loaded" not in st.session_state:
    st.session_state.shbj_loaded = False
if "shbj_coverage" not in st.session_state:
    st.session_state.shbj_coverage = {"matched": 0, "total": 0, "pct": 0.0}
if "drawer_candidates" not in st.session_state:
    st.session_state.drawer_candidates = []
if "drawer_reasoning" not in st.session_state:
    st.session_state.drawer_reasoning = []
# Programmatic page navigation key
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "📊 Dashboard Overview"
# Procurement Items drawer state
if "selected_drawer_item" not in st.session_state:
    st.session_state.selected_drawer_item = None
if "drawer_item_action_status" not in st.session_state:
    st.session_state.drawer_item_action_status = {}
if "rejected_candidates" not in st.session_state:
    st.session_state.rejected_candidates = set()
if "selected_candidates" not in st.session_state:
    st.session_state.selected_candidates = set()
# Potential savings from SHBJ comparison
if "shbj_potential_savings" not in st.session_state:
    st.session_state.shbj_potential_savings = {"total_savings": 0.0, "items_over_budget": 0, "total_budget": 0.0, "items_checked": 0}
# Pending programmatic navigation (avoids modifying widget-bound key after render)
if "pending_nav" not in st.session_state:
    st.session_state.pending_nav = None
# Demo dataset flags
if "demo_dataset_loaded" not in st.session_state:
    st.session_state.demo_dataset_loaded = False
if "using_custom_dataset" not in st.session_state:
    st.session_state.using_custom_dataset = False


# ============================================================
# Data Loading Functions (Backend logic PRESERVED exactly)
# ============================================================

@st.cache_data(show_spinner=False)
def load_procurement_excel(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        df = pd.read_excel(uploaded_file)
        has_nama = "nama_barang" in df.columns or "Nama Barang dan Spesifikasi" in df.columns
        if not has_nama:
            uploaded_file.seek(0)
            df_scan = pd.read_excel(uploaded_file, header=None, nrows=10)
            target_cols = {"ID", "Kategori", "Sub kategori", "Nama Barang dan Spesifikasi"}
            header_idx = None
            for idx, row in df_scan.iterrows():
                row_vals = set(str(val).strip() for val in row.values if pd.notna(val))
                if target_cols.issubset(row_vals):
                    header_idx = idx
                    break
            if header_idx is not None:
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, header=header_idx)
        return df
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_csv_file(uploaded_file):
    df_raw = pd.read_csv(uploaded_file, header=None)
    uploaded_file.seek(0)
    df_direct = pd.read_csv(uploaded_file)
    normalized_cols = [str(c).strip().lower() for c in df_direct.columns]
    validation_cols = {"id_item", "nama_barang", "status", "vendor", "comparison_price"}
    if validation_cols.intersection(set(normalized_cols)):
        df_direct = df_direct.loc[:, ~df_direct.columns.astype(str).str.contains("^Unnamed")]
        return df_direct, "validation_results"
    header_keywords = ["NAMA SURVEYOR", "No Urut", "ID", "Kategori", "Sub kategori"]
    header_row_idx = None
    for idx, row in df_raw.head(10).iterrows():
        row_values = [str(v).strip() for v in row.values]
        matches = sum(1 for keyword in header_keywords if keyword in row_values)
        if matches >= 3:
            header_row_idx = idx
            break
    if header_row_idx is not None:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, header=header_row_idx)
        df = df.dropna(how="all")
        df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed")]
        return df, "procurement_source"
    return df_direct, "unknown_csv"


@st.cache_data(show_spinner=False)
def load_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame(), "unknown"
    filename = uploaded_file.name.lower()
    if filename.endswith(".csv"):
        df, file_type = load_csv_file(uploaded_file)
    elif filename.endswith((".xlsx", ".xls")):
        df, file_type = load_procurement_excel(uploaded_file), "procurement_source"
    else:
        raise ValueError("Format file tidak didukung")
    df = df.replace("None", pd.NA)
    df = df.dropna(axis=1, how="all")
    return df, file_type


@st.cache_data(show_spinner=False)
def load_default_excel(file_path: str) -> pd.DataFrame:
    """Load the default SHBJ Excel file from disk."""
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_excel(file_path)
        has_nama = "nama_barang" in df.columns or "Nama Barang dan Spesifikasi" in df.columns
        if not has_nama:
            df_scan = pd.read_excel(file_path, header=None, nrows=10)
            target_cols = {"ID", "Kategori", "Sub kategori", "Nama Barang dan Spesifikasi"}
            header_idx = None
            for idx, row in df_scan.iterrows():
                row_vals = set(str(val).strip() for val in row.values if pd.notna(val))
                if target_cols.issubset(row_vals):
                    header_idx = idx
                    break
            if header_idx is not None:
                df = pd.read_excel(file_path, header=header_idx)
        nama_col = "Nama Barang dan Spesifikasi" if "Nama Barang dan Spesifikasi" in df.columns else "nama_barang"
        if nama_col in df.columns:
            df = df.dropna(subset=[nama_col])
        df = df.replace("None", pd.NA)
        df = df.dropna(axis=1, how="all")
        return df
    except Exception as e:
        st.error(f"Gagal memuat data default: {e}")
        return pd.DataFrame()


# ============================================================
# Validation Logic (PRESERVED exactly from original)
# ============================================================

def run_validation_logic():
    proc_df = st.session_state.proc_df
    if proc_df.empty:
        st.warning("Data pengadaan kosong.")
        return

    has_nama = "nama_barang" in proc_df.columns or "Nama Barang dan Spesifikasi" in proc_df.columns
    if not has_nama:
        st.error("File pengadaan tidak memiliki kolom: 'nama_barang' atau 'Nama Barang dan Spesifikasi'")
        return

    results: List[Dict[str, Any]] = []

    for _, item_row in proc_df.iterrows():
        item_dict = item_row.to_dict()

        # Normalize mapping for reasoning_engine if using SHBJ format
        if "Nama Barang dan Spesifikasi" in item_dict and "nama_barang" not in item_dict:
            item_dict["nama_barang"] = item_dict["Nama Barang dan Spesifikasi"]
        if "Kategori" in item_dict and "kategori" not in item_dict:
            item_dict["kategori"] = item_dict["Kategori"]
        if "Sub kategori" in item_dict and "subkategori" not in item_dict:
            item_dict["subkategori"] = item_dict["Sub kategori"]
        if "Satuan" in item_dict and "satuan" not in item_dict:
            item_dict["satuan"] = item_dict["Satuan"]
        if "Harga Satuan" in item_dict and "harga_satuan" not in item_dict:
            item_dict["harga_satuan"] = item_dict["Harga Satuan"]

        # Split combined nama + spesifikasi
        raw_nama = str(item_dict.get("nama_barang", ""))
        if "Spesifikasi:" in raw_nama and not item_dict.get("spesifikasi"):
            parts = raw_nama.split("Spesifikasi:", 1)
            item_dict["nama_barang"] = parts[0].strip()
            item_dict["spesifikasi"] = parts[1].strip()

        best_match: Dict[str, Any] = {
            "candidate": None,
            "status": "NO_CANDIDATE",
            "score": 0.0,
            "reasoning": [],
            "deviation_notes": []
        }

        generated_candidates = generate_placeholder_candidates(item_dict)

        for cand_dict in generated_candidates:
            evaluation = run_reasoning(item_dict, cand_dict)
            cand_status = evaluation["candidate_evaluation"]["candidate_status"]
            score = evaluation["candidate_evaluation"]["match_score"]

            if score > best_match["score"]:
                best_match.update({
                    "candidate": cand_dict,
                    "status": cand_status,
                    "score": score,
                    "reasoning": evaluation["candidate_evaluation"]["reasoning"],
                    "deviation_notes": evaluation["candidate_evaluation"]["deviation_notes"]
                })

        cand = best_match["candidate"] or {}

        id_val = item_dict.get("id_item") or item_dict.get("ID")
        nama_val = item_dict.get("nama_barang")
        satuan_val = item_dict.get("satuan")
        harga_satuan_val = item_dict.get("harga_satuan") or item_dict.get("Harga Satuan")

        results.append({
            "id_item": id_val,
            "nama_barang": nama_val,
            "satuan": satuan_val,
            "harga_satuan": harga_satuan_val,
            "comparison_product": cand.get("nama_produk", "N/A"),
            "comparison_specification": cand.get("spesifikasi", "N/A"),
            "vendor": cand.get("vendor", "N/A"),
            "comparison_price": cand.get("harga", 0),
            "status": best_match["status"],
            "score": best_match["score"],
            "deviation_notes": ", ".join(best_match["deviation_notes"])
        })

    st.session_state.result_df = pd.DataFrame(results)
    st.session_state.validation_run = True


# ============================================================
# Auto-load Default Data
# ============================================================

DEMO_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample_procurement.csv")

@st.cache_data(show_spinner=False)
def load_demo_csv(file_path: str) -> pd.DataFrame:
    """Load the demo dataset from CSV using the same normalization as uploaded files."""
    try:
        df = pd.read_csv(file_path)
        # Apply same normalization as load_uploaded_file
        df = df.replace("None", pd.NA)
        df = df.dropna(axis=1, how="all")
        # Drop empty rows based on name column if present
        nama_col = "Nama Barang dan Spesifikasi" if "Nama Barang dan Spesifikasi" in df.columns else (
            "nama_barang" if "nama_barang" in df.columns else None
        )
        if nama_col:
            df = df.dropna(subset=[nama_col])
        return df
    except Exception as e:
        return pd.DataFrame()

if st.session_state.proc_df.empty and not st.session_state.demo_dataset_loaded:
    if os.path.exists(DEMO_CSV_PATH):
        demo_df = load_demo_csv(DEMO_CSV_PATH)
        if not demo_df.empty:
            st.session_state.proc_df = demo_df
            st.session_state.uploaded_file_name = "data/sample_procurement.csv (Demo)"
            st.session_state.demo_dataset_loaded = True
            st.session_state.using_custom_dataset = False
            st.session_state.auto_loaded = True
            
            # Automatically run validation logic for the demo dataset
            run_validation_logic()
    else:
        st.warning("Demo dataset not found. Please upload a procurement file manually.")

# Auto-load SHBJ 2025 reference data (runs once per session)
if not st.session_state.shbj_loaded:
    with st.spinner("⏳ Memuat data SHBJ 2025..."):
        shbj_df = load_shbj_data()
        st.session_state.shbj_df = shbj_df
        st.session_state.shbj_loaded = True
        if not shbj_df.empty and not st.session_state.proc_df.empty:
            st.session_state.shbj_coverage = compute_coverage(
                st.session_state.proc_df, shbj_df
            )
            st.session_state.shbj_potential_savings = compute_potential_savings(
                st.session_state.proc_df, shbj_df
            )


# ============================================================
# Sidebar
# ============================================================

# Apply pending navigation BEFORE the radio widget is instantiated
if st.session_state.pending_nav is not None:
    st.session_state.nav_page = st.session_state.pending_nav
    st.session_state.pending_nav = None

with st.sidebar:
    st.markdown("""
    <div style="padding: 16px 0 8px 0;">
        <div style="font-size: 1.3rem; font-weight: 700; background: linear-gradient(135deg, #14B8A6, #FBBF24); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            🛡️ SIPVAL
        </div>
        <div style="color: #94A3B8; font-size: 0.72rem; margin-top: 2px; font-weight: 400;">
            Sistem Validasi Pengadaan v1.0
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    page = st.radio("Navigasi", [
        "📊 Dashboard Overview",
        "📝 Procurement Items",
        "🔍 Item Detail",
        "🏢 Vendor History",
        "📈 Validation Results",
    ], label_visibility="collapsed", key="nav_page")

    st.markdown("---")

    # System status
    st.markdown(render_system_status(), unsafe_allow_html=True)

    st.markdown("---")

    # File info
    if st.session_state.uploaded_file_name:
        st.markdown(f"""
        <div style="padding: 4px 0;">
            <div style="color: #94A3B8; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">Data Aktif</div>
            <div style="color: #CBD5E1; font-size: 0.8rem;">📄 {st.session_state.uploaded_file_name}</div>
            <div style="color: #64748B; font-size: 0.72rem; margin-top: 2px;">{len(st.session_state.proc_df)} item dimuat</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="color: #475569; font-size: 0.68rem; text-align: center; padding: 4px 0;">
        Demo MVP — JuaraVibeCoding<br>
        Bukan website resmi pemerintah
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# Dataset Indicator
# ============================================================

if st.session_state.using_custom_dataset:
    st.info("📄 Custom Dataset Loaded")
elif st.session_state.demo_dataset_loaded:
    st.info("🚀 Demo Dataset Loaded — using data/sample_procurement.csv")


# ============================================================
# Optional File Upload (Fallback)
# ============================================================

# Only show file uploader in an expander to keep the UI clean
with st.expander("📂 Upload Data Baru (Opsional)", expanded=False):
    proc_file = st.file_uploader(
        "Upload **Procurement Items (Excel)** atau **Validation Results (CSV)**",
        type=["csv", "xlsx", "xls"],
        key="file_upload_main",
    )
    if proc_file is not None:
        if st.session_state.uploaded_file_name != proc_file.name:
            try:
                df, file_type = load_uploaded_file(proc_file)
                if file_type == "validation_results":
                    if "Unnamed: 0" in df.columns:
                        df = df.drop(columns=["Unnamed: 0"])
                    st.session_state.result_df = df
                    st.session_state.proc_df = df
                    st.session_state.validation_run = True
                    st.session_state.uploaded_file_name = proc_file.name
                    st.session_state.using_custom_dataset = True
                    st.session_state.demo_dataset_loaded = False
                else:
                    nama_col = "Nama Barang dan Spesifikasi" if "Nama Barang dan Spesifikasi" in df.columns else "nama_barang"
                    if nama_col in df.columns:
                        df = df.dropna(subset=[nama_col])
                    st.session_state.proc_df = df
                    st.session_state.result_df = pd.DataFrame()
                    st.session_state.validation_run = False
                    st.session_state.uploaded_file_name = proc_file.name
                    st.session_state.using_custom_dataset = True
                    st.session_state.demo_dataset_loaded = False
                st.success(f"✅ File **{proc_file.name}** berhasil dimuat!")
            except Exception as e:
                st.error(f"Gagal memuat file: {e}")


# ============================================================
# Helper Functions
# ============================================================

def get_nama_col(df: pd.DataFrame) -> str:
    """Get the item name column from the DataFrame."""
    if "Nama Barang dan Spesifikasi" in df.columns:
        return "Nama Barang dan Spesifikasi"
    return "nama_barang"


def calc_deviation_pct(harga_ref, harga_comp) -> str:
    """Calculate price deviation percentage."""
    try:
        ref = float(harga_ref)
        comp = float(harga_comp)
        if ref > 0:
            return f"{((comp - ref) / ref) * 100:+.1f}%"
    except (ValueError, TypeError):
        pass
    return "N/A"


# ============================================================
# PAGE: Dashboard Overview
# ============================================================

if page == "📊 Dashboard Overview":
    render_page_header("📊", "Dashboard Overview", "Ringkasan status validasi pengadaan")

    total_items = len(st.session_state.proc_df)

    if st.session_state.validation_run and not st.session_state.result_df.empty and 'status' in st.session_state.result_df.columns:
        res_df = st.session_state.result_df

        valid_count = len(res_df[res_df['status'].isin(['MATCH', 'VALID'])])
        partial_count = len(res_df[res_df['status'] == 'PARTIAL_MATCH'])
        invalid_count = len(res_df[~res_df['status'].isin(['MATCH', 'VALID', 'PARTIAL_MATCH'])])
        avg_score = res_df['score'].mean() if 'score' in res_df.columns else 0.0
        total_vendors = res_df['vendor'].nunique() if 'vendor' in res_df.columns else 0

        # Calculate average deviation
        avg_dev = "N/A"
        if 'harga_satuan' in res_df.columns and 'comparison_price' in res_df.columns:
            try:
                valid_prices = res_df.dropna(subset=['harga_satuan', 'comparison_price'])
                if not valid_prices.empty:
                    ref_prices = pd.to_numeric(valid_prices['harga_satuan'], errors='coerce')
                    comp_prices = pd.to_numeric(valid_prices['comparison_price'], errors='coerce')
                    mask = ref_prices > 0
                    if mask.any():
                        deviations = ((comp_prices[mask] - ref_prices[mask]) / ref_prices[mask]) * 100
                        avg_dev = f"{deviations.mean():+.1f}%"
            except Exception:
                pass

        # KPI Row 1
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(render_kpi_card("📦", "Total Item", str(total_items), "dari data pengadaan", "teal"), unsafe_allow_html=True)
        with c2:
            st.markdown(render_kpi_card("✅", "Valid", str(valid_count), f"{valid_count/max(total_items,1)*100:.0f}% item valid", "green"), unsafe_allow_html=True)
        with c3:
            st.markdown(render_kpi_card("⚠️", "Partial Match", str(partial_count), "perlu review minor", "amber"), unsafe_allow_html=True)

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

        # KPI Row 2
        c4, c5, c6, c7, c8 = st.columns(5)
        with c4:
            st.markdown(render_kpi_card("❌", "Invalid", str(invalid_count), "perlu review manual", "red"), unsafe_allow_html=True)
        with c5:
            st.markdown(render_kpi_card("📊", "Rata-rata Skor", f"{avg_score:.0%}", "confidence AI", "teal"), unsafe_allow_html=True)
        with c6:
            st.markdown(render_kpi_card("🏢", "Total Vendor", str(total_vendors), f"avg deviasi: {avg_dev}", "gold"), unsafe_allow_html=True)
        with c7:
            cov = st.session_state.shbj_coverage
            cov_pct = cov.get("pct", 0)
            cov_matched = cov.get("matched", 0)
            cov_total = cov.get("total", total_items)
            st.markdown(render_kpi_card(
                "📚", "Histori SHBJ 2025",
                f"{cov_pct:.0f}%",
                f"{cov_matched} dari {cov_total} item cocok",
                "teal"
            ), unsafe_allow_html=True)
        with c8:
            sav = st.session_state.shbj_potential_savings
            sav_total = sav.get("total_savings", 0)
            sav_items = sav.get("items_over_budget", 0)
            st.markdown(render_kpi_card(
                "💰", "Potensi Penghematan",
                format_currency(sav_total) if sav_total > 0 else "—",
                f"{sav_items} item over-budget" if sav_items > 0 else "hitung setelah validasi",
                "gold"
            ), unsafe_allow_html=True)

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

        # Savings Banner
        sav = st.session_state.shbj_potential_savings
        sav_total = sav.get("total_savings", 0)
        sav_items = sav.get("items_over_budget", 0)
        sav_checked = sav.get("items_checked", 0)
        if sav_total > 0:
            st.markdown(f"""
            <div class="savings-banner">
                <div class="sb-icon">💰</div>
                <div class="sb-block">
                    <div class="sb-label">Potensi Penghematan</div>
                    <div class="sb-value">{format_currency(sav_total)}</div>
                    <div class="sb-sub">{sav_items} item teridentifikasi over-budget</div>
                </div>
                <div class="sb-divider"></div>
                <div class="sb-block">
                    <div class="sb-label">Item Diperiksa</div>
                    <div class="sb-value" style="font-size:1.1rem;color:var(--teal-400);">{sav_checked}</div>
                    <div class="sb-sub">dibandingkan ke SHBJ 2025</div>
                </div>
                <div class="sb-divider"></div>
                <div class="sb-message">
                    <strong>SIPVAL bukan hanya memvalidasi harga</strong> — sistem juga mengidentifikasi
                    potensi penghematan anggaran dengan membandingkan harga pengadaan
                    terhadap referensi SHBJ DKI Jakarta 2025.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

        # Validation Distribution Chart
        st.subheader("Distribusi Status Validasi")

        chart_data = pd.DataFrame({
            "Status": ["Valid", "Partial Match", "Invalid"],
            "Jumlah": [valid_count, partial_count, invalid_count],
        })
        chart_data = chart_data.set_index("Status")
        st.bar_chart(chart_data, color="#0D9488")

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

        # Quick summary
        st.success(f"✅ Validasi selesai — {valid_count} item valid, {partial_count} perlu review, {invalid_count} invalid dari {total_items} total item.")

    else:
        # Pre-validation state
        cov = st.session_state.shbj_coverage
        cov_pct = cov.get("pct", 0)
        cov_matched = cov.get("matched", 0)
        cov_total = cov.get("total", total_items)
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(render_kpi_card("📦", "Total Item", str(total_items), "dari data pengadaan", "teal"), unsafe_allow_html=True)
        with c2:
            st.markdown(render_kpi_card("⏳", "Status Validasi", "Belum", "jalankan validasi", "amber"), unsafe_allow_html=True)
        with c3:
            st.markdown(render_kpi_card("🤖", "AI Engine", "Ready", "reasoning engine aktif", "green"), unsafe_allow_html=True)
        with c4:
            st.markdown(render_kpi_card(
                "📚", "Histori SHBJ 2025",
                f"{cov_pct:.0f}%",
                f"{cov_matched} dari {cov_total} item cocok",
                "teal"
            ), unsafe_allow_html=True)
        with c5:
            sav = st.session_state.shbj_potential_savings
            sav_total = sav.get("total_savings", 0)
            sav_items = sav.get("items_over_budget", 0)
            st.markdown(render_kpi_card(
                "💰", "Potensi Penghematan",
                format_currency(sav_total) if sav_total > 0 else "—",
                f"{sav_items} item over-budget" if sav_items > 0 else "hitung setelah validasi",
                "gold"
            ), unsafe_allow_html=True)

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

        # Savings Banner (pre-validation)
        sav = st.session_state.shbj_potential_savings
        sav_total = sav.get("total_savings", 0)
        sav_items = sav.get("items_over_budget", 0)
        sav_checked = sav.get("items_checked", 0)
        if sav_total > 0:
            st.markdown(f"""
            <div class="savings-banner">
                <div class="sb-icon">💰</div>
                <div class="sb-block">
                    <div class="sb-label">Potensi Penghematan</div>
                    <div class="sb-value">{format_currency(sav_total)}</div>
                    <div class="sb-sub">{sav_items} item teridentifikasi over-budget</div>
                </div>
                <div class="sb-divider"></div>
                <div class="sb-block">
                    <div class="sb-label">Item Diperiksa</div>
                    <div class="sb-value" style="font-size:1.1rem;color:var(--teal-400);">{sav_checked}</div>
                    <div class="sb-sub">dibandingkan ke SHBJ 2025</div>
                </div>
                <div class="sb-divider"></div>
                <div class="sb-message">
                    <strong>SIPVAL bukan hanya memvalidasi harga</strong> — sistem juga mengidentifikasi
                    potensi penghematan anggaran dengan membandingkan harga pengadaan
                    terhadap referensi SHBJ DKI Jakarta 2025.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

        if total_items > 0:
            st.info(f"📋 **{total_items} item** pengadaan dimuat. Klik tombol di bawah untuk menjalankan validasi AI.")
            if st.button("🚀 Jalankan Validasi AI", type="primary", key="dash_run_btn", use_container_width=True):
                with st.spinner("⏳ Menjalankan validasi AI... Mohon tunggu."):
                    run_validation_logic()
                st.rerun()
        else:
            st.info("📂 Tidak ada data. Upload file pengadaan untuk memulai.")

    # Preview data
    if not st.session_state.proc_df.empty:
        with st.expander("👀 Preview Data Pengadaan", expanded=False):
            st.dataframe(st.session_state.proc_df.head(10), use_container_width=True)



# ============================================================
# PAGE: Procurement Items
# ============================================================

elif page == "📝 Procurement Items":
    render_page_header("📝", "Procurement Items", "Registry item pengadaan — pilih item untuk melihat analisis lengkap")

    if st.session_state.proc_df.empty:
        st.info("📂 Tidak ada data. Upload file pengadaan untuk melihat item.")
    else:
        proc_df = st.session_state.proc_df
        nama_col = get_nama_col(proc_df)
        total = len(proc_df)

        # ── Summary Metrics ──────────────────────────────
        if st.session_state.validation_run and not st.session_state.result_df.empty:
            res_df = st.session_state.result_df
            valid_n   = len(res_df[res_df['status'].isin(['MATCH', 'VALID'])]) if 'status' in res_df.columns else 0
            partial_n = len(res_df[res_df['status'] == 'PARTIAL_MATCH']) if 'status' in res_df.columns else 0
            invalid_n = len(res_df[~res_df['status'].isin(['MATCH', 'VALID', 'PARTIAL_MATCH'])]) if 'status' in res_df.columns else 0
            avg_score = res_df['score'].mean() if 'score' in res_df.columns else 0.0
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("📦 Total Item", total)
            c2.metric("✅ Valid", valid_n)
            c3.metric("⚠️ Partial", partial_n)
            c4.metric("❌ Need Review", invalid_n)
            c5.metric("📊 Avg Confidence", f"{avg_score:.0%}")
        else:
            c1, c2 = st.columns([1, 3])
            c1.metric("📦 Total Item", total)
            with c2:
                st.info("Validasi AI belum dijalankan untuk data ini.")
                if st.button("🚀 Jalankan Validasi AI", type="primary", key="proc_run_btn"):
                    with st.spinner("⏳ Menjalankan validasi AI..."):
                        run_validation_logic()
                    st.rerun()

        st.divider()

        # ── Filters ─────────────────────────────────────────
        col_s, col_f1, col_f2 = st.columns([3, 1, 1])
        with col_s:
            search_query = st.text_input("🔍", placeholder="Cari berdasarkan nama item...", label_visibility="collapsed")
        with col_f1:
            status_opts = ["Semua Status"]
            if st.session_state.validation_run and not st.session_state.result_df.empty and 'status' in st.session_state.result_df.columns:
                status_opts += sorted(st.session_state.result_df['status'].dropna().unique().tolist())
            status_filter = st.selectbox("Filter Status", status_opts, label_visibility="collapsed")
        with col_f2:
            cat_col = "Kategori" if "Kategori" in proc_df.columns else ("kategori" if "kategori" in proc_df.columns else None)
            cat_opts = ["Semua Kategori"]
            if cat_col:
                cat_opts += sorted(proc_df[cat_col].dropna().astype(str).unique().tolist())
            cat_filter = st.selectbox("Filter Kategori", cat_opts, label_visibility="collapsed")

        # ── Build result lookup ────────────────────────────
        result_lookup: dict = {}
        if st.session_state.validation_run and not st.session_state.result_df.empty:
            for _, rrow in st.session_state.result_df.iterrows():
                result_lookup[str(rrow.get('nama_barang', ''))] = rrow.to_dict()

        # ── Apply filters ────────────────────────────────
        df_filtered = proc_df.copy()
        if search_query and nama_col in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered[nama_col].astype(str).str.contains(search_query, case=False, na=False)
            ]
        if status_filter != "Semua Status" and st.session_state.validation_run and 'status' in st.session_state.result_df.columns:
            valid_names = st.session_state.result_df[
                st.session_state.result_df['status'] == status_filter
            ]['nama_barang'].tolist()
            df_filtered = df_filtered[df_filtered[nama_col].isin(valid_names)]
        if cat_filter != "Semua Kategori" and cat_col and cat_col in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[cat_col].astype(str) == cat_filter]

        # ── Build display table ────────────────────────────
        tbl_rows = []
        full_names = []
        for _, item_row in df_filtered.iterrows():
            d = item_row.to_dict()
            name = str(d.get(nama_col, ""))
            res  = result_lookup.get(name, {})
            score = res.get('score')
            full_names.append(name)
            tbl_rows.append({
                "ID":           str(d.get("ID") or d.get("id_item") or "")[:15],
                "Item Name":    name[:80],
                "Category":     str(d.get("Kategori") or d.get("kategori") or "")[:30],
                "Ref. Price":   format_currency_full(d.get("Harga Satuan") or d.get("harga_satuan") or 0),
                "Status":       res.get("status", "Belum Divalidasi"),
                "Confidence":   f"{round(float(score)*100)}%" if score is not None else "—",
            })

        tbl_df = pd.DataFrame(tbl_rows) if tbl_rows else pd.DataFrame(
            columns=["ID", "Item Name", "Category", "Ref. Price", "Status", "Confidence"]
        )

        st.caption(f"Menampilkan **{len(tbl_df)}** dari **{total}** item")
        st.dataframe(
            tbl_df,
            use_container_width=True,
            hide_index=True,
            height=min(500, max(150, len(tbl_df) * 35 + 45)),
            column_config={
                "ID":           st.column_config.TextColumn("ID",            width="small"),
                "Item Name":    st.column_config.TextColumn("Item Name",     width="large"),
                "Category":     st.column_config.TextColumn("Category",      width="medium"),
                "Ref. Price":   st.column_config.TextColumn("Ref. Price",    width="medium"),
                "Status":       st.column_config.TextColumn("Status",        width="medium"),
                "Confidence":   st.column_config.TextColumn("Confidence",    width="small"),
            },
        )

        st.divider()

        # ── Item Selector & Navigation ─────────────────────
        st.markdown("##### Pilih item untuk melihat analisis detail")
        col_sel, col_btn = st.columns([5, 1])
        with col_sel:
            default_idx = 0
            if st.session_state.selected_item_name and st.session_state.selected_item_name in full_names:
                default_idx = full_names.index(st.session_state.selected_item_name)
            if full_names:
                selected_proc_name = st.selectbox(
                    "Item",
                    full_names,
                    index=default_idx,
                    label_visibility="collapsed",
                    key="proc_item_select",
                )
            else:
                st.info("Tidak ada item sesuai filter.")
                selected_proc_name = None
        with col_btn:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("👁 View Detail", type="primary", key="proc_view_btn",
                         use_container_width=True, disabled=(not full_names)):
                if selected_proc_name:
                    st.session_state.selected_item_name = selected_proc_name
                    st.session_state.pending_nav = "🔍 Item Detail"
                    st.rerun()


    if st.session_state.proc_df.empty:
        st.info("📂 Tidak ada data. Upload file pengadaan untuk melihat item.")
    else:
        proc_df = st.session_state.proc_df
        nama_col = get_nama_col(proc_df)
        total = len(proc_df)

        # ── Summary KPIs ──────────────────────────────────────
        if st.session_state.validation_run and not st.session_state.result_df.empty:
            res_df = st.session_state.result_df
            validated = len(res_df)
            valid_n = len(res_df[res_df['status'].isin(['MATCH', 'VALID'])]) if 'status' in res_df.columns else 0
            needs_review = len(res_df[~res_df['status'].isin(['MATCH', 'VALID'])]) if 'status' in res_df.columns else 0
            avg_score = res_df['score'].mean() if 'score' in res_df.columns else 0.0

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("📦 Total Item", total)
            c2.metric("✅ Valid", valid_n)
            c3.metric("⚠️ Perlu Review", needs_review)
            c4.metric("📊 Avg Confidence", f"{avg_score:.0%}")
            c5.metric("🔍 Sudah Divalidasi", validated)
        else:
            c1, c2 = st.columns([1, 3])
            with c1:
                st.metric("📦 Total Item", total)
            with c2:
                if st.button("🚀 Jalankan Validasi AI untuk Semua Item", type="primary", key="proc_run_btn", use_container_width=True):
                    with st.spinner("⏳ Menjalankan validasi AI..."):
                        run_validation_logic()
                    st.rerun()

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

        # ── Filters ───────────────────────────────────────────
        col_search, col_filter, col_sort = st.columns([2, 1, 1])
        with col_search:
            search_query = st.text_input("🔍 Cari item", placeholder="Ketik nama barang...", label_visibility="collapsed")
        with col_filter:
            status_filter = "Semua"
            if st.session_state.validation_run and not st.session_state.result_df.empty and 'status' in st.session_state.result_df.columns:
                statuses = ["Semua"] + list(st.session_state.result_df['status'].unique())
                status_filter = st.selectbox("Filter Status", statuses, label_visibility="collapsed")
        with col_sort:
            page_size = st.selectbox("Tampilkan", [10, 25, 50, 100], index=0, label_visibility="collapsed")

        # ── Build display list ─────────────────────────────────
        df_display = proc_df.copy()
        if search_query and nama_col in df_display.columns:
            df_display = df_display[df_display[nama_col].astype(str).str.contains(search_query, case=False, na=False)]
        if status_filter != "Semua" and st.session_state.validation_run and 'status' in st.session_state.result_df.columns:
            filtered_names = st.session_state.result_df[
                st.session_state.result_df['status'] == status_filter
            ]['nama_barang'].tolist()
            if nama_col in df_display.columns:
                df_display = df_display[df_display[nama_col].isin(filtered_names)]

        df_display = df_display.head(page_size)
        display_total = len(proc_df)
        st.caption(f"Menampilkan **{len(df_display)}** dari **{display_total}** item")

        # ── Build result lookup dict ───────────────────────────
        result_lookup: dict = {}
        if st.session_state.validation_run and not st.session_state.result_df.empty:
            for _, rrow in st.session_state.result_df.iterrows():
                result_lookup[str(rrow.get('nama_barang', ''))] = rrow.to_dict()

        # ── Table Header ──────────────────────────────────────
        st.markdown("""
        <div class="proc-table-header">
            <div class="proc-table-header-cell">ID</div>
            <div class="proc-table-header-cell">Item Name</div>
            <div class="proc-table-header-cell">Category</div>
            <div class="proc-table-header-cell">Reference Price</div>
            <div class="proc-table-header-cell">Status</div>
            <div class="proc-table-header-cell">Confidence</div>
            <div class="proc-table-header-cell">Action</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Table Rows ─────────────────────────────────────────
        active_drawer = st.session_state.selected_drawer_item

        for row_idx, (_, item_row) in enumerate(df_display.iterrows()):
            item_dict_row = item_row.to_dict()
            item_name = str(item_dict_row.get(nama_col, f"Item {row_idx+1}"))
            item_id   = str(item_dict_row.get("ID") or item_dict_row.get("id_item") or f"{row_idx+1}")
            item_kat  = str(item_dict_row.get("Kategori") or item_dict_row.get("kategori") or "—")
            item_harga = item_dict_row.get("Harga Satuan") or item_dict_row.get("harga_satuan") or 0
            item_sat   = str(item_dict_row.get("Satuan") or item_dict_row.get("satuan") or "")

            # Get validation result
            res = result_lookup.get(item_name, {})
            val_status = res.get("status", None)
            val_score  = res.get("score", None)

            # Status badge
            if val_status:
                status_html = render_status_badge(val_status)
            else:
                status_html = '<span class="status-badge neutral">◽ Belum Divalidasi</span>'

            # Confidence pill
            if val_score is not None:
                score_pct = round(float(val_score) * 100)
                pill_level = "high" if score_pct >= 70 else ("medium" if score_pct >= 40 else "low")
                conf_html = f'<span class="confidence-pill {pill_level}">{score_pct}%</span>'
            else:
                conf_html = '<span class="confidence-pill none">—</span>'

            # Price
            try:
                price_display = format_currency_full(float(item_harga))
            except (ValueError, TypeError):
                price_display = str(item_harga) if item_harga else "N/A"

            # Truncated name for display
            name_truncated = item_name[:80] + ("..." if len(item_name) > 80 else "")
            id_truncated   = item_id[:12]
            kat_truncated  = item_kat[:20]

            # Row selected state
            is_selected = (active_drawer == item_name)
            row_class = "proc-table-row selected" if is_selected else "proc-table-row"

            # Render HTML row
            st.markdown(f"""
            <div class="{row_class}">
                <div class="proc-cell-id">{id_truncated}</div>
                <div class="proc-cell-name" title="{item_name}">{name_truncated}</div>
                <div class="proc-cell-category">{kat_truncated}</div>
                <div class="proc-cell-price">{price_display}</div>
                <div>{status_html}</div>
                <div>{conf_html}</div>
                <div style="color: #64748B; font-size: 0.72rem;">↓ actions below</div>
            </div>
            """, unsafe_allow_html=True)

            # Action buttons — rendered as Streamlit native buttons in a tight row
            btn_col1, btn_col2, btn_col3, btn_col4, _ = st.columns([1.2, 1.2, 1.2, 1.5, 3])

            with btn_col1:
                view_label = "🔼 Close" if is_selected else "👁 View Detail"
                if st.button(view_label, key=f"view_{row_idx}_{item_name[:20]}", use_container_width=True):
                    if is_selected:
                        st.session_state.selected_drawer_item = None
                    else:
                        st.session_state.selected_drawer_item = item_name
                        # Pre-load candidates and reasoning
                        _item_for_drawer = item_dict_row.copy()
                        if "Nama Barang dan Spesifikasi" in _item_for_drawer and "nama_barang" not in _item_for_drawer:
                            _item_for_drawer["nama_barang"] = _item_for_drawer["Nama Barang dan Spesifikasi"]
                        if "Kategori" in _item_for_drawer and "kategori" not in _item_for_drawer:
                            _item_for_drawer["kategori"] = _item_for_drawer["Kategori"]
                        if "Satuan" in _item_for_drawer and "satuan" not in _item_for_drawer:
                            _item_for_drawer["satuan"] = _item_for_drawer["Satuan"]
                        raw_nama = str(_item_for_drawer.get("nama_barang", ""))
                        if "Spesifikasi:" in raw_nama and not _item_for_drawer.get("spesifikasi"):
                            _parts = raw_nama.split("Spesifikasi:", 1)
                            _item_for_drawer["nama_barang"] = _parts[0].strip()
                            _item_for_drawer["spesifikasi"] = _parts[1].strip()
                        cands = generate_placeholder_candidates(_item_for_drawer)
                        st.session_state.drawer_candidates = cands
                        # Enrich candidates with reasoning scores
                        enriched = []
                        for c in cands:
                            ev = run_reasoning(_item_for_drawer, c)
                            ev_data = ev.get("candidate_evaluation", {})
                            c["score"]  = ev_data.get("match_score", 0)
                            c["status"] = ev_data.get("candidate_status", "—")
                            enriched.append(c)
                        st.session_state.drawer_candidates = enriched
                        # Store best reasoning
                        best_sc, best_rs = -1, []
                        for c in enriched:
                            ev = run_reasoning(_item_for_drawer, c)
                            sc = ev["candidate_evaluation"]["match_score"]
                            if sc > best_sc:
                                best_sc = sc
                                best_rs = ev["candidate_evaluation"]["reasoning"]
                        st.session_state.drawer_reasoning = best_rs
                        st.session_state.rejected_candidates = set()
                        st.session_state.selected_candidates = set()
                    st.rerun()

            with btn_col2:
                if st.button("🔄 Search Again", key=f"search_{row_idx}_{item_name[:20]}", use_container_width=True):
                    _item_s = item_dict_row.copy()
                    if "Nama Barang dan Spesifikasi" in _item_s and "nama_barang" not in _item_s:
                        _item_s["nama_barang"] = _item_s["Nama Barang dan Spesifikasi"]
                    if "Satuan" in _item_s and "satuan" not in _item_s:
                        _item_s["satuan"] = _item_s["Satuan"]
                    with st.spinner(f"🔄 Mencari kandidat untuk {item_name[:40]}..."):
                        cands = generate_placeholder_candidates(_item_s)
                        enriched = []
                        for c in cands:
                            ev = run_reasoning(_item_s, c)
                            ev_data = ev.get("candidate_evaluation", {})
                            c["score"]  = ev_data.get("match_score", 0)
                            c["status"] = ev_data.get("candidate_status", "—")
                            enriched.append(c)
                    if st.session_state.selected_drawer_item == item_name:
                        st.session_state.drawer_candidates = enriched
                        st.session_state.rejected_candidates = set()
                        st.session_state.selected_candidates = set()
                    st.session_state.drawer_item_action_status[item_name] = f"✅ {len(enriched)} kandidat ditemukan"
                    st.rerun()

            with btn_col3:
                if st.button("✅ Run Validation", key=f"val_{row_idx}_{item_name[:20]}", use_container_width=True):
                    _item_v = item_dict_row.copy()
                    if "Nama Barang dan Spesifikasi" in _item_v and "nama_barang" not in _item_v:
                        _item_v["nama_barang"] = _item_v["Nama Barang dan Spesifikasi"]
                    if "Kategori" in _item_v and "kategori" not in _item_v:
                        _item_v["kategori"] = _item_v["Kategori"]
                    if "Satuan" in _item_v and "satuan" not in _item_v:
                        _item_v["satuan"] = _item_v["Satuan"]
                    if "Harga Satuan" in _item_v and "harga_satuan" not in _item_v:
                        _item_v["harga_satuan"] = _item_v["Harga Satuan"]
                    raw_n = str(_item_v.get("nama_barang", ""))
                    if "Spesifikasi:" in raw_n and not _item_v.get("spesifikasi"):
                        _p = raw_n.split("Spesifikasi:", 1)
                        _item_v["nama_barang"] = _p[0].strip()
                        _item_v["spesifikasi"] = _p[1].strip()
                    with st.spinner(f"✅ Menjalankan validasi untuk {item_name[:40]}..."):
                        cands_v = generate_placeholder_candidates(_item_v)
                        best_sc_v, best_ev_v, best_c_v = -1, {}, {}
                        for c in cands_v:
                            ev = run_reasoning(_item_v, c)
                            sc = ev["candidate_evaluation"]["match_score"]
                            if sc > best_sc_v:
                                best_sc_v = sc
                                best_ev_v = ev["candidate_evaluation"]
                                best_c_v = c
                        new_res = {
                            "id_item": _item_v.get("id_item") or _item_v.get("ID"),
                            "nama_barang": _item_v.get("nama_barang"),
                            "satuan": _item_v.get("satuan"),
                            "harga_satuan": _item_v.get("harga_satuan"),
                            "comparison_product": best_c_v.get("nama_produk", "N/A"),
                            "comparison_specification": best_c_v.get("spesifikasi", "N/A"),
                            "vendor": best_c_v.get("vendor", "N/A"),
                            "comparison_price": best_c_v.get("harga", 0),
                            "status": best_ev_v.get("candidate_status", "NO_CANDIDATE"),
                            "score": best_ev_v.get("match_score", 0),
                            "deviation_notes": ", ".join(best_ev_v.get("deviation_notes", [])),
                        }
                        # Update or append to result_df
                        res_df_cur = st.session_state.result_df
                        if not res_df_cur.empty and "nama_barang" in res_df_cur.columns:
                            mask = res_df_cur["nama_barang"] == _item_v.get("nama_barang")
                            if mask.any():
                                for k, v in new_res.items():
                                    st.session_state.result_df.loc[mask, k] = v
                            else:
                                st.session_state.result_df = pd.concat(
                                    [res_df_cur, pd.DataFrame([new_res])], ignore_index=True
                                )
                        else:
                            st.session_state.result_df = pd.DataFrame([new_res])
                        st.session_state.validation_run = True
                        if st.session_state.selected_drawer_item == item_name:
                            st.session_state.drawer_reasoning = best_ev_v.get("reasoning", [])
                    st.session_state.drawer_item_action_status[item_name] = f"✅ Validasi selesai — {best_ev_v.get('candidate_status','')}"
                    st.rerun()

            with btn_col4:
                if st.button("📝 Generate Reasoning", key=f"reason_{row_idx}_{item_name[:20]}", use_container_width=True):
                    _item_r = item_dict_row.copy()
                    if "Nama Barang dan Spesifikasi" in _item_r and "nama_barang" not in _item_r:
                        _item_r["nama_barang"] = _item_r["Nama Barang dan Spesifikasi"]
                    if "Satuan" in _item_r and "satuan" not in _item_r:
                        _item_r["satuan"] = _item_r["Satuan"]
                    with st.spinner(f"📝 Generating reasoning untuk {item_name[:40]}..."):
                        cands_r = generate_placeholder_candidates(_item_r)
                        best_sc_r, best_rs_r = -1, []
                        for c in cands_r:
                            ev = run_reasoning(_item_r, c)
                            sc = ev["candidate_evaluation"]["match_score"]
                            if sc > best_sc_r:
                                best_sc_r = sc
                                best_rs_r = ev["candidate_evaluation"]["reasoning"]
                    if st.session_state.selected_drawer_item == item_name:
                        st.session_state.drawer_reasoning = best_rs_r
                    st.session_state.drawer_item_action_status[item_name] = f"📝 Reasoning diperbarui ({len(best_rs_r)} poin)"
                    st.rerun()

            # Show action status feedback if any
            action_status = st.session_state.drawer_item_action_status.get(item_name)
            if action_status:
                st.caption(f"   {action_status}")

            # ── INLINE DETAIL DRAWER ─────────────────────────────
            if is_selected:
                res = result_lookup.get(item_name, {})
                val_status_d = res.get("status", "BELUM_DIVALIDASI")
                val_score_d  = res.get("score", 0.0)
                dev_notes_d  = res.get("deviation_notes", "")
                ref_price_d  = item_dict_row.get("Harga Satuan") or item_dict_row.get("harga_satuan") or 0
                item_sat_d   = str(item_dict_row.get("Satuan") or item_dict_row.get("satuan") or "—")
                item_id_d    = str(item_dict_row.get("ID") or item_dict_row.get("id_item") or "N/A")

                try:
                    ref_price_float = float(ref_price_d)
                except (ValueError, TypeError):
                    ref_price_float = 0.0

                spec_text_d = str(
                    item_dict_row.get("Spesifikasi") or
                    item_dict_row.get("spesifikasi") or ""
                )

                drawer_candidates = st.session_state.drawer_candidates
                drawer_reasoning  = st.session_state.drawer_reasoning

                # Compute max deviation across all candidates
                max_dev_pct = 0.0
                for c in drawer_candidates:
                    _, _, dpct = _calc_deviation(ref_price_float, c.get("harga") or c.get("comparison_price") or 0)
                    if abs(dpct) > abs(max_dev_pct):
                        max_dev_pct = dpct

                # ── Drawer Header ──────────────────────────────
                status_badge_d = render_status_badge(val_status_d) if val_status_d != "BELUM_DIVALIDASI" else '<span class="status-badge neutral">◽ Belum Divalidasi</span>'
                score_pct_d = round(float(val_score_d) * 100) if val_score_d else 0
                pill_d = "high" if score_pct_d >= 70 else ("medium" if score_pct_d >= 40 else ("low" if score_pct_d > 0 else "none"))

                st.markdown(f"""
                <div class="detail-drawer">
                    <div class="drawer-header">
                        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 10px;">
                            <span style="color: #64748B; font-size: 0.7rem; background: rgba(30,58,95,0.5); padding: 3px 10px; border-radius: 6px; font-family: monospace;">ID: {item_id_d}</span>
                            <span style="color: #64748B; font-size: 0.7rem; background: rgba(30,58,95,0.5); padding: 3px 10px; border-radius: 6px;">📁 {item_kat[:40]}</span>
                            {status_badge_d}
                            <span class="confidence-pill {pill_d}" style="margin-left: 4px;">🎯 {score_pct_d}% Confidence</span>
                        </div>
                        <div style="color: #F1F5F9; font-size: 1.15rem; font-weight: 700; line-height: 1.4; margin-bottom: 12px;">{item_name}</div>

                        <div class="drawer-item-header">
                            <div class="drawer-info-block">
                                <span class="drawer-info-label">Item ID</span>
                                <span class="drawer-info-value">{item_id_d}</span>
                            </div>
                            <div class="drawer-info-block">
                                <span class="drawer-info-label">Kategori</span>
                                <span class="drawer-info-value">{item_kat[:35]}</span>
                            </div>
                            <div class="drawer-info-block">
                                <span class="drawer-info-label">Satuan</span>
                                <span class="drawer-info-value">{item_sat_d}</span>
                            </div>
                            <div class="drawer-info-block">
                                <span class="drawer-info-label">Reference Price</span>
                                <span class="drawer-info-value price">{format_currency_full(ref_price_float)}</span>
                            </div>
                            <div class="drawer-info-block">
                                <span class="drawer-info-label">Confidence Score</span>
                                <span class="drawer-info-value" style="color: {'#10B981' if score_pct_d >= 70 else ('#F59E0B' if score_pct_d >= 40 else '#EF4444')}">{score_pct_d}%</span>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # ── Section 1: Extracted Specification ────────
                st.markdown("""
                    <div class="drawer-section">
                        <div class="drawer-section-title">🔬 Extracted Specification</div>
                """, unsafe_allow_html=True)
                spec_grid_html = render_spec_grid(spec_text_d, item_dict_row)
                st.markdown(spec_grid_html, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # ── Section 2: Validation Checklist ───────────
                st.markdown("""
                    <div class="drawer-section">
                        <div class="drawer-section-title">✅ Validation Checklist</div>
                """, unsafe_allow_html=True)
                if drawer_reasoning:
                    checklist_html = render_validation_checklist(drawer_reasoning)
                    st.markdown(checklist_html, unsafe_allow_html=True)
                else:
                    st.markdown('<div style="color: #64748B; font-size: 0.82rem; font-style: italic;">Klik ✅ Run Validation atau 📝 Generate Reasoning untuk melihat checklist.</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # ── Section 3: Candidate Comparison ──────────
                st.markdown("""
                    <div class="drawer-section">
                        <div class="drawer-section-title">🔍 Candidate Comparison</div>
                """, unsafe_allow_html=True)
                if drawer_candidates:
                    # Render HTML table rows
                    cand_table_html = render_candidate_comparison_table(
                        drawer_candidates,
                        ref_price_float,
                        st.session_state.selected_candidates,
                        st.session_state.rejected_candidates,
                    )
                    st.markdown(cand_table_html, unsafe_allow_html=True)
                else:
                    st.markdown('<div style="color: #64748B; font-size: 0.82rem; font-style: italic;">Klik 👁 View Detail atau 🔄 Search Again untuk memuat kandidat.</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # Candidate action buttons (below drawer HTML section)
                if drawer_candidates:
                    st.markdown("**Aksi per Kandidat:**")
                    for ci, cand in enumerate(drawer_candidates):
                        cand_id = f"cand_{ci}"
                        vendor_name = cand.get("vendor", f"Vendor {ci+1}")
                        prod_name   = str(cand.get("nama_produk") or "Kandidat")[:50]
                        cand_price  = cand.get("harga") or cand.get("comparison_price") or 0
                        _, _, dev_pct_ci = _calc_deviation(ref_price_float, cand_price)

                        ca1, ca2, ca3, ca4, _ = st.columns([0.5, 1.2, 1.2, 1.2, 4])
                        with ca1:
                            st.markdown(f"<div style='color: #64748B; font-size: 0.78rem; padding-top: 8px;'>#{ci+1}</div>", unsafe_allow_html=True)
                        with ca2:
                            link_url = cand.get("url", "#")
                            if st.button(f"🔗 Source Link", key=f"link_{row_idx}_{ci}_{item_name[:10]}", use_container_width=True):
                                st.info(f"URL: {link_url}")
                        with ca3:
                            is_sel = cand_id in st.session_state.selected_candidates
                            sel_label = "✓ Selected" if is_sel else "✓ Select"
                            if st.button(sel_label, key=f"sel_{row_idx}_{ci}_{item_name[:10]}", use_container_width=True):
                                if is_sel:
                                    st.session_state.selected_candidates.discard(cand_id)
                                else:
                                    st.session_state.selected_candidates.add(cand_id)
                                st.rerun()
                        with ca4:
                            is_rej = cand_id in st.session_state.rejected_candidates
                            rej_label = "↩ Undo Reject" if is_rej else "✗ Reject"
                            if st.button(rej_label, key=f"rej_{row_idx}_{ci}_{item_name[:10]}", use_container_width=True):
                                if is_rej:
                                    st.session_state.rejected_candidates.discard(cand_id)
                                else:
                                    st.session_state.rejected_candidates.add(cand_id)
                                st.rerun()

                # ── Section 4: Procurement Reasoning ──────────
                st.markdown("""
                    <div class="drawer-section">
                        <div class="drawer-section-title">🧠 Procurement Reasoning</div>
                """, unsafe_allow_html=True)
                reasoning_html = render_procurement_reasoning_block(
                    drawer_reasoning,
                    val_status_d,
                    val_score_d,
                    dev_notes_d,
                )
                st.markdown(reasoning_html, unsafe_allow_html=True)

                # High deviation warning inside reasoning section
                if max_dev_pct != 0.0:
                    warning_html = render_deviation_warning(max_dev_pct)
                    if warning_html:
                        st.markdown(warning_html, unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

                # Close drawer div
                st.markdown("</div>", unsafe_allow_html=True)

                # ── Drawer Footer Actions ──────────────────────
                st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
                df_col1, df_col2, df_col3 = st.columns(3)
                with df_col1:
                    if st.button("🔼 Close Detail Panel", key=f"close_drawer_{row_idx}", use_container_width=True):
                        st.session_state.selected_drawer_item = None
                        st.rerun()
                with df_col2:
                    if st.button("🔗 Open in Item Detail Page", key=f"open_detail_page_{row_idx}", use_container_width=True):
                        st.session_state.selected_item_name = item_name
                        st.info("➡️ Navigasikan ke **🔍 Item Detail** di sidebar untuk detail lebih lengkap.")
                with df_col3:
                    # Export quick justification
                    if res:
                        just_text = generate_justification_text(item_dict_row, res)
                        st.download_button(
                            "📥 Export Justifikasi",
                            data=just_text.encode("utf-8"),
                            file_name=f"justifikasi_{item_name[:30].replace(' ','_')}.txt",
                            mime="text/plain",
                            use_container_width=True,
                            key=f"dl_just_{row_idx}",
                        )


                st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)


# ============================================================
# PAGE: Item Detail — Primary Workspace
# ============================================================

elif page == "🔍 Item Detail":
    render_page_header("🔍", "Item Detail", "Analisis validasi pengadaan per item")

    if st.session_state.proc_df.empty:
        st.info("📂 Tidak ada data. Upload file pengadaan.")
    else:
        proc_df = st.session_state.proc_df
        nama_col = get_nama_col(proc_df)

        item_names = proc_df[nama_col].dropna().unique().tolist() if nama_col in proc_df.columns else []

        default_idx = 0
        if st.session_state.selected_item_name and st.session_state.selected_item_name in item_names:
            default_idx = item_names.index(st.session_state.selected_item_name)

        selected_name = st.selectbox("📋 Pilih Item", item_names, index=default_idx, key="item_detail_select")

        if not selected_name:
            st.info("Pilih item dari daftar di atas.")
        else:
            # ── Get item data ─────────────────────────────────
            item_row = proc_df[proc_df[nama_col] == selected_name].iloc[0]
            item_dict = item_row.to_dict()

            # Normalize column names for backend compatibility
            if "Nama Barang dan Spesifikasi" in item_dict and "nama_barang" not in item_dict:
                item_dict["nama_barang"] = item_dict["Nama Barang dan Spesifikasi"]
            if "Kategori" in item_dict and "kategori" not in item_dict:
                item_dict["kategori"] = item_dict["Kategori"]
            if "Sub kategori" in item_dict and "subkategori" not in item_dict:
                item_dict["subkategori"] = item_dict["Sub kategori"]
            if "Satuan" in item_dict and "satuan" not in item_dict:
                item_dict["satuan"] = item_dict["Satuan"]
            if "Harga Satuan" in item_dict and "harga_satuan" not in item_dict:
                item_dict["harga_satuan"] = item_dict["Harga Satuan"]

            raw_nama = str(item_dict.get("nama_barang", ""))
            if "Spesifikasi:" in raw_nama and not item_dict.get("spesifikasi"):
                parts = raw_nama.split("Spesifikasi:", 1)
                item_dict["nama_barang"] = parts[0].strip()
                item_dict["spesifikasi"] = parts[1].strip()

            id_val    = str(item_dict.get("id_item") or item_dict.get("ID") or "N/A")
            kat_val   = str(item_dict.get("kategori") or "N/A")
            sat_val   = str(item_dict.get("satuan") or "N/A")
            harga_val = item_dict.get("harga_satuan") or 0

            # ── Get validation result ──────────────────────────
            result_row = None
            if st.session_state.validation_run and not st.session_state.result_df.empty and 'status' in st.session_state.result_df.columns:
                match = st.session_state.result_df[st.session_state.result_df['nama_barang'] == selected_name]
                if not match.empty:
                    result_row = match.iloc[0].to_dict()

            val_status = result_row.get("status", "BELUM_DIVALIDASI") if result_row else "BELUM_DIVALIDASI"
            val_score  = result_row.get("score", 0.0) if result_row else 0.0
            score_pct  = round(float(val_score) * 100) if val_score else 0

            # ── Item Header ──────────────────────────────────
            st.divider()
            h_col1, h_col2, h_col3 = st.columns([5, 1, 1])
            with h_col1:
                st.subheader(selected_name[:100])
                st.caption(f"ID: {id_val}  ·  Kategori: {kat_val}  ·  Satuan: {sat_val}")
            with h_col2:
                if val_status in ("VALID", "MATCH"):
                    st.success("✅ VALID")
                elif val_status == "PARTIAL_MATCH":
                    st.warning("⚠️ PARTIAL")
                elif val_status == "BELUM_DIVALIDASI":
                    st.info("◽ Belum")
                else:
                    st.error("❌ INVALID")
            with h_col3:
                st.metric("Confidence", f"{score_pct}%")

            # ── Action Buttons ───────────────────────────────
            act1, act2, act3, _ = st.columns([1, 1, 1, 4])

            with act1:
                if st.button("✅ Run Validation", key="detail_run_val", use_container_width=True):
                    with st.spinner("Menjalankan validasi..."):
                        _item_v = item_dict.copy()
                        cands_v = generate_placeholder_candidates(_item_v)
                        best_sc_v, best_ev_v, best_c_v = -1, {}, {}
                        for c in cands_v:
                            ev = run_reasoning(_item_v, c)
                            sc = ev["candidate_evaluation"]["match_score"]
                            if sc > best_sc_v:
                                best_sc_v = sc
                                best_ev_v = ev["candidate_evaluation"]
                                best_c_v  = c
                        new_res = {
                            "id_item":                    _item_v.get("id_item") or _item_v.get("ID"),
                            "nama_barang":                _item_v.get("nama_barang"),
                            "satuan":                     _item_v.get("satuan"),
                            "harga_satuan":               _item_v.get("harga_satuan"),
                            "comparison_product":         best_c_v.get("nama_produk", "N/A"),
                            "comparison_specification":   best_c_v.get("spesifikasi", "N/A"),
                            "vendor":                     best_c_v.get("vendor", "N/A"),
                            "comparison_price":           best_c_v.get("harga", 0),
                            "status":                     best_ev_v.get("candidate_status", "NO_CANDIDATE"),
                            "score":                      best_ev_v.get("match_score", 0),
                            "deviation_notes":            ", ".join(best_ev_v.get("deviation_notes", [])),
                        }
                        st.session_state.drawer_reasoning = best_ev_v.get("reasoning", [])
                        st.session_state.drawer_candidates = cands_v
                        res_df_cur = st.session_state.result_df
                        if not res_df_cur.empty and "nama_barang" in res_df_cur.columns:
                            mask = res_df_cur["nama_barang"] == _item_v.get("nama_barang")
                            if mask.any():
                                for k, v in new_res.items():
                                    st.session_state.result_df.loc[mask, k] = v
                            else:
                                st.session_state.result_df = pd.concat(
                                    [res_df_cur, pd.DataFrame([new_res])], ignore_index=True
                                )
                        else:
                            st.session_state.result_df = pd.DataFrame([new_res])
                        st.session_state.validation_run = True
                    st.rerun()

            with act2:
                if st.button("🔄 Search Again", key="detail_search", use_container_width=True):
                    with st.spinner("Mencari kandidat..."):
                        cands_s = generate_placeholder_candidates(item_dict)
                        enriched_s = []
                        for c in cands_s:
                            ev = run_reasoning(item_dict, c)
                            ev_data = ev.get("candidate_evaluation", {})
                            c["score"]  = ev_data.get("match_score", 0)
                            c["status"] = ev_data.get("candidate_status", "—")
                            enriched_s.append(c)
                        st.session_state.drawer_candidates = enriched_s
                    st.rerun()

            with act3:
                if st.button("📝 Generate Reasoning", key="detail_reasoning", use_container_width=True):
                    with st.spinner("Generating reasoning..."):
                        cands_r = generate_placeholder_candidates(item_dict)
                        best_sc_r, best_rs_r = -1, []
                        for c in cands_r:
                            ev = run_reasoning(item_dict, c)
                            sc = ev["candidate_evaluation"]["match_score"]
                            if sc > best_sc_r:
                                best_sc_r = sc
                                best_rs_r = ev["candidate_evaluation"]["reasoning"]
                        st.session_state.drawer_reasoning = best_rs_r
                    st.rerun()

            st.divider()

            # ── 5 Tabs ───────────────────────────────────────────
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📋 Overview",
                "📈 Price History",
                "🏢 Vendor History",
                "✅ Validation",
                "📄 Justification",
            ])

            # ═══ TAB 1: OVERVIEW ══════════════════════════════
            with tab1:
                st.markdown("#### Informasi Item")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("ID Item",          id_val)
                m2.metric("Kategori",         kat_val[:22])
                m3.metric("Satuan",           sat_val)
                m4.metric("Harga Referensi",  format_currency_full(harga_val))

                st.markdown("---")
                st.markdown("#### Konteks Pengadaan")
                ctx1, ctx2 = st.columns(2)
                with ctx1:
                    render_info_card("Konteks Pengadaan",   "Pembelian rutin operasional pemerintah daerah")
                    render_info_card("Fungsi Bisnis",        "Operasional & Dukungan Kegiatan")
                    render_info_card("Sumber Anggaran",      "APBD DKI Jakarta — SHBJ 2025")
                with ctx2:
                    render_info_card("Kriteria Validasi",   "Kewajaran harga, ketersediaan vendor, kecocokan spesifikasi")
                    render_info_card("Standar Spesifikasi",  "Mengikuti standar LKPP / Internal SHBJ DKI Jakarta")
                    render_info_card("Prioritas Match",     "Fungsi → Spesifikasi → Ukuran → Material → Satuan → Harga")

                # Extracted specification
                import re as _re
                spec_raw = str(item_dict.get("spesifikasi") or item_dict.get("Spesifikasi") or "")
                if spec_raw:
                    st.markdown("---")
                    st.markdown("#### Spesifikasi Teknis")
                    ATTR_PATTERNS = [
                        ("Part Number",   r"(?:part\s*(?:number|no|num|#))[\s:]+([^\n;,]{1,80})"),
                        ("Brand / Merek", r"(?:brand|merek|merk)[\s:]+([^\n;,]{1,60})"),
                        ("Fungsi",        r"(?:function|fungsi|kegunaan)[\s:]+([^\n;,]{1,80})"),
                        ("Kapasitas",     r"(?:capacity|kapasitas|volume)[\s:]+([^\n;,]{1,60})"),
                        ("Dimensi",       r"(?:dimension|dimensi|ukuran|size)[\s:]+([^\n;,]{1,60})"),
                        ("Material",      r"(?:material|bahan)[\s:]+([^\n;,]{1,60})"),
                        ("Tegangan",      r"(?:voltage|tegangan|volt)[\s:]+([^\n;,]{1,60})"),
                        ("Daya",          r"(?:power|daya|watt)[\s:]+([^\n;,]{1,60})"),
                    ]
                    spec_attrs = []
                    for slabel, spattern in ATTR_PATTERNS:
                        sm = _re.search(spattern, spec_raw, _re.IGNORECASE)
                        if sm:
                            sv = sm.group(1).strip().rstrip(".,;")
                            if sv:
                                spec_attrs.append((slabel, sv))
                    if not spec_attrs:
                        for sline in _re.split(r"[;\n]+", spec_raw)[:8]:
                            sline = sline.strip()
                            if ":" in sline:
                                sk, _, sv2 = sline.partition(":")
                                if sk.strip() and sv2.strip():
                                    spec_attrs.append((sk.strip()[:30], sv2.strip()[:80]))
                    if spec_attrs:
                        for si in range(0, len(spec_attrs), 3):
                            schunk = spec_attrs[si:si+3]
                            scols = st.columns(3)
                            for sj, (slbl, sval) in enumerate(schunk):
                                scols[sj].metric(slbl, sval[:40])
                    else:
                        st.info(spec_raw[:400])

                if result_row:
                    st.markdown("---")
                    st.markdown(render_score_bar(result_row["score"], "Skor Kecocokan AI"), unsafe_allow_html=True)

            # ═══ TAB 2: PRICE HISTORY ══════════════════════════
            with tab2:
                st.markdown("#### Riwayat Anggaran SHBJ 2025")

                try:
                    harga_numeric = float(pd.to_numeric(harga_val, errors='coerce'))
                    if pd.isna(harga_numeric):
                        harga_numeric = None
                except (ValueError, TypeError):
                    harga_numeric = None

                spec_t2 = str(item_dict.get("spesifikasi") or item_dict.get("Spesifikasi") or "")
                sat_t2  = sat_val if sat_val != "N/A" else ""
                kat_t2  = kat_val if kat_val != "N/A" else ""

                shbj_match = find_shbj_match(
                    item_name=selected_name, item_spec=spec_t2,
                    item_satuan=sat_t2, item_kategori=kat_t2,
                    shbj_df=st.session_state.shbj_df,
                )

                if shbj_match:
                    harga_shbj_ref = shbj_match.get("harga_satuan_shbj")
                    harga_est_2025 = shbj_match.get("est_harga_2025")
                    harga_shbj = harga_est_2025 if harga_est_2025 else harga_shbj_ref

                    match_label = {
                        "exact_name_spec": "✅ Kecocokan nama + spesifikasi",
                        "exact_name":      "🔎 Kecocokan nama",
                        "category_fallback": "📂 Fallback kategori",
                    }.get(shbj_match.get("match_type", ""), "🔎 Kecocokan")

                    # Compute deviation for chip rendering
                    _t2_pct_abs = None
                    _t2_pct_val = None
                    if harga_shbj and harga_numeric and harga_shbj > 0:
                        _t2_pct_val = (harga_numeric - harga_shbj) / harga_shbj * 100
                        _t2_pct_abs = abs(_t2_pct_val)

                    # Kewajaran chip
                    if _t2_pct_abs is not None:
                        if _t2_pct_abs <= 5:
                            _chip_html = '<span class="kewajaran-chip wajar">✅ Harga Wajar</span>'
                        elif _t2_pct_abs <= 15:
                            _chip_html = '<span class="kewajaran-chip perhatian">⚠️ Perlu Perhatian</span>'
                        else:
                            _chip_html = '<span class="kewajaran-chip deviasi">❌ Deviasi Signifikan</span>'
                    else:
                        _chip_html = ''

                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px;">'
                        f'<span style="color:#64748B;font-size:0.75rem;">Sumber SHBJ: {match_label} &nbsp;|&nbsp; '
                        f'ID: {shbj_match.get("shbj_id", "N/A")} &nbsp;|&nbsp; '
                        f'Kategori: {shbj_match.get("shbj_kategori", "N/A")}</span>'
                        f'{_chip_html}</div>',
                        unsafe_allow_html=True
                    )

                    pc1, pc2, pc3 = st.columns(3)
                    pc1.metric("Harga SHBJ 2025",   format_currency_full(harga_shbj) if harga_shbj else "N/A")
                    pc2.metric("Harga Pengadaan",   format_currency_full(harga_numeric) if harga_numeric else "N/A")
                    if harga_shbj and harga_numeric:
                        delta_val = harga_numeric - harga_shbj
                        pct_val   = _t2_pct_val
                        pc3.metric("Deviasi", f"{pct_val:+.1f}%",
                                   delta=f"Rp {abs(delta_val):,.0f}".replace(",", "."),
                                   delta_color="inverse")
                    else:
                        pc3.metric("Deviasi", "N/A")

                    if harga_shbj and harga_numeric:
                        st.markdown("---")
                        chart_cmp = pd.DataFrame(
                            {"Harga (Rp)": [harga_shbj, harga_numeric]},
                            index=["SHBJ 2025", "Pengadaan"]
                        )
                        st.bar_chart(chart_cmp, color="#0D9488")

                        pct_abs = _t2_pct_abs
                        if pct_abs <= 5:
                            st.success(f"✅ Harga wajar — deviasi {pct_abs:.1f}% dalam batas toleransi (≤5%)")
                        elif pct_abs <= 15:
                            st.warning(f"⚠️ Perlu perhatian — deviasi {pct_abs:.1f}% dari SHBJ 2025")
                        else:
                            st.error(f"❌ Deviasi signifikan — {pct_abs:.1f}% dari SHBJ 2025. Wajib justifikasi khusus.")

                    st.markdown("---")
                    sd1, sd2, sd3 = st.columns(3)
                    sd1.metric("Nama SHBJ",     shbj_match.get('shbj_nama', 'N/A')[:30])
                    sd2.metric("Satuan SHBJ",   shbj_match.get('shbj_satuan', 'N/A'))
                    sd3.metric("Status",         shbj_match.get('keterangan', 'N/A')[:25])

                else:
                    st.info("ℹ️ Tidak ditemukan histori anggaran 2025 untuk item ini.")
                    if harga_numeric:
                        st.markdown("#### Tren Anggaran Estimasi")
                        st.caption("Data historis estimasi — belum ditemukan data riil SHBJ 2025.")
                        history = get_budget_history(selected_name, harga_numeric)
                        hist_df = pd.DataFrame(history)[["tahun", "harga_satuan"]].copy()
                        hist_df["tahun"] = hist_df["tahun"].astype(str)
                        hist_df = hist_df.set_index("tahun")
                        hist_df.columns = ["Harga Satuan (Rp)"]
                        st.line_chart(hist_df, color="#F59E0B")

            # ═══ TAB 3: VENDOR HISTORY ═════════════════════════
            with tab3:
                st.markdown("#### Kandidat Pembanding")

                candidates = st.session_state.drawer_candidates
                if not candidates:
                    with st.spinner("Memuat kandidat..."):
                        _cands_t3 = generate_placeholder_candidates(item_dict)
                        _enriched_t3 = []
                        for c in _cands_t3:
                            ev = run_reasoning(item_dict, c)
                            ev_d = ev.get("candidate_evaluation", {})
                            c["score"]  = ev_d.get("match_score", 0)
                            c["status"] = ev_d.get("candidate_status", "—")
                            _enriched_t3.append(c)
                        st.session_state.drawer_candidates = _enriched_t3
                        candidates = _enriched_t3

                SOURCE_MAP = {
                    "vendor a": "INAPROC",  "vendor b": "Tokopedia",
                    "vendor c": "Shopee",   "inaproc":  "INAPROC",
                    "tokopedia": "Tokopedia", "shopee": "Shopee",
                }

                cand_rows = []
                for c in candidates:
                    vendor  = str(c.get("vendor", "N/A"))
                    price   = c.get("harga") or c.get("comparison_price") or 0
                    score_c = c.get("score")
                    source  = next((v for k, v in SOURCE_MAP.items() if k in vendor.lower()), "Official Vendor")
                    location = str(c.get("lokasi") or "Jakarta")
                    try:
                        ref_f   = float(harga_val)
                        cand_f  = float(price)
                        dev_pct = ((cand_f - ref_f) / ref_f * 100) if ref_f > 0 else 0
                        dev_str = f"{dev_pct:+.1f}%"
                    except (ValueError, TypeError):
                        dev_str = "N/A"
                    cand_rows.append({
                        "Source":     source,
                        "Vendor":     vendor[:30],
                        "Product":    str(c.get("nama_produk") or c.get("comparison_product") or "N/A")[:50],
                        "Location":   location,
                        "Price":      format_currency_full(price),
                        "Deviation": dev_str,
                        "Confidence": f"{round(float(score_c)*100)}%" if score_c is not None else "—",
                        "Status":     str(c.get("status", "—")),
                    })

                if cand_rows:
                    cand_df = pd.DataFrame(cand_rows)
                    st.dataframe(
                        cand_df, use_container_width=True, hide_index=True,
                        column_config={
                            "Source":     st.column_config.TextColumn("Source",    width="small"),
                            "Vendor":     st.column_config.TextColumn("Vendor",    width="medium"),
                            "Product":    st.column_config.TextColumn("Product",   width="large"),
                            "Location":   st.column_config.TextColumn("Location",  width="small"),
                            "Price":      st.column_config.TextColumn("Price",     width="medium"),
                            "Deviation":  st.column_config.TextColumn("Dev %",     width="small"),
                            "Confidence": st.column_config.TextColumn("Confidence",width="small"),
                            "Status":     st.column_config.TextColumn("Status",    width="small"),
                        },
                    )
                else:
                    st.info("Tidak ada kandidat. Klik 🔄 Search Again untuk mencari.")

                if result_row:
                    st.markdown("---")
                    st.markdown("#### 🏆 Kandidat Terpilih")
                    render_candidate_card(result_row)

                st.markdown("---")
                st.markdown("#### Profil Vendor")
                vendor_info = get_vendor_for_item(selected_name)
                if result_row and result_row.get("vendor") and result_row["vendor"] != "N/A":
                    vendor_info["nama"] = result_row["vendor"]
                render_vendor_card(vendor_info)

                transactions = get_vendor_transactions(vendor_info["nama"])
                if transactions:
                    tx_df = pd.DataFrame(transactions)
                    tx_df["harga_fmt"] = tx_df["harga_satuan"].apply(format_currency_full)
                    tx_df["total_fmt"] = tx_df["total_nilai"].apply(format_currency)
                    st.dataframe(
                        tx_df[["tahun","nama_barang","harga_fmt","satuan","jumlah","total_fmt","status_kontrak"]].rename(
                            columns={"tahun":"Tahun","nama_barang":"Item","harga_fmt":"Harga",
                                     "satuan":"Satuan","jumlah":"Qty","total_fmt":"Total","status_kontrak":"Status"}
                        ),
                        use_container_width=True, hide_index=True,
                    )

                if result_row:
                    st.markdown("---")
                    st.markdown(f"**Status Validasi Item Ini:** {render_status_text(result_row['status'])}")

            # ═══ TAB 4: VALIDATION ═════════════════════════════
            with tab4:
                st.markdown("#### Checklist Validasi")

                reasoning_list = st.session_state.drawer_reasoning
                if not reasoning_list and result_row:
                    with st.spinner("Memuat reasoning..."):
                        _cands_t4 = generate_placeholder_candidates(item_dict)
                        _bsc4, _brs4 = -1, []
                        for c in _cands_t4:
                            ev = run_reasoning(item_dict, c)
                            sc = ev["candidate_evaluation"]["match_score"]
                            if sc > _bsc4:
                                _bsc4 = sc
                                _brs4 = ev["candidate_evaluation"]["reasoning"]
                        reasoning_list = _brs4
                        st.session_state.drawer_reasoning = reasoning_list

                # Build reasoning lookup
                r_lookup: dict = {}
                for r in reasoning_list:
                    r_type = r.get("type", "")
                    r_stat = str(r.get("status", "")).lower()
                    if r_stat in ("match", "pass", "valid", "equivalent"):
                        r_lookup[r_type] = ("\u2705 Pass",   r.get("notes", ""))
                    elif r_stat in ("partial", "review", "partial_match", "close"):
                        r_lookup[r_type] = ("⚠️ Review", r.get("notes", ""))
                    elif r_stat in ("mismatch", "fail", "invalid"):
                        r_lookup[r_type] = ("❌ Fail",   r.get("notes", ""))
                    else:
                        r_lookup[r_type] = ("◽ N/A",    r.get("notes", ""))

                CHECKLIST_ITEMS = [
                    ("function_match",              "⚙️",  "Function Match"),
                    ("dimension_match",             "📐",  "Size / Dimension Match"),
                    ("material_equivalence",        "🔩",  "Material Match"),
                    ("industrial_vs_consumer_grade","🏭",  "Brand / Grade Equivalence"),
                    ("quantity_or_unit",            "📦",  "Unit Match"),
                    ("vendor_location",             "📍",  "Vendor Location Match"),
                ]

                check_rows = []
                for r_type, icon, label in CHECKLIST_ITEMS:
                    status_lbl, notes = r_lookup.get(r_type, ("◽ N/A", ""))
                    check_rows.append({
                        "Kriteria":  f"{icon}  {label}",
                        "Status":    status_lbl,
                        "Catatan":   notes[:100] if notes else "—",
                    })

                check_df = pd.DataFrame(check_rows)
                st.dataframe(
                    check_df, use_container_width=True, hide_index=True,
                    column_config={
                        "Kriteria":  st.column_config.TextColumn("Kriteria",  width="medium"),
                        "Status":    st.column_config.TextColumn("Status",    width="small"),
                        "Catatan":   st.column_config.TextColumn("Catatan",   width="large"),
                    },
                )

                # Verdict
                st.markdown("---")
                st.markdown("#### Verdict")
                if val_status in ("VALID", "MATCH"):
                    st.success(f"✅ **VALID** — Skor kecocokan {score_pct}%. Item sesuai dengan referensi internal. Dapat diproses lebih lanjut.")
                elif val_status == "PARTIAL_MATCH":
                    st.warning(f"⚠️ **PARTIAL MATCH** — Skor {score_pct}%. Terdapat deviasi minor. Perlu review sebelum diproses.")
                elif val_status != "BELUM_DIVALIDASI":
                    st.error(f"❌ **TIDAK VALID** — Skor {score_pct}%. Tidak ada referensi yang cocok. Wajib review manual.")
                else:
                    st.info("⏳ Belum divalidasi. Klik **✅ Run Validation** di atas untuk memulai.")

                if result_row:
                    st.markdown(render_score_bar(result_row["score"], "Skor Kecocokan Keseluruhan"), unsafe_allow_html=True)

                # Reasoning detail
                if reasoning_list:
                    st.markdown("---")
                    st.markdown("#### Analisis Reasoning AI")
                    render_reasoning_cards(reasoning_list)

                if result_row and result_row.get("deviation_notes"):
                    st.markdown("---")
                    st.warning(f"⚠️ **Catatan Deviasi:** {result_row['deviation_notes']}")

            # ═══ TAB 5: JUSTIFICATION ═════════════════════════
            with tab5:
                if not result_row:
                    st.info("⏳ Jalankan validasi terlebih dahulu untuk menghasilkan justifikasi.")
                else:
                    st.markdown("#### Justifikasi Pengadaan")
                    justification_text = generate_justification_text(item_dict, result_row)
                    st.markdown(
                        f'<div class="justification-preview"><pre style="white-space:pre-wrap;font-family:\'Inter\',monospace;font-size:0.82rem;color:#CBD5E1;margin:0;">'
                        f'{justification_text}</pre></div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("---")
                    jcol1, jcol2, jcol3 = st.columns(3)
                    with jcol1:
                        docx_bytes = generate_justification_docx(item_dict, result_row)
                        if docx_bytes:
                            safe_nm = str(selected_name)[:40].replace(" ", "_").replace("/", "-")
                            st.download_button(
                                "📥 Download Justifikasi (.docx)",
                                data=docx_bytes,
                                file_name=f"justifikasi_{safe_nm}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True,
                            )
                        else:
                            st.info("ℹ️ Instal `python-docx` untuk ekspor .docx")
                    with jcol2:
                        st.download_button(
                            "📥 Download Justifikasi (.txt)",
                            data=justification_text.encode("utf-8"),
                            file_name=f"justifikasi_{str(selected_name)[:40].replace(' ','_')}.txt",
                            mime="text/plain",
                            use_container_width=True,
                        )
                    with jcol3:
                        # Single-item CSV export — enriched with SHBJ comparison data
                        try:
                            _shbj_m = find_shbj_match(
                                item_name=selected_name,
                                item_spec=str(item_dict.get("spesifikasi") or item_dict.get("Spesifikasi") or ""),
                                item_satuan=str(item_dict.get("satuan") or item_dict.get("Satuan") or ""),
                                item_kategori=str(item_dict.get("kategori") or item_dict.get("Kategori") or ""),
                                shbj_df=st.session_state.shbj_df,
                            )
                            _csv_row = {
                                "ID": item_dict.get("id_item") or item_dict.get("ID") or "N/A",
                                "Nama Barang": selected_name,
                                "Kategori": item_dict.get("kategori") or item_dict.get("Kategori") or "N/A",
                                "Satuan": item_dict.get("satuan") or item_dict.get("Satuan") or "N/A",
                                "Harga Pengadaan": format_currency_full(item_dict.get("harga_satuan") or item_dict.get("Harga Satuan") or 0),
                                "Harga SHBJ 2025": format_currency_full(_shbj_m.get("est_harga_2025") or _shbj_m.get("harga_satuan_shbj") or 0) if _shbj_m else "N/A",
                                "Status Validasi": result_row.get("status", "N/A"),
                                "Confidence Score": f"{round(float(result_row.get('score', 0)) * 100)}%",
                                "Vendor Pembanding": result_row.get("vendor", "N/A"),
                                "Produk Pembanding": result_row.get("comparison_product", "N/A"),
                                "Catatan Deviasi": result_row.get("deviation_notes", ""),
                            }
                            _csv_data = pd.DataFrame([_csv_row]).to_csv(index=False, encoding="utf-8")
                            st.download_button(
                                "📊 Download Data Item (.csv)",
                                data=_csv_data.encode("utf-8"),
                                file_name=f"item_{str(selected_name)[:30].replace(' ', '_')}.csv",
                                mime="text/csv",
                                use_container_width=True,
                            )
                        except Exception:
                            # Fallback: plain result_row CSV
                            st.download_button(
                                "📊 Download Data Item (.csv)",
                                data=pd.DataFrame([result_row]).to_csv(index=False).encode("utf-8"),
                                file_name=f"item_{str(selected_name)[:30].replace(' ', '_')}.csv",
                                mime="text/csv",
                                use_container_width=True,
                            )


# ============================================================
# PAGE: Vendor History
# ============================================================

elif page == "🏢 Vendor History":
    if not st.session_state.proc_df.empty:
        proc_df = st.session_state.proc_df
        nama_col = get_nama_col(proc_df)
        if nama_col in proc_df.columns:
            item_names = proc_df[nama_col].dropna().unique().tolist()
        else:
            item_names = proc_df.index.tolist()

        # Use selected item from procurement page if available
        default_idx = 0
        if st.session_state.selected_item_name and st.session_state.selected_item_name in item_names:
            default_idx = item_names.index(st.session_state.selected_item_name)

        selected_name = st.selectbox("📋 Pilih Item", item_names, index=default_idx, key="item_detail_select")

        if selected_name:
            # Get item row
            if nama_col in proc_df.columns:
                item_row = proc_df[proc_df[nama_col] == selected_name].iloc[0]
            else:
                item_row = proc_df.loc[selected_name]

            item_dict = item_row.to_dict()

            id_val = item_dict.get("id_item") or item_dict.get("ID") or "N/A"
            kat_val = item_dict.get("Kategori") or item_dict.get("kategori") or "N/A"
            subkat_val = item_dict.get("Sub kategori") or item_dict.get("subkategori") or "N/A"
            sat_val = item_dict.get("Satuan") or item_dict.get("satuan") or "N/A"
            harga_val = item_dict.get("Harga Satuan") or item_dict.get("harga_satuan") or "N/A"

            # Get validation result for this item
            result_row = None
            if st.session_state.validation_run and not st.session_state.result_df.empty and 'status' in st.session_state.result_df.columns:
                res_match = st.session_state.result_df[st.session_state.result_df['nama_barang'] == selected_name]
                if not res_match.empty:
                    result_row = res_match.iloc[0].to_dict()

            # --- Item Header ---
            status_html = render_status_badge(result_row['status']) if result_row else '<span class="status-badge neutral">◽ Belum Divalidasi</span>'

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(26, 39, 66, 0.6), rgba(14, 26, 46, 0.8)); border: 1px solid rgba(30, 58, 95, 0.4); border-radius: 14px; padding: 24px 28px; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px;">
                    <span style="color: #94A3B8; font-size: 0.72rem; background: rgba(30, 58, 95, 0.5); padding: 3px 10px; border-radius: 6px;">ID: {id_val}</span>
                    <span style="color: #94A3B8; font-size: 0.72rem; background: rgba(30, 58, 95, 0.5); padding: 3px 10px; border-radius: 6px;">📁 {kat_val}</span>
                    {status_html}
                </div>
                <div style="color: #F1F5F9; font-size: 1.2rem; font-weight: 700; margin-bottom: 16px; line-height: 1.4;">
                    {selected_name}
                </div>
                <div style="display: flex; gap: 24px; flex-wrap: wrap;">
                    <div>
                        <span style="color: #64748B; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em;">Harga Satuan</span>
                        <div style="color: #FBBF24; font-size: 1.2rem; font-weight: 700;">{format_currency_full(harga_val)}</div>
                    </div>
                    <div>
                        <span style="color: #64748B; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em;">Satuan</span>
                        <div style="color: #CBD5E1; font-size: 1rem; font-weight: 500;">{sat_val}</div>
                    </div>
                    <div>
                        <span style="color: #64748B; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em;">Sub Kategori</span>
                        <div style="color: #CBD5E1; font-size: 1rem; font-weight: 500;">{subkat_val}</div>
                    </div>
                    <div>
                        <span style="color: #64748B; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em;">Skor</span>
                        <div style="color: #14B8A6; font-size: 1rem; font-weight: 700;">{f"{result_row['score']:.0%}" if result_row else "—"}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- Tabs ---
            t1, t2, t3, t4, t5 = st.tabs([
                "📋 Overview",
                "🤖 Analisis AI",
                "📊 Riwayat Anggaran SHBJ 2025",
                "🏢 Riwayat Vendor",
                "📄 Ekspor Justifikasi",
            ])

            # ---- TAB 1: Overview ----
            with t1:
                col_a, col_b = st.columns(2)
                with col_a:
                    render_info_card("Konteks Pengadaan", "Pembelian rutin operasional pemerintah daerah")
                    render_info_card("Fungsi Bisnis", "Operasional & Dukungan Kegiatan")
                    render_info_card("Sumber Anggaran", "APBD DKI Jakarta — SHBJ 2025")
                with col_b:
                    render_info_card("Kriteria Validasi", "Kewajaran harga, ketersediaan vendor, kecocokan spesifikasi")
                    render_info_card("Spesifikasi Kritis", "Mengikuti standar LKPP / Internal SHBJ DKI Jakarta")
                    render_info_card("Prioritas Pencocokan", "Fungsi → Spesifikasi Teknis → Ukuran → Material → Satuan → Harga")

                if result_row:
                    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
                    st.markdown(render_score_bar(result_row["score"], "Skor Kecocokan AI"), unsafe_allow_html=True)

            # ---- TAB 2: AI Analysis ----
            with t2:
                if not st.session_state.validation_run or result_row is None:
                    st.warning("⏳ Validasi belum dijalankan. Klik **Jalankan Validasi AI** di halaman Dashboard.")
                else:
                    # Candidate card
                    render_candidate_card(result_row)

                    # Score bar
                    st.markdown(render_score_bar(result_row["score"], "Skor Kecocokan Keseluruhan"), unsafe_allow_html=True)

                    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

                    # Reasoning breakdown
                    st.markdown("#### 🧠 Analisis Reasoning AI")

                    # Re-run reasoning to get detailed breakdown (since result_df only stores summary)
                    item_for_reasoning = item_dict.copy()
                    if "Nama Barang dan Spesifikasi" in item_for_reasoning and "nama_barang" not in item_for_reasoning:
                        item_for_reasoning["nama_barang"] = item_for_reasoning["Nama Barang dan Spesifikasi"]
                    if "Kategori" in item_for_reasoning and "kategori" not in item_for_reasoning:
                        item_for_reasoning["kategori"] = item_for_reasoning["Kategori"]
                    if "Satuan" in item_for_reasoning and "satuan" not in item_for_reasoning:
                        item_for_reasoning["satuan"] = item_for_reasoning["Satuan"]

                    raw_nama = str(item_for_reasoning.get("nama_barang", ""))
                    if "Spesifikasi:" in raw_nama and not item_for_reasoning.get("spesifikasi"):
                        parts = raw_nama.split("Spesifikasi:", 1)
                        item_for_reasoning["nama_barang"] = parts[0].strip()
                        item_for_reasoning["spesifikasi"] = parts[1].strip()

                    candidates = generate_placeholder_candidates(item_for_reasoning)
                    best_reasoning = []
                    best_score = -1
                    for c in candidates:
                        eval_result = run_reasoning(item_for_reasoning, c)
                        s = eval_result["candidate_evaluation"]["match_score"]
                        if s > best_score:
                            best_score = s
                            best_reasoning = eval_result["candidate_evaluation"]["reasoning"]

                    render_reasoning_cards(best_reasoning)

                    # Deviation notes
                    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
                    if result_row.get("deviation_notes"):
                        st.markdown("#### ⚠️ Catatan Deviasi")
                        st.warning(result_row["deviation_notes"])

            # ---- TAB 3: SHBJ 2025 Budget History ----
            with t3:
                st.markdown("#### 📊 Riwayat Anggaran 2025 — Data Riil SHBJ DKI Jakarta")
                st.caption("Selain validasi pembanding, sistem membandingkan item dengan histori SHBJ 2025 untuk menilai kewajaran harga dan mendukung justifikasi pengadaan.")

                # Parse current procurement price
                try:
                    harga_numeric = float(pd.to_numeric(harga_val, errors='coerce'))
                    if pd.isna(harga_numeric):
                        harga_numeric = None
                except (ValueError, TypeError):
                    harga_numeric = None

                # Get spec from item dict
                item_spec = str(item_dict.get("Spesifikasi") or item_dict.get("spesifikasi") or "")
                item_satuan_raw = str(sat_val) if sat_val != "N/A" else ""
                item_kat_raw = str(kat_val) if kat_val != "N/A" else ""

                # Search SHBJ 2025
                shbj_match = find_shbj_match(
                    item_name=selected_name,
                    item_spec=item_spec,
                    item_satuan=item_satuan_raw,
                    item_kategori=item_kat_raw,
                    shbj_df=st.session_state.shbj_df,
                )

                if shbj_match:
                    harga_shbj_ref = shbj_match.get("harga_satuan_shbj")
                    harga_est_2025 = shbj_match.get("est_harga_2025")
                    # Prefer est_harga_2025 as the canonical SHBJ 2025 price
                    harga_shbj = harga_est_2025 if harga_est_2025 else harga_shbj_ref
                    match_type_label = {
                        "exact_name_spec": "✅ Kecocokan nama + spesifikasi",
                        "exact_name": "🔎 Kecocokan nama",
                        "category_fallback": "📂 Fallback kategori",
                    }.get(shbj_match.get("match_type", ""), "🔎 Kecocokan")

                    # Compute delta vs current procurement price
                    if harga_numeric and harga_shbj:
                        selisih = harga_numeric - harga_shbj
                        perubahan_pct = (selisih / harga_shbj) * 100
                        selisih_str = format_currency_full(abs(selisih))
                        selisih_sign = "+" if selisih >= 0 else "-"
                        perubahan_str = f"{perubahan_pct:+.2f}%"
                        color_delta = "#EF4444" if selisih > 0 else "#10B981"
                    else:
                        selisih = None
                        selisih_str = "N/A"
                        perubahan_str = "N/A"
                        selisih_sign = ""
                        color_delta = "#94A3B8"

                    # --- Comparison Card ---
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, rgba(13,148,136,0.08), rgba(26,39,66,0.6));
                                border: 1px solid rgba(13,148,136,0.25); border-radius: 12px;
                                padding: 20px 24px; margin-bottom: 16px;">
                        <div style="color: #14B8A6; font-size: 0.72rem; font-weight: 600;
                                    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 12px;
                                    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                            📚 Riwayat Anggaran SHBJ 2025 &nbsp;|&nbsp;
                            <span style="color: #94A3B8; font-weight: 400;">{match_type_label}</span>
                            {(
                                '<span class="kewajaran-chip wajar">✅ Harga Wajar</span>'
                                if selisih is not None and abs(perubahan_pct) <= 5
                                else '<span class="kewajaran-chip perhatian">⚠️ Perlu Perhatian</span>'
                                if selisih is not None and abs(perubahan_pct) <= 15
                                else '<span class="kewajaran-chip deviasi">❌ Deviasi Signifikan</span>'
                                if selisih is not None
                                else ''
                            )}
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <div style="color: #64748B; font-size: 0.7rem; text-transform: uppercase;
                                            letter-spacing: 0.05em; margin-bottom: 4px;">Harga SHBJ 2025</div>
                                <div style="color: #F1F5F9; font-size: 1.15rem; font-weight: 700;">
                                    {format_currency_full(harga_shbj) if harga_shbj else 'N/A'}
                                </div>
                                <div style="color: #64748B; font-size: 0.7rem; margin-top: 2px;">
                                    {('Ref: ' + format_currency_full(harga_shbj_ref)) if harga_shbj_ref and harga_shbj_ref != harga_shbj else ''}
                                </div>
                            </div>
                            <div>
                                <div style="color: #64748B; font-size: 0.7rem; text-transform: uppercase;
                                            letter-spacing: 0.05em; margin-bottom: 4px;">Harga Pengadaan Saat Ini</div>
                                <div style="color: #FBBF24; font-size: 1.15rem; font-weight: 700;">
                                    {format_currency_full(harga_numeric) if harga_numeric else 'N/A'}
                                </div>
                            </div>
                            <div>
                                <div style="color: #64748B; font-size: 0.7rem; text-transform: uppercase;
                                            letter-spacing: 0.05em; margin-bottom: 4px;">Selisih</div>
                                <div style="color: {color_delta}; font-size: 1.1rem; font-weight: 700;">
                                    {selisih_sign + selisih_str if selisih is not None else 'N/A'}
                                </div>
                            </div>
                            <div>
                                <div style="color: #64748B; font-size: 0.7rem; text-transform: uppercase;
                                            letter-spacing: 0.05em; margin-bottom: 4px;">Perubahan</div>
                                <div style="color: {color_delta}; font-size: 1.1rem; font-weight: 700;">
                                    {perubahan_str}
                                </div>
                            </div>
                        </div>
                        <div style="border-top: 1px solid rgba(30,58,95,0.3); padding-top: 12px;
                                    display: flex; gap: 20px; flex-wrap: wrap;">
                            <div>
                                <span style="color: #64748B; font-size: 0.7rem;">Nama SHBJ:</span>
                                <span style="color: #CBD5E1; font-size: 0.8rem; margin-left: 6px;">{shbj_match.get('shbj_nama', 'N/A')}</span>
                            </div>
                            <div>
                                <span style="color: #64748B; font-size: 0.7rem;">Spesifikasi:</span>
                                <span style="color: #CBD5E1; font-size: 0.8rem; margin-left: 6px;">{shbj_match.get('shbj_spesifikasi', 'N/A')[:80]}</span>
                            </div>
                            <div>
                                <span style="color: #64748B; font-size: 0.7rem;">Satuan:</span>
                                <span style="color: #CBD5E1; font-size: 0.8rem; margin-left: 6px;">{shbj_match.get('shbj_satuan', 'N/A')}</span>
                            </div>
                            <div>
                                <span style="color: #64748B; font-size: 0.7rem;">Status:</span>
                                <span style="color: #CBD5E1; font-size: 0.8rem; margin-left: 6px;">{shbj_match.get('keterangan', 'N/A')}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # --- Comparison Chart ---
                    if harga_shbj and harga_numeric:
                        st.markdown("#### 📈 Perbandingan Harga")
                        chart_compare = pd.DataFrame({
                            "Label": ["Harga SHBJ 2025", "Harga Pengadaan"],
                            "Harga (Rp)": [harga_shbj, harga_numeric],
                        }).set_index("Label")
                        st.bar_chart(chart_compare, color="#0D9488")

                    # --- Waiver assessment ---
                    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
                    if selisih is not None and harga_shbj:
                        if abs(perubahan_pct) <= 5:
                            st.success(f"✅ **Harga Wajar** — Deviasi {perubahan_str} dari SHBJ 2025, dalam batas toleransi (≤5%).")
                        elif abs(perubahan_pct) <= 15:
                            st.warning(f"⚠️ **Perlu Perhatian** — Deviasi {perubahan_str} dari SHBJ 2025. Pastikan ada justifikasi yang memadai.")
                        else:
                            st.error(f"❌ **Deviasi Signifikan** — Harga pengadaan berbeda {perubahan_str} dari SHBJ 2025. Wajib review dan justifikasi khusus.")

                    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
                    st.caption(f"📋 Sumber: SHBJ DKI Jakarta 2025 — ID {shbj_match.get('shbj_id', 'N/A')} | Kategori: {shbj_match.get('shbj_kategori', 'N/A')}")

                else:
                    st.info("ℹ️ **Tidak ditemukan histori anggaran 2025.** Item ini belum ada padanannya dalam data SHBJ DKI Jakarta 2025.")
                    # Still show mock historical trend as supplementary context
                    if harga_numeric:
                        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
                        st.markdown("#### 📈 Tren Anggaran Estimasi (Mock)")
                        st.caption("Data historis estimasi — belum ditemukan data riil SHBJ 2025 untuk item ini.")
                        history = get_budget_history(selected_name, harga_numeric)
                        hist_df = pd.DataFrame(history)
                        chart_df = hist_df[["tahun", "harga_satuan"]].copy()
                        chart_df["tahun"] = chart_df["tahun"].astype(str)
                        chart_df = chart_df.set_index("tahun")
                        chart_df.columns = ["Harga Satuan (Rp)"]
                        st.line_chart(chart_df, color="#F59E0B")

            # ---- TAB 4: Vendor History ----
            with t4:
                st.markdown("#### 🏢 Riwayat Vendor")

                vendor_info = get_vendor_for_item(selected_name)

                # Override with validation result vendor if available
                if result_row and result_row.get("vendor") and result_row["vendor"] != "N/A":
                    vendor_info["nama"] = result_row["vendor"]

                # Vendor details card
                st.markdown(f"""
                <div class="vendor-card fade-in">
                    <div class="vc-name">🏢 {vendor_info['nama']}</div>
                    <div class="vc-location">📍 {vendor_info['lokasi']} &nbsp;|&nbsp; NPWP: {vendor_info['npwp']}</div>
                    <div class="vc-stats">
                        <div class="vc-stat">
                            <span class="vc-stat-label">Email</span>
                            <span class="vc-stat-value" style="font-size: 0.8rem;">{vendor_info['email']}</span>
                        </div>
                        <div class="vc-stat">
                            <span class="vc-stat-label">Kontak</span>
                            <span class="vc-stat-value" style="font-size: 0.8rem;">{vendor_info['kontak']}</span>
                        </div>
                        <div class="vc-stat">
                            <span class="vc-stat-label">Kategori</span>
                            <span class="vc-stat-value" style="font-size: 0.8rem;">{vendor_info['kategori']}</span>
                        </div>
                        <div class="vc-stat">
                            <span class="vc-stat-label">Reliabilitas</span>
                            <span class="vc-stat-value">{vendor_info['reliability']}%</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

                # Transaction history
                st.markdown("#### 📜 Riwayat Transaksi")
                transactions = get_vendor_transactions(vendor_info["nama"])
                if transactions:
                    tx_df = pd.DataFrame(transactions)
                    tx_df["harga_formatted"] = tx_df["harga_satuan"].apply(format_currency_full)
                    tx_df["total_formatted"] = tx_df["total_nilai"].apply(format_currency)

                    st.dataframe(
                        tx_df[["tahun", "nama_barang", "harga_formatted", "satuan", "jumlah", "total_formatted", "status_kontrak", "lokasi"]].rename(columns={
                            "tahun": "Tahun",
                            "nama_barang": "Nama Barang",
                            "harga_formatted": "Harga Satuan",
                            "satuan": "Satuan",
                            "jumlah": "Qty",
                            "total_formatted": "Total Nilai",
                            "status_kontrak": "Status",
                            "lokasi": "Lokasi",
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Tidak ada riwayat transaksi tercatat.")

                # Validation status
                if result_row:
                    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
                    st.markdown(f"**Status Validasi Item Ini:** {render_status_text(result_row['status'])}")

            # ---- TAB 5: Export Justification ----
            with t5:
                if not st.session_state.validation_run or result_row is None:
                    st.warning("⏳ Jalankan validasi terlebih dahulu untuk menghasilkan justifikasi.")
                else:
                    st.markdown("#### 📄 Preview Justifikasi Pengadaan")

                    justification_text = generate_justification_text(item_dict, result_row)

                    st.markdown(f"""
                    <div class="justification-preview">
                        <pre style="white-space: pre-wrap; font-family: 'Inter', monospace; font-size: 0.82rem; color: #CBD5E1; margin: 0;">{justification_text}</pre>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

                    col_exp1, col_exp2, col_exp3 = st.columns(3)

                    with col_exp1:
                        # Try DOCX export
                        docx_bytes = generate_justification_docx(item_dict, result_row)
                        if docx_bytes:
                            safe_name = str(selected_name)[:40].replace(" ", "_").replace("/", "-")
                            st.download_button(
                                label="📥 Download Justifikasi (.docx)",
                                data=docx_bytes,
                                file_name=f"justifikasi_{safe_name}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True,
                            )
                        else:
                            st.info("ℹ️ Instal `python-docx` untuk ekspor .docx")

                    with col_exp2:
                        # Text fallback
                        st.download_button(
                            label="📥 Download Justifikasi (.txt)",
                            data=justification_text.encode("utf-8"),
                            file_name=f"justifikasi_{str(selected_name)[:40].replace(' ', '_')}.txt",
                            mime="text/plain",
                            use_container_width=True,
                        )

                    with col_exp3:
                        # CSV single-item export
                        try:
                            shbj_m = find_shbj_match(
                                item_name=selected_name,
                                item_spec=str(item_dict.get("spesifikasi") or item_dict.get("Spesifikasi") or ""),
                                item_satuan=str(item_dict.get("satuan") or item_dict.get("Satuan") or ""),
                                item_kategori=str(item_dict.get("kategori") or item_dict.get("Kategori") or ""),
                                shbj_df=st.session_state.shbj_df,
                            )
                            csv_row = {
                                "ID": item_dict.get("id_item") or item_dict.get("ID") or "N/A",
                                "Nama Barang": selected_name,
                                "Kategori": item_dict.get("kategori") or item_dict.get("Kategori") or "N/A",
                                "Satuan": item_dict.get("satuan") or item_dict.get("Satuan") or "N/A",
                                "Harga Pengadaan": format_currency_full(item_dict.get("harga_satuan") or item_dict.get("Harga Satuan") or 0),
                                "Harga SHBJ 2025": format_currency_full(shbj_m.get("est_harga_2025") or shbj_m.get("harga_satuan_shbj") or 0) if shbj_m else "N/A",
                                "Status Validasi": result_row.get("status", "N/A"),
                                "Confidence Score": f"{round(float(result_row.get('score', 0)) * 100)}%",
                                "Vendor": result_row.get("vendor", "N/A"),
                                "Catatan Deviasi": result_row.get("deviation_notes", ""),
                            }
                            csv_single = pd.DataFrame([csv_row]).to_csv(index=False, encoding="utf-8")
                            st.download_button(
                                label="📊 Download Data Item (.csv)",
                                data=csv_single.encode("utf-8"),
                                file_name=f"item_{str(selected_name)[:30].replace(' ', '_')}.csv",
                                mime="text/csv",
                                use_container_width=True,
                            )
                        except Exception:
                            st.download_button(
                                label="📊 Download Data Item (.csv)",
                                data=pd.DataFrame([result_row]).to_csv(index=False).encode("utf-8"),
                                file_name=f"item_{str(selected_name)[:30].replace(' ', '_')}.csv",
                                mime="text/csv",
                                use_container_width=True,
                            )



# ============================================================
# PAGE: Vendor History
# ============================================================

elif page == "🏢 Vendor History":
    render_page_header("🏢", "Vendor History", "Profil vendor dan riwayat transaksi pengadaan")

    if not st.session_state.validation_run or st.session_state.result_df.empty or 'status' not in st.session_state.result_df.columns:
        st.info("⏳ Jalankan validasi untuk melihat riwayat vendor dari data pengadaan Anda.")

        # Show mock vendor registry as preview
        st.markdown("#### 📋 Vendor Registry (Database Internal)")
        for v in MOCK_VENDORS[:4]:
            render_vendor_card(v)
    else:
        res_df = st.session_state.result_df

        # Build vendor summaries
        vendor_summaries = get_vendor_summary(res_df)

        if vendor_summaries:
            # Summary metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Vendor", len(vendor_summaries))
            total_val = sum(v.get("total_nilai", 0) for v in vendor_summaries)
            c2.metric("Total Nilai Transaksi", format_currency(total_val))
            avg_rel = sum(v.get("reliability", 0) for v in vendor_summaries) / len(vendor_summaries)
            c3.metric("Rata-rata Reliabilitas", f"{avg_rel:.0f}%")

            st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

            # Vendor cards
            st.markdown("#### 🏢 Profil Vendor")
            for vendor in vendor_summaries:
                render_vendor_card(vendor)

                # Expandable transaction detail
                with st.expander(f"📜 Riwayat Transaksi — {vendor['nama']}"):
                    transactions = get_vendor_transactions(vendor["nama"])
                    if transactions:
                        tx_df = pd.DataFrame(transactions)
                        tx_df["harga_formatted"] = tx_df["harga_satuan"].apply(format_currency_full)
                        st.dataframe(
                            tx_df[["tahun", "nama_barang", "harga_formatted", "satuan", "jumlah", "status_kontrak"]].rename(columns={
                                "tahun": "Tahun",
                                "nama_barang": "Nama Barang",
                                "harga_formatted": "Harga",
                                "satuan": "Satuan",
                                "jumlah": "Qty",
                                "status_kontrak": "Status",
                            }),
                            use_container_width=True,
                            hide_index=True,
                        )

            st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

            # Vendor comparison chart
            st.markdown("#### 📊 Perbandingan Vendor — Item Dipasok")
            vendor_chart = pd.DataFrame({
                "Vendor": [v["nama"][:25] for v in vendor_summaries],
                "Item Dipasok": [v.get("items_supplied", 0) for v in vendor_summaries],
            })
            vendor_chart = vendor_chart.set_index("Vendor")
            st.bar_chart(vendor_chart, color="#F59E0B")
        else:
            st.info("Tidak ada data vendor ditemukan.")


# ============================================================
# PAGE: Validation Results
# ============================================================

elif page == "📈 Validation Results":
    render_page_header("📈", "Validation Results", "Ringkasan lengkap hasil validasi AI")

    if not st.session_state.validation_run:
        st.info("⏳ Validasi belum dijalankan. Jalankan validasi di Dashboard atau Procurement Items.")
    else:
        res_df = st.session_state.result_df

        # ── KPIs ────────────────────────────────────────────
        total_val    = len(res_df)
        valid_count  = len(res_df[res_df['status'].isin(['MATCH', 'VALID'])]) if 'status' in res_df.columns else 0
        partial_count = len(res_df[res_df['status'] == 'PARTIAL_MATCH']) if 'status' in res_df.columns else 0
        invalid_count = total_val - valid_count - partial_count
        avg_score     = res_df['score'].mean() if 'score' in res_df.columns else 0

        kc1, kc2, kc3, kc4, kc5 = st.columns(5)
        kc1.metric("Total Divalidasi", total_val)
        kc2.metric("✅ Valid",          valid_count)
        kc3.metric("⚠️ Partial",       partial_count)
        kc4.metric("❌ Need Review",   invalid_count)
        kc5.metric("Avg Confidence",   f"{avg_score:.0%}")

        st.divider()

        # ── Charts ───────────────────────────────────────────
        ch1, ch2 = st.columns(2)
        with ch1:
            st.subheader("Distribusi Status")
            dist_data = pd.DataFrame({
                "Status":  ["Valid", "Partial", "Need Review"],
                "Jumlah": [valid_count, partial_count, invalid_count],
            }).set_index("Status")
            st.bar_chart(dist_data, color="#14B8A6")
        with ch2:
            st.subheader("Distribusi Confidence Score")
            if 'score' in res_df.columns:
                score_bins = pd.cut(
                    pd.to_numeric(res_df['score'], errors='coerce').dropna() * 100,
                    bins=[0, 40, 70, 100],
                    labels=["Low (0-40%)", "Medium (40-70%)", "High (70-100%)"]
                ).value_counts().sort_index()
                st.bar_chart(score_bins.rename("Jumlah Item"), color="#F59E0B")
            else:
                st.info("Data score tidak tersedia.")

        st.divider()

        # ── Filters & Table ───────────────────────────────
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if 'status' in res_df.columns:
                res_statuses = ["Semua"] + list(res_df['status'].unique())
                res_status_filter = st.selectbox("Filter Status", res_statuses, key="val_status_filter")
            else:
                res_status_filter = "Semua"
        with col_f2:
            sort_by = st.selectbox("Urutkan", [
                "Score (Tinggi → Rendah)", "Score (Rendah → Tinggi)", "Nama Barang"
            ], key="val_sort")

        display_df = res_df.copy()
        if res_status_filter != "Semua":
            display_df = display_df[display_df['status'] == res_status_filter]
        if sort_by == "Score (Tinggi → Rendah)" and 'score' in display_df.columns:
            display_df = display_df.sort_values('score', ascending=False)
        elif sort_by == "Score (Rendah → Tinggi)" and 'score' in display_df.columns:
            display_df = display_df.sort_values('score', ascending=True)
        elif sort_by == "Nama Barang" and 'nama_barang' in display_df.columns:
            display_df = display_df.sort_values('nama_barang')

        display_fmt = display_df.copy()
        if 'harga_satuan' in display_fmt.columns:
            display_fmt['harga_satuan'] = display_fmt['harga_satuan'].apply(
                lambda x: format_currency_full(x) if pd.notna(x) else "N/A")
        if 'comparison_price' in display_fmt.columns:
            display_fmt['comparison_price'] = display_fmt['comparison_price'].apply(
                lambda x: format_currency_full(x) if pd.notna(x) else "N/A")

        st.caption(f"Menampilkan **{len(display_fmt)}** hasil")
        st.dataframe(display_fmt, use_container_width=True, hide_index=True, height=400)

        st.divider()

        # ── Export ────────────────────────────────────────
        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                "📥 Download Hasil Validasi (CSV)",
                data=res_df.to_csv(index=False).encode('utf-8'),
                file_name="sipval_validation_results.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with dl2:
            summary_txt = (
                f"SIPVAL — Ringkasan Hasil Validasi\n{'='*50}\n"
                f"Total Divalidasi  : {total_val}\n"
                f"Valid (MATCH)     : {valid_count}\n"
                f"Partial Match     : {partial_count}\n"
                f"Need Review       : {invalid_count}\n"
                f"Rata-rata Score   : {avg_score:.2f}\n"
                f"{'='*50}\nDihasilkan oleh SIPVAL v1.0\n"
            )
            st.download_button(
                "📥 Download Ringkasan (TXT)",
                data=summary_txt.encode("utf-8"),
                file_name="sipval_summary_report.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with st.expander("📐 Referensi Aturan Validasi"):
            st.markdown("""
            **Prioritas pencocokan validasi (urut dari tertinggi):**
            1. **Fungsi** — Apakah fungsi utama barang sama?
            2. **Spesifikasi Teknis** — Dimensi, kapasitas, parameter teknis.
            3. **Ukuran** — Ukuran/dimensi fisik sesuai.
            4. **Material** — Material/bahan setara.
            5. **Brand Equivalence** — Merek setara secara kualitas.
            6. **Satuan** — Satuan pengukuran sama.
            7. **Harga** — Harga bukan faktor utama pencocokan.
            """)


# ============================================================
# Footer
# ============================================================

st.markdown("""
<div class="sipval-footer">
    SIPVAL v1.0 — Sistem Validasi Pengadaan &nbsp;|&nbsp; AI-Assisted Procurement Validation System<br>
    Demo MVP untuk JuaraVibeCoding — Bukan produksi resmi
</div>
""", unsafe_allow_html=True)
