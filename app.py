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

DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shbj only me.xlsx")

if st.session_state.proc_df.empty and not st.session_state.auto_loaded:
    default_df = load_default_excel(DEFAULT_FILE)
    if not default_df.empty:
        st.session_state.proc_df = default_df
        st.session_state.uploaded_file_name = "shbj only me.xlsx (Auto)"
        st.session_state.auto_loaded = True


# ============================================================
# Sidebar
# ============================================================

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
    ], label_visibility="collapsed")

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
                else:
                    nama_col = "Nama Barang dan Spesifikasi" if "Nama Barang dan Spesifikasi" in df.columns else "nama_barang"
                    if nama_col in df.columns:
                        df = df.dropna(subset=[nama_col])
                    st.session_state.proc_df = df
                    st.session_state.result_df = pd.DataFrame()
                    st.session_state.validation_run = False
                    st.session_state.uploaded_file_name = proc_file.name
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
        c4, c5, c6 = st.columns(3)
        with c4:
            st.markdown(render_kpi_card("❌", "Invalid", str(invalid_count), "perlu review manual", "red"), unsafe_allow_html=True)
        with c5:
            st.markdown(render_kpi_card("📊", "Rata-rata Skor", f"{avg_score:.0%}", "confidence AI", "teal"), unsafe_allow_html=True)
        with c6:
            st.markdown(render_kpi_card("🏢", "Total Vendor", str(total_vendors), f"avg deviasi: {avg_dev}", "gold"), unsafe_allow_html=True)

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
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(render_kpi_card("📦", "Total Item", str(total_items), "dari data pengadaan", "teal"), unsafe_allow_html=True)
        with c2:
            st.markdown(render_kpi_card("⏳", "Status Validasi", "Belum", "jalankan validasi", "amber"), unsafe_allow_html=True)
        with c3:
            st.markdown(render_kpi_card("🤖", "AI Engine", "Ready", "reasoning engine aktif", "green"), unsafe_allow_html=True)

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
    render_page_header("📝", "Procurement Items", "Daftar seluruh item pengadaan dari data yang dimuat")

    if st.session_state.proc_df.empty:
        st.info("📂 Tidak ada data. Upload file pengadaan untuk melihat item.")
    else:
        proc_df = st.session_state.proc_df
        nama_col = get_nama_col(proc_df)
        total = len(proc_df)

        # Summary bar
        if st.session_state.validation_run and not st.session_state.result_df.empty:
            res_df = st.session_state.result_df
            validated = len(res_df)
            needs_review = len(res_df[~res_df['status'].isin(['MATCH', 'VALID'])]) if 'status' in res_df.columns else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Item", total)
            c2.metric("Sudah Divalidasi", validated)
            c3.metric("Perlu Review", needs_review)
        else:
            st.metric("Total Item", total)
            if st.button("🚀 Jalankan Validasi AI", type="primary", key="proc_run_btn"):
                with st.spinner("⏳ Menjalankan validasi AI..."):
                    run_validation_logic()
                st.rerun()

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

        # Filters
        col_search, col_filter = st.columns(2)
        with col_search:
            search_query = st.text_input("🔍 Cari berdasarkan nama item", placeholder="Ketik nama barang...")
        with col_filter:
            status_filter = "Semua"
            if st.session_state.validation_run and not st.session_state.result_df.empty and 'status' in st.session_state.result_df.columns:
                statuses = ["Semua"] + list(st.session_state.result_df['status'].unique())
                status_filter = st.selectbox("📋 Filter Status", statuses)

        # Build display dataframe
        df_display = proc_df.copy()

        # Apply search
        if search_query and nama_col in df_display.columns:
            df_display = df_display[df_display[nama_col].astype(str).str.contains(search_query, case=False, na=False)]

        # Apply status filter
        if status_filter != "Semua" and st.session_state.validation_run and 'status' in st.session_state.result_df.columns:
            filtered_names = st.session_state.result_df[st.session_state.result_df['status'] == status_filter]['nama_barang'].tolist()
            if nama_col in df_display.columns:
                df_display = df_display[df_display[nama_col].isin(filtered_names)]

        st.markdown(f"**Menampilkan {len(df_display)} dari {total} item**")
        st.dataframe(df_display, use_container_width=True, height=450)

        # Quick navigate to item detail
        if nama_col in proc_df.columns:
            st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
            quick_select = st.selectbox(
                "🔗 Lihat Detail Item",
                ["-- Pilih item --"] + proc_df[nama_col].dropna().unique().tolist(),
                key="quick_nav_select"
            )
            if quick_select != "-- Pilih item --":
                st.session_state.selected_item_name = quick_select
                st.info(f"➡️ Navigasikan ke **🔍 Item Detail** di sidebar untuk melihat detail **{quick_select[:60]}...**")


