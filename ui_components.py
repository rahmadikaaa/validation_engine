"""
ui_components.py — Reusable UI components for SIPVAL Dashboard.
Provides HTML-rendered widgets and DOCX justification export.
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime
from typing import Dict, Any, List, Optional

from mock_data import format_currency, format_currency_full


# ============================================================
# Status Badge
# ============================================================

def render_status_badge(status: str) -> str:
    """Return HTML for a colored status badge."""
    status_upper = str(status).upper()
    if status_upper in ("VALID", "MATCH"):
        return '<span class="status-badge valid">✅ Valid</span>'
    elif status_upper == "PARTIAL_MATCH":
        return '<span class="status-badge partial">⚠️ Partial Match</span>'
    elif status_upper in ("INVALID", "NO_CANDIDATE"):
        return '<span class="status-badge invalid">❌ Invalid</span>'
    else:
        return f'<span class="status-badge neutral">◽ {status}</span>'


def render_status_text(status: str) -> str:
    """Return text label for status (used in non-HTML contexts)."""
    status_upper = str(status).upper()
    if status_upper in ("VALID", "MATCH"):
        return "✅ Valid"
    elif status_upper == "PARTIAL_MATCH":
        return "⚠️ Partial Match"
    elif status_upper in ("INVALID", "NO_CANDIDATE"):
        return "❌ Invalid"
    return f"◽ {status}"


# ============================================================
# KPI Card
# ============================================================

def render_kpi_card(icon: str, label: str, value: str, subtitle: str = "", color: str = "teal") -> str:
    """Return HTML for a glassmorphism KPI card."""
    return f"""
    <div class="kpi-card {color} fade-in">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{subtitle}</div>
    </div>
    """


# ============================================================
# Score Bar
# ============================================================

def render_score_bar(score: float, label: str = "Match Score") -> str:
    """Return HTML for a visual score progress bar.
    
    Score should be 0.0 to 1.0.
    """
    pct = max(0, min(100, round(score * 100)))
    if pct >= 70:
        level = "high"
    elif pct >= 40:
        level = "medium"
    else:
        level = "low"

    return f"""
    <div style="margin: 8px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="color: #94A3B8; font-size: 0.75rem; font-weight: 500;">{label}</span>
            <span style="color: #F1F5F9; font-size: 0.85rem; font-weight: 700;">{pct}%</span>
        </div>
        <div class="score-bar-container">
            <div class="score-bar-fill {level}" style="width: {pct}%;"></div>
        </div>
    </div>
    """


# ============================================================
# Page Header
# ============================================================

def render_page_header(icon: str, title: str, subtitle: str = ""):
    """Render a branded page header."""
    sub_html = f'<div class="subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div class="sipval-header fade-in">
        <h1>{icon} {title}</h1>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# AI Reasoning Display
# ============================================================

REASONING_TYPE_LABELS = {
    "dimension_match": ("📐", "Kecocokan Dimensi"),
    "function_match": ("⚙️", "Kecocokan Fungsi"),
    "material_equivalence": ("🔩", "Kesetaraan Material"),
    "industrial_vs_consumer_grade": ("🏭", "Grade Industrial"),
    "quantity_or_unit": ("📦", "Kecocokan Satuan"),
}


def render_reasoning_cards(reasoning_list: List[Dict[str, Any]]):
    """Render AI reasoning as styled cards."""
    if not reasoning_list:
        st.info("Tidak ada data reasoning tersedia.")
        return

    for item in reasoning_list:
        r_type = item.get("type", "unknown")
        r_status = item.get("status", "unknown")
        r_notes = item.get("notes", "")

        icon, label = REASONING_TYPE_LABELS.get(r_type, ("🔍", r_type.replace("_", " ").title()))

        st.markdown(f"""
        <div class="reasoning-item">
            <div class="ri-header">
                <span class="ri-icon">{icon}</span>
                <span class="ri-type">{label}</span>
                <span class="ri-status {r_status}">{r_status.upper()}</span>
            </div>
            <div class="ri-notes">{r_notes}</div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# Candidate Card
