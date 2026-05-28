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

st.title("🛒 AI-Assisted Procurement Validation Dashboard")
st.markdown("Upload procurement items to automatically find internal comparisons and evaluate deviations.")

# Helper to read uploaded file into DataFrame with flexible parsing
@st.cache_data(show_spinner=False)
def load_dataframe(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            return df
        else:  # assume Excel formats
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

# File upload section (Single Upload Flow)
proc_file = st.file_uploader("📂 Upload **Procurement Items** (CSV/Excel)", type=["csv", "xlsx", "xls"])

if proc_file:
    proc_df = load_dataframe(proc_file)

    # Fix 1: Drop rows where the procurement item name is empty or NaN
    nama_col = "Nama Barang dan Spesifikasi" if "Nama Barang dan Spesifikasi" in proc_df.columns else "nama_barang"
    if nama_col in proc_df.columns:
        proc_df = proc_df.dropna(subset=[nama_col])

    st.subheader("🔎 Preview: Procurement Items")
    st.dataframe(proc_df.head())

    if st.button("🚀 Run Validation", type="primary"):
        if proc_df.empty:
            st.warning("The uploaded dataframe is empty.")
        else:
            # Check for required procurement columns
            has_nama = "nama_barang" in proc_df.columns or "Nama Barang dan Spesifikasi" in proc_df.columns
            
            if not has_nama:
                st.error("Procurement file is missing required column: 'nama_barang' or 'Nama Barang dan Spesifikasi'")
            else:
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

                # Display results table
                result_df = pd.DataFrame(results)
                st.subheader("📊 Validation Results")
                st.dataframe(result_df)
                st.success("Validation completed.")
else:
    st.info("Please upload a procurement file to begin.")