# ============================================================
# PAGE: Item Detail (MOST IMPORTANT FOR DEMO)
# ============================================================

elif page == "🔍 Item Detail":
    render_page_header("🔍", "Detail Item Pengadaan", "Analisis lengkap per item — AI reasoning, riwayat anggaran, vendor")

    if st.session_state.proc_df.empty:
        st.info("📂 Tidak ada data. Upload file pengadaan untuk melihat detail item.")
    else:
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
                "📊 Riwayat Anggaran",
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

            # ---- TAB 3: Budget History ----
            with t3:
                st.markdown("#### 📊 Riwayat Anggaran (2023 — 2025)")

                try:
                    harga_numeric = float(pd.to_numeric(harga_val, errors='coerce'))
                except (ValueError, TypeError):
                    harga_numeric = None

                if harga_numeric and pd.notna(harga_numeric):
                    history = get_budget_history(selected_name, harga_numeric)
                    hist_df = pd.DataFrame(history)

                    # Display table
                    display_hist = hist_df.copy()
                    display_hist["harga_formatted"] = display_hist["harga_satuan"].apply(format_currency_full)

                    # Calculate YoY delta
                    deltas = ["—"]
                    for i in range(1, len(display_hist)):
                        prev = display_hist.iloc[i-1]["harga_satuan"]
                        curr = display_hist.iloc[i]["harga_satuan"]
                        if prev > 0:
                            pct = ((curr - prev) / prev) * 100
                            deltas.append(f"{pct:+.1f}%")
                        else:
                            deltas.append("N/A")
                    display_hist["delta_yoy"] = deltas

                    st.dataframe(
                        display_hist[["tahun", "harga_formatted", "sumber", "keterangan", "delta_yoy"]].rename(columns={
                            "tahun": "Tahun",
                            "harga_formatted": "Harga Satuan",
                            "sumber": "Sumber",
                            "keterangan": "Keterangan",
                            "delta_yoy": "Delta YoY",
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

                    # Price trend chart
                    st.markdown("#### 📈 Tren Harga 3 Tahun")
                    chart_df = hist_df[["tahun", "harga_satuan"]].copy()
                    chart_df["tahun"] = chart_df["tahun"].astype(str)
                    chart_df = chart_df.set_index("tahun")
                    chart_df.columns = ["Harga Satuan (Rp)"]
                    st.line_chart(chart_df, color="#0D9488")

                    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
                    st.info("📋 **Sumber data:** SHBJ DKI Jakarta (Standar Harga Barang Jasa). Data 2023-2024 merupakan data historis, data 2025 merupakan anggaran aktif.")
                else:
                    st.info("ℹ️ Data harga tidak tersedia untuk item ini.")

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

                    col_exp1, col_exp2 = st.columns(2)

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
        st.info("⏳ Validasi belum dijalankan. Jalankan validasi di halaman Dashboard atau Procurement Items.")
    else:
        res_df = st.session_state.result_df

        # Summary metrics
        total = len(res_df)
        valid_count = len(res_df[res_df['status'].isin(['MATCH', 'VALID'])]) if 'status' in res_df.columns else 0
        partial_count = len(res_df[res_df['status'] == 'PARTIAL_MATCH']) if 'status' in res_df.columns else 0
        invalid_count = total - valid_count - partial_count
        avg_score = res_df['score'].mean() if 'score' in res_df.columns else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Divalidasi", total)
        c2.metric("✅ Valid", valid_count)
        c3.metric("⚠️ Partial", partial_count)
        c4.metric("❌ Invalid", invalid_count)
        c5.metric("Avg Score", f"{avg_score:.0%}")

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

        # Status distribution
        st.subheader("Distribusi Status")
        dist_data = pd.DataFrame({
            "Status": ["Valid", "Partial Match", "Invalid"],
            "Jumlah": [valid_count, partial_count, invalid_count],
        }).set_index("Status")
        st.bar_chart(dist_data, color="#14B8A6")

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            res_status_filter = "Semua"
            if 'status' in res_df.columns:
                res_statuses = ["Semua"] + list(res_df['status'].unique())
                res_status_filter = st.selectbox("Filter Status", res_statuses, key="val_status_filter")
        with col_f2:
            sort_by = st.selectbox("Urutkan", ["Score (Tinggi → Rendah)", "Score (Rendah → Tinggi)", "Nama Barang"], key="val_sort")

        # Apply filters
        display_df = res_df.copy()
        if res_status_filter != "Semua":
            display_df = display_df[display_df['status'] == res_status_filter]

        if sort_by == "Score (Tinggi → Rendah)" and 'score' in display_df.columns:
            display_df = display_df.sort_values('score', ascending=False)
        elif sort_by == "Score (Rendah → Tinggi)" and 'score' in display_df.columns:
            display_df = display_df.sort_values('score', ascending=True)
        elif sort_by == "Nama Barang" and 'nama_barang' in display_df.columns:
            display_df = display_df.sort_values('nama_barang')

        # Format for display
        display_formatted = display_df.copy()
        if 'harga_satuan' in display_formatted.columns:
            display_formatted['harga_satuan'] = display_formatted['harga_satuan'].apply(
                lambda x: format_currency_full(x) if pd.notna(x) else "N/A"
            )
        if 'comparison_price' in display_formatted.columns:
            display_formatted['comparison_price'] = display_formatted['comparison_price'].apply(
                lambda x: format_currency_full(x) if pd.notna(x) else "N/A"
            )

        st.markdown(f"**Menampilkan {len(display_formatted)} hasil**")
        st.dataframe(display_formatted, use_container_width=True, height=400)

        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)

        # Export
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_data = res_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Hasil Validasi (CSV)",
                data=csv_data,
                file_name="sipval_validation_results.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_dl2:
            # Summary report text
            summary_text = f"""SIPVAL — Ringkasan Hasil Validasi
{"="*50}
Total Item Divalidasi : {total}
Valid (MATCH)          : {valid_count}
Partial Match         : {partial_count}
Invalid               : {invalid_count}
Rata-rata Skor        : {avg_score:.2f}
{"="*50}
Dihasilkan oleh SIPVAL v1.0
"""
            st.download_button(
                label="📥 Download Ringkasan (TXT)",
                data=summary_text.encode("utf-8"),
                file_name="sipval_summary_report.txt",
                mime="text/plain",
                use_container_width=True,
            )

        # Validation rules reference
        with st.expander("📏 Referensi Aturan Validasi"):
            st.markdown("""
            **Prioritas pencocokan validasi (urut dari tertinggi):**

            1. **Fungsi** — Apakah fungsi utama barang sama?
            2. **Spesifikasi Teknis** — Apakah dimensi, kapasitas, dan parameter teknis cocok?
            3. **Ukuran** — Apakah ukuran/dimensi fisik sesuai?
            4. **Material** — Apakah material/bahan setara?
            5. **Brand Equivalence** — Apakah merek setara secara kualitas?
            6. **Satuan** — Apakah satuan pengukuran sama?
            7. **Harga** — Harga bukan faktor utama pencocokan

            > ⚠️ **Catatan:** Sistem tidak memaksakan match hanya karena nama mirip.
            > Kecocokan didasarkan pada kesetaraan fungsional dan teknis.
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
