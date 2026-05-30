# app.py
"""Streamlit application for AI-Assisted Procurement Validation System MVP.
Features:
- Upload procurement items (CSV or Excel)
- Flexible parsing (handles both standard headers and row-offset headers)
- Internal placeholder candidate search
- Run validation using reasoning_engine.run_reasoning
- Show validation results with match status, score, and notes.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any

# Local import of reasoning engine functions
from cognition.reasoning_engine import run_reasoning
from cognition.candidate_generator import generate_placeholder_candidates

st.set_page_config(page_title="Procurement Validation Dashboard", layout="wide")

# -- Session State Init --
if "proc_df" not in st.session_state:
    st.session_state.proc_df = pd.DataFrame()
if "result_df" not in st.session_state:
    st.session_state.result_df = pd.DataFrame()
if "validation_run" not in st.session_state:
    st.session_state.validation_run = False
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

# Helper to read uploaded Excel file into DataFrame with flexible parsing
@st.cache_data(show_spinner=False)
def load_procurement_excel(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        # Read normally first
        df = pd.read_excel(uploaded_file)
        
        # Check if required columns exist in the normal read
        has_nama = "nama_barang" in df.columns or "Nama Barang dan Spesifikasi" in df.columns
        if not has_nama:
            # Reset file pointer for re-read
            uploaded_file.seek(0)
            # Dynamic header scan: load first 10 rows without header
            df_scan = pd.read_excel(uploaded_file, header=None, nrows=10)
            
            target_cols = {"ID", "Kategori", "Sub kategori", "Nama Barang dan Spesifikasi"}
            header_idx = None
            
            for idx, row in df_scan.iterrows():
                row_vals = set(str(val).strip() for val in row.values if pd.notna(val))
                # Check if all target columns are in this row
                if target_cols.issubset(row_vals):
                    header_idx = idx
                    break
            
            if header_idx is not None:
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, header=header_idx)
        return df
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_csv_file(uploaded_file):
    df_raw = pd.read_csv(uploaded_file, header=None)

    # Try detecting validation results first
    uploaded_file.seek(0)
    df_direct = pd.read_csv(uploaded_file)
    normalized_cols = [str(c).strip().lower() for c in df_direct.columns]

    validation_cols = {"id_item", "nama_barang", "status", "vendor", "comparison_price"}
    if validation_cols.intersection(set(normalized_cols)):
        df_direct = df_direct.loc[:, ~df_direct.columns.astype(str).str.contains("^Unnamed")]
        return df_direct, "validation_results"

    # Detect SHBJ procurement header row
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

    # fallback
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
        raise ValueError("Unsupported file format")
        
    # Clean up fully empty columns
    df = df.replace("None", pd.NA)
    df = df.dropna(axis=1, how="all")
    
    return df, file_type

def run_validation_logic():
    proc_df = st.session_state.proc_df
    if proc_df.empty:
        st.warning("The uploaded dataframe is empty.")
        return
        
    has_nama = "nama_barang" in proc_df.columns or "Nama Barang dan Spesifikasi" in proc_df.columns
    if not has_nama:
        st.error("Procurement file is missing required column: 'nama_barang' or 'Nama Barang dan Spesifikasi'")
        return
        
    results: List[Dict[str, Any]] = []
    
    # Iterate over procurement rows
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

        # Fix 3: Split combined nama + spesifikasi when separator exists
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
        
        # Generate internal comparison candidates
        generated_candidates = generate_placeholder_candidates(item_dict)
        
        # Evaluate each candidate and keep the highest score
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
        
        # Ensure candidate was found
        cand = best_match["candidate"] or {}
        
        # Extract original values for reporting
        id_val = item_dict.get("id_item") or item_dict.get("ID")
        nama_val = item_dict.get("nama_barang")
        satuan_val = item_dict.get("satuan")
        
        # Fix 4: Extract harga_satuan reference price
        harga_satuan_val = item_dict.get("harga_satuan") or item_dict.get("Harga Satuan")

        # Append summary for this procurement item with specific output schema
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


# -- Sidebar Navigation --
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [
    "📊 Dashboard Overview", 
    "📝 Procurement Items", 
    "🔍 Item Detail", 
    "🏢 Vendor History", 
    "📈 Validation Results"
])

st.sidebar.markdown("---")
st.sidebar.markdown("*Demo MVP — bukan website resmi pemerintah*")

# -- Main App Header & Global File Uploader --
st.title("🛒 AI-Assisted Procurement Validation Dashboard")
st.markdown("Upload procurement items to automatically find internal comparisons and evaluate deviations.")

proc_file = st.file_uploader("📂 Upload **Procurement Items (Excel)** or **Validation Results (CSV)**", type=["csv", "xlsx", "xls"])
if proc_file is not None:
    if st.session_state.uploaded_file_name != proc_file.name:
        try:
            df, file_type = load_uploaded_file(proc_file)
            
            if file_type == "validation_results":
                # Flow B: Validation Results CSV -> Results Viewer
                if "Unnamed: 0" in df.columns:
                    df = df.drop(columns=["Unnamed: 0"])
                
                st.session_state.result_df = df
                st.session_state.proc_df = df  # Use result_df for UI item references as well
                st.session_state.validation_run = True
                st.session_state.uploaded_file_name = proc_file.name
            else:
                # Flow A: Procurement File -> Normalization
                nama_col = "Nama Barang dan Spesifikasi" if "Nama Barang dan Spesifikasi" in df.columns else "nama_barang"
                if nama_col in df.columns:
                    df = df.dropna(subset=[nama_col])
                st.session_state.proc_df = df
                st.session_state.result_df = pd.DataFrame()
                st.session_state.validation_run = False
                st.session_state.uploaded_file_name = proc_file.name
                
        except Exception as e:
            st.error(f"Error loading file: {e}")

st.divider()

# -- Page Implementations --

if page == "📊 Dashboard Overview":
    st.header("Dashboard Overview")
    
    col1, col2, col3 = st.columns(3)
    total_items = len(st.session_state.proc_df)
    col1.metric("Total Items", total_items)
    
    if st.session_state.validation_run and not st.session_state.result_df.empty and 'status' in st.session_state.result_df.columns:
        res_df = st.session_state.result_df
        total_vendors = res_df['vendor'].nunique() if 'vendor' in res_df.columns else 0
        col2.metric("Total Vendors", total_vendors)
        
        valid_items = len(res_df[res_df['status'] == 'MATCH'])
        col3.metric("Valid Items", valid_items)
        
        col4, col5, col6 = st.columns(3)
        partial_items = len(res_df[res_df['status'] == 'PARTIAL_MATCH'])
        false_items = len(res_df[~res_df['status'].isin(['MATCH', 'PARTIAL_MATCH'])])
        avg_score = res_df['score'].mean() if 'score' in res_df.columns else 0.0
        
        col4.metric("Partial Items", partial_items)
        col5.metric("False / Perlu Review Items", false_items)
        col6.metric("Average Score (Deviation)", f"{avg_score:.2f}")
        
        st.subheader("Validation Summary")
        st.success("Validation has been successfully run. Check 'Validation Results' for details.")
    else:
        st.info("Validation not yet run")
        col2.metric("Total Vendors", "-")
        col3.metric("Valid Items", "-")
        
        if total_items > 0:
            if st.button("🚀 Run Validation", type="primary", key="dash_run_btn"):
                with st.spinner("Running Validation..."):
                    run_validation_logic()
                st.rerun()
    
    if not st.session_state.proc_df.empty:
        st.subheader("Preview: Uploaded Data")
        st.dataframe(st.session_state.proc_df.head())


elif page == "📝 Procurement Items":
    st.header("Procurement Items")
    
    if st.session_state.proc_df.empty:
        st.info("Please upload a procurement file to view items.")
    else:
        if not st.session_state.validation_run:
            if st.button("🚀 Run Validation", type="primary", key="proc_run_btn"):
                with st.spinner("Running Validation..."):
                    run_validation_logic()
                st.rerun()
                
        df_display = st.session_state.proc_df.copy()
        
        col1, col2 = st.columns(2)
        with col1:
            search_query = st.text_input("🔍 Search items by name")
        with col2:
            status_filter = "All"
            if st.session_state.validation_run and not st.session_state.result_df.empty and 'status' in st.session_state.result_df.columns:
                statuses = ["All"] + list(st.session_state.result_df['status'].unique())
                status_filter = st.selectbox("Filter by Validation Status", statuses)
        
        # Apply Search
        if search_query:
            nama_col = "Nama Barang dan Spesifikasi" if "Nama Barang dan Spesifikasi" in df_display.columns else "nama_barang"
            if nama_col in df_display.columns:
                df_display = df_display[df_display[nama_col].astype(str).str.contains(search_query, case=False, na=False)]
                
        # Apply Filter
        if status_filter != "All" and st.session_state.validation_run and 'status' in st.session_state.result_df.columns:
            res_df = st.session_state.result_df
            filtered_names = res_df[res_df['status'] == status_filter]['nama_barang'].tolist()
            nama_col = "Nama Barang dan Spesifikasi" if "Nama Barang dan Spesifikasi" in df_display.columns else "nama_barang"
            if nama_col in df_display.columns:
                df_display = df_display[df_display[nama_col].isin(filtered_names)]
                
        st.dataframe(df_display)


elif page == "🔍 Item Detail":
    st.header("Item Detail")
    
    if st.session_state.proc_df.empty:
        st.info("Please upload a procurement file to view item details.")
    else:
        proc_df = st.session_state.proc_df
        nama_col = "Nama Barang dan Spesifikasi" if "Nama Barang dan Spesifikasi" in proc_df.columns else "nama_barang"
        
        if nama_col in proc_df.columns:
            item_names = proc_df[nama_col].dropna().unique().tolist()
        else:
            item_names = proc_df.index.tolist()
            
        selected_name = st.selectbox("Select Item", item_names)
        
        if selected_name:
            if nama_col in proc_df.columns:
                item_row = proc_df[proc_df[nama_col] == selected_name].iloc[0]
            else:
                item_row = proc_df.loc[selected_name]
                
            id_val = item_row.get("id_item") or item_row.get("ID") or "N/A"
            kat_val = item_row.get("Kategori") or item_row.get("kategori") or "N/A"
            sat_val = item_row.get("Satuan") or item_row.get("satuan") or "N/A"
            harga_val = item_row.get("Harga Satuan") or item_row.get("harga_satuan") or "N/A"
            
            st.subheader(f"Item: {selected_name}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("ID", str(id_val))
            c2.metric("Kategori", str(kat_val))
            c3.metric("Satuan", str(sat_val))
            c4.metric("Harga Satuan (Ref)", str(harga_val))
            
            t1, t2, t3, t4, t5 = st.tabs(["Overview", "Price History", "Vendor History", "Validation", "Justification"])
            
            with t1:
                st.markdown("**Procurement Context:** Pembelian rutin")
                st.markdown("**Business Function:** Operasional & Dukungan")
                st.markdown("**Critical Specifications:** Mengikuti spesifikasi LKPP / Internal")
                st.markdown("**Validation Criteria:** Harga kewajaran dan ketersediaan vendor")
                
            with t2:
                st.markdown("### Price History (2024 vs 2025)")
                try:
                    val = float(pd.to_numeric(harga_val, errors='coerce'))
                    if pd.notna(val):
                        hist_df = pd.DataFrame({"Year": ["2024", "2025"], "Price": [val * 0.92, val]})
                        st.bar_chart(hist_df.set_index("Year"))
                    else:
                        st.info("No numeric price available for chart.")
                except Exception:
                    st.info("No numeric price available for chart.")
                    
            with t3:
                st.markdown("### Vendor History")
                vendor_name = "Mock Vendor PT"
                status_val = "N/A"
                if st.session_state.validation_run and not st.session_state.result_df.empty and 'status' in st.session_state.result_df.columns:
                    res_row = st.session_state.result_df[st.session_state.result_df['nama_barang'] == selected_name]
                    if not res_row.empty:
                        vendor_name = res_row.iloc[0].get('vendor', vendor_name)
                        status_val = res_row.iloc[0].get('status', status_val)
                        
                st.markdown(f"**Vendor Name:** {vendor_name}")
                st.markdown("**Year:** 2024")
                st.markdown("**Location:** Jakarta Pusat")
                st.markdown("**Contact Available:** Yes (Verified)")
                st.markdown(f"**Validation Status:** {status_val}")
                
            with t4:
                if not st.session_state.validation_run or 'status' not in st.session_state.result_df.columns:
                    st.warning("Validation has not been run yet.")
                else:
                    res_row = st.session_state.result_df[st.session_state.result_df['nama_barang'] == selected_name]
                    if not res_row.empty:
                        row = res_row.iloc[0]
                        st.markdown(f"**Status:** {row.get('status')}")
                        st.markdown(f"**Score:** {row.get('score')}")
                        st.markdown(f"**Comparison Product:** {row.get('comparison_product')}")
                        st.markdown(f"**Comparison Specification:** {row.get('comparison_specification')}")
                        st.markdown(f"**Deviation Notes:** {row.get('deviation_notes')}")
                    else:
                        st.info("No validation data for this item.")
                        
            with t5:
                if not st.session_state.validation_run or 'status' not in st.session_state.result_df.columns:
                    st.warning("Run validation to generate justification.")
                else:
                    res_row = st.session_state.result_df[st.session_state.result_df['nama_barang'] == selected_name]
                    if not res_row.empty:
                        row = res_row.iloc[0]
                        status = row.get('status')
                        if status == "MATCH":
                            st.success("Justifikasi Pengadaan: Item ini sesuai dengan referensi standar internal. Harga dan spesifikasi wajar, dapat diproses lebih lanjut.")
                        elif status == "PARTIAL_MATCH":
                            st.warning("Justifikasi Pengadaan: Item memiliki kemiripan parsial dengan referensi. Terdapat deviasi minor yang perlu direview (Perlu Review) sebelum dilanjutkan.")
                        else:
                            st.error("Justifikasi Pengadaan: Item tidak memiliki referensi internal yang cocok atau deviasi terlalu tinggi. Wajib review manual (False / Perlu Review).")
                    else:
                        st.info("No validation data for this item.")


elif page == "🏢 Vendor History":
    st.header("Vendor History")
    if not st.session_state.validation_run or st.session_state.result_df.empty or 'status' not in st.session_state.result_df.columns:
        st.info("Run validation to view vendor matching history from your uploaded items.")
    else:
        res_df = st.session_state.result_df
        if 'vendor' in res_df.columns:
            vendor_counts = res_df['vendor'].value_counts().reset_index()
            vendor_counts.columns = ['Vendor Name', 'Items Supplied']
            st.dataframe(vendor_counts)
        else:
            st.info("No vendor data found in validation results.")


elif page == "📈 Validation Results":
    st.header("Validation Results")
    if not st.session_state.validation_run:
        st.info("Validation has not been run yet. Please run validation on the Procurement Items page or Dashboard.")
    else:
        res_df = st.session_state.result_df
        st.dataframe(res_df)
        
        csv_data = res_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Validation Results as CSV",
            data=csv_data,
            file_name="validation_results.csv",
            mime="text/csv",
        )