# ============================================================

def render_candidate_card(candidate: Dict[str, Any]):
    """Render the best candidate comparison card."""
    nama = candidate.get("comparison_product") or candidate.get("nama_produk", "N/A")
    vendor = candidate.get("vendor", "N/A")
    harga = candidate.get("comparison_price") or candidate.get("harga", 0)
    spec = candidate.get("comparison_specification") or candidate.get("spesifikasi", "N/A")
    satuan = candidate.get("satuan", "-")

    st.markdown(f"""
    <div class="candidate-card fade-in">
        <div class="cc-title">🏆 Kandidat Pembanding Terbaik</div>
        <div class="cc-name">{nama}</div>
        <div class="cc-details">
            <div class="cc-field">
                <span class="cc-field-label">Vendor</span>
                <span class="cc-field-value">{vendor}</span>
            </div>
            <div class="cc-field">
                <span class="cc-field-label">Harga</span>
                <span class="cc-field-value">{format_currency_full(harga)}</span>
            </div>
            <div class="cc-field">
                <span class="cc-field-label">Spesifikasi</span>
                <span class="cc-field-value">{spec}</span>
            </div>
            <div class="cc-field">
                <span class="cc-field-label">Satuan</span>
                <span class="cc-field-value">{satuan}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# Vendor Card
# ============================================================

def render_vendor_card(vendor: Dict[str, Any]):
    """Render a vendor summary card."""
    nama = vendor.get("nama", "Unknown")
    lokasi = vendor.get("lokasi", "-")
    items = vendor.get("items_supplied", 0)
    total = vendor.get("total_nilai", 0)
    reliability = vendor.get("reliability", 0)
    npwp = vendor.get("npwp", "-")
    valid = vendor.get("valid_count", 0)
    partial = vendor.get("partial_count", 0)
    invalid = vendor.get("invalid_count", 0)

    # Reliability color
    if reliability >= 90:
        rel_color = "#10B981"
    elif reliability >= 80:
        rel_color = "#F59E0B"
    else:
        rel_color = "#EF4444"

    st.markdown(f"""
    <div class="vendor-card fade-in">
        <div class="vc-name">🏢 {nama}</div>
        <div class="vc-location">📍 {lokasi} &nbsp;|&nbsp; NPWP: {npwp}</div>
        <div class="vc-stats">
            <div class="vc-stat">
                <span class="vc-stat-label">Item Dipasok</span>
                <span class="vc-stat-value">{items}</span>
            </div>
            <div class="vc-stat">
                <span class="vc-stat-label">Total Nilai</span>
                <span class="vc-stat-value">{format_currency(total)}</span>
            </div>
            <div class="vc-stat">
                <span class="vc-stat-label">Reliabilitas</span>
                <span class="vc-stat-value" style="color: {rel_color};">{reliability}%</span>
            </div>
            <div class="vc-stat">
                <span class="vc-stat-label">Status Validasi</span>
                <span class="vc-stat-value" style="font-size: 0.8rem;">✅{valid} ⚠️{partial} ❌{invalid}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# Info Card Row
# ============================================================

def render_info_card(label: str, value: str):
    """Render a simple info card."""
    st.markdown(f"""
    <div class="info-card">
        <div class="card-label">{label}</div>
        <div class="card-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# System Status
# ============================================================

def render_system_status():
    """Render system status indicators for sidebar."""
    return """
    <div style="padding: 8px 0;">
        <div style="color: #94A3B8; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Status Sistem</div>
        <div style="margin-bottom: 6px;">
            <span class="sys-status online"><span class="dot"></span> Internal DB</span>
        </div>
        <div style="margin-bottom: 6px;">
            <span class="sys-status online"><span class="dot"></span> Reasoning Engine</span>
        </div>
        <div style="margin-bottom: 6px;">
            <span class="sys-status offline"><span class="dot"></span> INAPROC API</span>
        </div>
    </div>
    """


# ============================================================
# Justification Text Generator
# ============================================================

def generate_justification_text(
    item_data: Dict[str, Any],
    result_data: Dict[str, Any],
) -> str:
    """Generate a plain-text justification document."""
    nama = item_data.get("nama_barang") or item_data.get("Nama Barang dan Spesifikasi", "N/A")
    id_val = item_data.get("id_item") or item_data.get("ID", "N/A")
    kategori = item_data.get("Kategori") or item_data.get("kategori", "N/A")
    satuan = item_data.get("Satuan") or item_data.get("satuan", "N/A")
    harga_ref = item_data.get("Harga Satuan") or item_data.get("harga_satuan", "N/A")

    status = result_data.get("status", "N/A")
    score = result_data.get("score", 0)
    comp_product = result_data.get("comparison_product", "N/A")
    comp_spec = result_data.get("comparison_specification", "N/A")
    vendor = result_data.get("vendor", "N/A")
    comp_price = result_data.get("comparison_price", 0)
    deviation = result_data.get("deviation_notes", "")

    # Determine recommendation
    if status in ("VALID", "MATCH"):
        rekomendasi = "LAYAK — Item sesuai dengan referensi standar internal. Harga dan spesifikasi wajar, dapat diproses lebih lanjut."
    elif status == "PARTIAL_MATCH":
        rekomendasi = "PERLU REVIEW — Item memiliki kemiripan parsial dengan referensi. Terdapat deviasi minor yang perlu direview."
    else:
        rekomendasi = "TIDAK LAYAK — Item tidak memiliki referensi internal yang cocok atau deviasi terlalu tinggi. Wajib review manual."

    # Calculate deviation percentage
    try:
        harga_ref_val = float(harga_ref)
        comp_price_val = float(comp_price)
        if harga_ref_val > 0:
            dev_pct = ((comp_price_val - harga_ref_val) / harga_ref_val) * 100
            dev_str = f"{dev_pct:+.1f}%"
        else:
            dev_str = "N/A"
    except (ValueError, TypeError):
        dev_str = "N/A"

    now = datetime.now().strftime("%d %B %Y, %H:%M WIB")

    text = f"""
═══════════════════════════════════════════════════════════
         JUSTIFIKASI PENGADAAN BARANG/JASA
         SIPVAL — Sistem Validasi Pengadaan
═══════════════════════════════════════════════════════════

Tanggal     : {now}
Dokumen     : Justifikasi Validasi Pembanding

═══════════════════════════════════════════════════════════
1. INFORMASI ITEM PENGADAAN
═══════════════════════════════════════════════════════════

ID Item        : {id_val}
Nama Barang    : {nama}
Kategori       : {kategori}
Satuan         : {satuan}
Harga Referensi: {format_currency_full(harga_ref)}

═══════════════════════════════════════════════════════════
2. KANDIDAT PEMBANDING
═══════════════════════════════════════════════════════════

Produk Pembanding  : {comp_product}
Spesifikasi        : {comp_spec}
Vendor             : {vendor}
Harga Pembanding   : {format_currency_full(comp_price)}
Deviasi Harga      : {dev_str}

═══════════════════════════════════════════════════════════
3. HASIL VALIDASI AI
═══════════════════════════════════════════════════════════

Status Validasi    : {status}
Skor Kecocokan     : {score}
Catatan Deviasi    : {deviation}

═══════════════════════════════════════════════════════════
4. REKOMENDASI
═══════════════════════════════════════════════════════════

{rekomendasi}

═══════════════════════════════════════════════════════════
Dokumen ini dihasilkan secara otomatis oleh SIPVAL.
Sistem Validasi Pengadaan berbasis AI — v1.0 MVP
═══════════════════════════════════════════════════════════
"""
    return text.strip()


# ============================================================
# DOCX Justification Export
# ============================================================

def generate_justification_docx(
    item_data: Dict[str, Any],
    result_data: Dict[str, Any],
) -> Optional[bytes]:
    """Generate a .docx justification document. Returns bytes or None if python-docx unavailable."""
    try:
        from docx import Document
        from docx.shared import Pt, Inches, RGBColor, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
    except ImportError:
        return None

    nama = item_data.get("nama_barang") or item_data.get("Nama Barang dan Spesifikasi", "N/A")
    id_val = str(item_data.get("id_item") or item_data.get("ID", "N/A"))
    kategori = str(item_data.get("Kategori") or item_data.get("kategori", "N/A"))
    satuan = str(item_data.get("Satuan") or item_data.get("satuan", "N/A"))
    harga_ref = item_data.get("Harga Satuan") or item_data.get("harga_satuan", "N/A")

    status = result_data.get("status", "N/A")
    score = result_data.get("score", 0)
    comp_product = str(result_data.get("comparison_product", "N/A"))
    comp_spec = str(result_data.get("comparison_specification", "N/A"))
    vendor = str(result_data.get("vendor", "N/A"))
    comp_price = result_data.get("comparison_price", 0)
    deviation = str(result_data.get("deviation_notes", ""))

    # Recommendation
    if status in ("VALID", "MATCH"):
        rekomendasi = "LAYAK — Item sesuai dengan referensi standar internal. Harga dan spesifikasi wajar."
    elif status == "PARTIAL_MATCH":
        rekomendasi = "PERLU REVIEW — Item memiliki kemiripan parsial. Terdapat deviasi yang perlu diperiksa."
    else:
        rekomendasi = "TIDAK LAYAK — Referensi internal tidak cocok atau deviasi terlalu tinggi."

    now = datetime.now().strftime("%d %B %Y")

    doc = Document()

    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(10)

    # Title
    title = doc.add_heading("JUSTIFIKASI PENGADAAN BARANG/JASA", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(13, 148, 136)

    subtitle = doc.add_paragraph("SIPVAL — Sistem Validasi Pengadaan")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in subtitle.runs:
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph(f"Tanggal: {now}")
    doc.add_paragraph("")

    # Section 1: Item Info
    doc.add_heading("1. Informasi Item Pengadaan", level=1)
    table1 = doc.add_table(rows=5, cols=2)
    table1.style = "Light List Accent 1"
    fields1 = [
        ("ID Item", id_val),
        ("Nama Barang", str(nama)),
        ("Kategori", kategori),
        ("Satuan", satuan),
        ("Harga Referensi", format_currency_full(harga_ref)),
    ]
    for i, (label, val) in enumerate(fields1):
        table1.rows[i].cells[0].text = label
        table1.rows[i].cells[1].text = val

    doc.add_paragraph("")

    # Section 2: Candidate
    doc.add_heading("2. Kandidat Pembanding", level=1)
    table2 = doc.add_table(rows=4, cols=2)
    table2.style = "Light List Accent 1"
    fields2 = [
        ("Produk Pembanding", comp_product),
        ("Spesifikasi", comp_spec),
        ("Vendor", vendor),
        ("Harga Pembanding", format_currency_full(comp_price)),
    ]
    for i, (label, val) in enumerate(fields2):
        table2.rows[i].cells[0].text = label
        table2.rows[i].cells[1].text = val

    doc.add_paragraph("")

    # Section 3: Validation
    doc.add_heading("3. Hasil Validasi AI", level=1)
    table3 = doc.add_table(rows=3, cols=2)
    table3.style = "Light List Accent 1"
    fields3 = [
        ("Status Validasi", str(status)),
        ("Skor Kecocokan", str(score)),
        ("Catatan Deviasi", deviation),
    ]
    for i, (label, val) in enumerate(fields3):
        table3.rows[i].cells[0].text = label
        table3.rows[i].cells[1].text = val

    doc.add_paragraph("")

    # Section 4: Recommendation
    doc.add_heading("4. Rekomendasi", level=1)
    rec_para = doc.add_paragraph(rekomendasi)
    for run in rec_para.runs:
        run.font.bold = True
        run.font.size = Pt(11)

    doc.add_paragraph("")

    # Footer
    footer = doc.add_paragraph("Dokumen ini dihasilkan secara otomatis oleh SIPVAL — Sistem Validasi Pengadaan v1.0")
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in footer.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(148, 163, 184)

    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
