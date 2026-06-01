"""
ui_styles.py — Enterprise CSS Theme for SIPVAL Procurement Dashboard.
Injects custom CSS via st.markdown for professional dark-mode appearance.
Color System: Deep Navy + Teal + Gold (government/procurement style).
"""

import streamlit as st


def inject_enterprise_css():
    """Inject the full enterprise CSS theme into the Streamlit app."""
    st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)


ENTERPRISE_CSS = """
<style>
/* ============================================================
   SIPVAL — Sistem Validasi Pengadaan
   Enterprise Dark Theme — Navy + Teal + Gold
   ============================================================ */

/* --- Google Font --- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* --- CSS Variables --- */
:root {
    --navy-900: #060F1E;
    --navy-800: #0A1628;
    --navy-700: #0E1A2E;
    --navy-600: #1A2742;
    --navy-500: #1E3A5F;
    --navy-400: #2D4A6F;
    --teal-600: #0D9488;
    --teal-500: #14B8A6;
    --teal-400: #2DD4BF;
    --gold-500: #F59E0B;
    --gold-400: #FBBF24;
    --gold-300: #FDE68A;
    --slate-50: #F8FAFC;
    --slate-100: #F1F5F9;
    --slate-300: #CBD5E1;
    --slate-400: #94A3B8;
    --slate-500: #64748B;
    --green-500: #10B981;
    --green-400: #34D399;
    --amber-500: #F59E0B;
    --red-500: #EF4444;
    --red-400: #F87171;
}

/* --- Global App --- */
.stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Hide default Streamlit header bar */
header[data-testid="stHeader"] {
    background: rgba(6, 15, 30, 0.85) !important;
    backdrop-filter: blur(12px);
}

/* --- Sidebar --- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #060F1E 0%, #0A1628 40%, #0E1A2E 100%) !important;
    border-right: 1px solid rgba(13, 148, 136, 0.2);
}

section[data-testid="stSidebar"] .stRadio > label {
    color: var(--slate-300) !important;
    font-weight: 500;
}

section[data-testid="stSidebar"] .stRadio > div > label {
    background: transparent !important;
    border-radius: 8px;
    padding: 8px 12px !important;
    margin-bottom: 2px;
    transition: all 0.2s ease;
    color: var(--slate-400) !important;
}

section[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(13, 148, 136, 0.1) !important;
    color: var(--slate-100) !important;
}

section[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
section[data-testid="stSidebar"] .stRadio > div [aria-checked="true"] {
    background: rgba(13, 148, 136, 0.15) !important;
    color: var(--teal-400) !important;
}

/* --- Headings --- */
h1, h2, h3 {
    font-family: 'Inter', sans-serif !important;
    letter-spacing: -0.02em;
}

h1 {
    color: var(--slate-50) !important;
    font-weight: 700 !important;
    font-size: 1.75rem !important;
}

h2 {
    color: var(--slate-100) !important;
    font-weight: 600 !important;
}

h3 {
    color: var(--slate-300) !important;
    font-weight: 600 !important;
}

/* --- Metric Cards --- */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(26, 39, 66, 0.8) 0%, rgba(14, 26, 46, 0.9) 100%);
    border: 1px solid rgba(30, 58, 95, 0.5);
    border-radius: 12px;
    padding: 16px 20px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

[data-testid="stMetric"]:hover {
    border-color: rgba(13, 148, 136, 0.4);
    box-shadow: 0 6px 24px rgba(13, 148, 136, 0.1);
    transform: translateY(-2px);
}

[data-testid="stMetricLabel"] {
    color: var(--slate-400) !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

[data-testid="stMetricValue"] {
    color: var(--slate-50) !important;
    font-weight: 700 !important;
    font-size: 1.6rem !important;
}

[data-testid="stMetricDelta"] > div {
    font-weight: 500 !important;
}

/* --- Buttons --- */
.stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 8px 24px !important;
    transition: all 0.25s ease !important;
    border: 1px solid rgba(30, 58, 95, 0.5) !important;
    letter-spacing: 0.01em;
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--teal-600) 0%, #0F766E 100%) !important;
    color: white !important;
    border: 1px solid var(--teal-500) !important;
    box-shadow: 0 4px 14px rgba(13, 148, 136, 0.3) !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, var(--teal-500) 0%, var(--teal-600) 100%) !important;
    box-shadow: 0 6px 20px rgba(13, 148, 136, 0.4) !important;
    transform: translateY(-1px);
}

.stButton > button[kind="secondary"],
.stButton > button[data-testid="stBaseButton-secondary"] {
    background: rgba(26, 39, 66, 0.6) !important;
    color: var(--slate-300) !important;
}

.stButton > button[kind="secondary"]:hover,
.stButton > button[data-testid="stBaseButton-secondary"]:hover {
    background: rgba(26, 39, 66, 0.9) !important;
    border-color: var(--teal-600) !important;
    color: var(--teal-400) !important;
}

/* Download Button */
.stDownloadButton > button {
    background: linear-gradient(135deg, var(--gold-500) 0%, #D97706 100%) !important;
    color: #1a1a1a !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 14px rgba(245, 158, 11, 0.3) !important;
}

.stDownloadButton > button:hover {
    box-shadow: 0 6px 20px rgba(245, 158, 136, 0.4) !important;
    transform: translateY(-1px);
}

/* --- Tabs --- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(14, 26, 46, 0.5);
    border-radius: 10px;
    padding: 4px;
    border: 1px solid rgba(30, 58, 95, 0.3);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 10px 20px;
    color: var(--slate-400);
    font-weight: 500;
    font-size: 0.85rem;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--slate-100);
    background: rgba(13, 148, 136, 0.08);
}

.stTabs [aria-selected="true"] {
    background: rgba(13, 148, 136, 0.15) !important;
    color: var(--teal-400) !important;
    font-weight: 600;
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--teal-600) !important;
}

/* --- DataFrames --- */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(30, 58, 95, 0.4);
}

[data-testid="stDataFrame"] table {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem;
}

/* --- Expander --- */
[data-testid="stExpander"] {
    background: rgba(26, 39, 66, 0.4) !important;
    border: 1px solid rgba(30, 58, 95, 0.4) !important;
    border-radius: 10px !important;
    margin-bottom: 8px;
    transition: border-color 0.2s ease;
}

[data-testid="stExpander"]:hover {
    border-color: rgba(13, 148, 136, 0.3) !important;
}

[data-testid="stExpander"] summary {
    font-weight: 500 !important;
    color: var(--slate-300) !important;
}

/* --- File Uploader --- */
[data-testid="stFileUploader"] {
    border: 2px dashed rgba(30, 58, 95, 0.5) !important;
    border-radius: 12px !important;
    background: rgba(14, 26, 46, 0.3) !important;
    padding: 16px !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--teal-600) !important;
    background: rgba(13, 148, 136, 0.05) !important;
}

/* --- Selectbox, TextInput --- */
[data-testid="stSelectbox"] > div > div,
[data-testid="stTextInput"] > div > div > input {
    border-radius: 8px !important;
    border: 1px solid rgba(30, 58, 95, 0.5) !important;
    font-family: 'Inter', sans-serif !important;
}

/* --- Alert/Info/Warning/Error Messages --- */
.stAlert {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
}

div[data-testid="stNotification"] {
    border-radius: 10px !important;
}

/* --- Divider --- */
hr {
    border-color: rgba(30, 58, 95, 0.4) !important;
}

/* --- Spinner --- */
.stSpinner > div {
    border-top-color: var(--teal-500) !important;
}

/* ============================================================
   Custom HTML Component Classes
   Used via st.markdown(html, unsafe_allow_html=True)
   ============================================================ */

/* --- Branded Header --- */
.sipval-header {
    background: linear-gradient(135deg, rgba(13, 148, 136, 0.12) 0%, rgba(245, 158, 11, 0.06) 100%);
    border: 1px solid rgba(13, 148, 136, 0.2);
    border-radius: 14px;
    padding: 20px 28px;
    margin-bottom: 24px;
}

.sipval-header h1 {
    margin: 0 !important;
    font-size: 1.5rem !important;
    background: linear-gradient(135deg, var(--teal-400), var(--gold-400));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.sipval-header .subtitle {
    color: var(--slate-400);
    font-size: 0.85rem;
    margin-top: 4px;
    font-weight: 400;
}

/* --- KPI Card --- */
.kpi-card {
    background: linear-gradient(135deg, rgba(26, 39, 66, 0.7) 0%, rgba(14, 26, 46, 0.85) 100%);
    border: 1px solid rgba(30, 58, 95, 0.4);
    border-radius: 12px;
    padding: 18px 22px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
    min-height: 110px;
}

.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.kpi-card::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    border-radius: 12px 0 0 12px;
}

.kpi-card.teal::before { background: linear-gradient(180deg, var(--teal-500), var(--teal-600)); }
.kpi-card.green::before { background: linear-gradient(180deg, var(--green-400), var(--green-500)); }
.kpi-card.amber::before { background: linear-gradient(180deg, var(--gold-400), var(--gold-500)); }
.kpi-card.red::before { background: linear-gradient(180deg, var(--red-400), var(--red-500)); }
.kpi-card.gold::before { background: linear-gradient(180deg, var(--gold-300), var(--gold-500)); }

.kpi-card .kpi-icon {
    font-size: 1.5rem;
    margin-bottom: 4px;
}

.kpi-card .kpi-label {
    color: var(--slate-400);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}

.kpi-card .kpi-value {
    color: var(--slate-50);
    font-size: 1.7rem;
    font-weight: 700;
    line-height: 1.2;
}

.kpi-card .kpi-sub {
    color: var(--slate-500);
    font-size: 0.72rem;
    margin-top: 4px;
    font-weight: 400;
}

/* --- Status Badge --- */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}

.status-badge.valid {
    background: rgba(16, 185, 129, 0.15);
    color: var(--green-400);
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-badge.partial {
    background: rgba(245, 158, 11, 0.15);
    color: var(--gold-400);
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.status-badge.invalid {
    background: rgba(239, 68, 68, 0.15);
    color: var(--red-400);
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.status-badge.neutral {
    background: rgba(148, 163, 184, 0.1);
    color: var(--slate-400);
    border: 1px solid rgba(148, 163, 184, 0.2);
}

/* --- Score Bar --- */
.score-bar-container {
    background: rgba(14, 26, 46, 0.6);
    border-radius: 10px;
    height: 14px;
    overflow: hidden;
    border: 1px solid rgba(30, 58, 95, 0.3);
    position: relative;
}

.score-bar-fill {
    height: 100%;
    border-radius: 10px;
    transition: width 0.8s ease;
    position: relative;
}

.score-bar-fill.high {
    background: linear-gradient(90deg, var(--green-500), var(--teal-400));
}

.score-bar-fill.medium {
    background: linear-gradient(90deg, var(--gold-500), var(--amber-500));
}

.score-bar-fill.low {
    background: linear-gradient(90deg, var(--red-500), #DC2626);
}

/* --- Info Card --- */
.info-card {
    background: rgba(26, 39, 66, 0.5);
    border: 1px solid rgba(30, 58, 95, 0.4);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}

.info-card .card-label {
    color: var(--slate-400);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}

.info-card .card-value {
    color: var(--slate-100);
    font-size: 0.92rem;
    font-weight: 500;
}

/* --- Reasoning Card --- */
.reasoning-item {
    background: rgba(14, 26, 46, 0.4);
    border: 1px solid rgba(30, 58, 95, 0.35);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
    transition: border-color 0.2s ease;
}

.reasoning-item:hover {
    border-color: rgba(13, 148, 136, 0.3);
}

.reasoning-item .ri-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

.reasoning-item .ri-icon {
    font-size: 1.1rem;
}

.reasoning-item .ri-type {
    color: var(--slate-300);
    font-size: 0.82rem;
    font-weight: 600;
}

.reasoning-item .ri-status {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 12px;
    margin-left: auto;
}

.reasoning-item .ri-status.match {
    background: rgba(16, 185, 129, 0.15);
    color: var(--green-400);
}

.reasoning-item .ri-status.partial {
    background: rgba(245, 158, 11, 0.15);
    color: var(--gold-400);
}

.reasoning-item .ri-status.mismatch {
    background: rgba(239, 68, 68, 0.15);
    color: var(--red-400);
}

.reasoning-item .ri-status.unknown {
    background: rgba(148, 163, 184, 0.1);
    color: var(--slate-400);
}

.reasoning-item .ri-notes {
    color: var(--slate-400);
    font-size: 0.8rem;
    line-height: 1.5;
    padding-left: 28px;
}

/* --- Candidate Card --- */
.candidate-card {
    background: linear-gradient(135deg, rgba(13, 148, 136, 0.08) 0%, rgba(26, 39, 66, 0.6) 100%);
    border: 1px solid rgba(13, 148, 136, 0.25);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}

.candidate-card .cc-title {
    color: var(--teal-400);
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}

.candidate-card .cc-name {
    color: var(--slate-50);
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 12px;
}

.candidate-card .cc-details {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}

.candidate-card .cc-field {
    display: flex;
    flex-direction: column;
}

.candidate-card .cc-field-label {
    color: var(--slate-500);
    font-size: 0.7rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.candidate-card .cc-field-value {
    color: var(--slate-300);
    font-size: 0.88rem;
    font-weight: 500;
    margin-top: 2px;
}

/* --- Vendor Card --- */
.vendor-card {
    background: linear-gradient(135deg, rgba(26, 39, 66, 0.7) 0%, rgba(14, 26, 46, 0.8) 100%);
    border: 1px solid rgba(30, 58, 95, 0.4);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    transition: all 0.3s ease;
}

.vendor-card:hover {
    border-color: rgba(13, 148, 136, 0.3);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

.vendor-card .vc-name {
    color: var(--slate-100);
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 4px;
}

.vendor-card .vc-location {
    color: var(--slate-400);
    font-size: 0.8rem;
    margin-bottom: 12px;
}

.vendor-card .vc-stats {
    display: flex;
    gap: 20px;
}

.vendor-card .vc-stat {
    display: flex;
    flex-direction: column;
}

.vendor-card .vc-stat-label {
    color: var(--slate-500);
    font-size: 0.68rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.vendor-card .vc-stat-value {
    color: var(--teal-400);
    font-size: 0.95rem;
    font-weight: 600;
}

/* --- Justification Preview --- */
.justification-preview {
    background: rgba(14, 26, 46, 0.5);
    border: 1px solid rgba(30, 58, 95, 0.4);
    border-radius: 12px;
    padding: 24px;
    font-size: 0.88rem;
    line-height: 1.7;
    color: var(--slate-300);
}

.justification-preview h4 {
    color: var(--teal-400) !important;
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    margin-top: 16px !important;
    margin-bottom: 8px !important;
}

.justification-preview .j-field {
    margin-bottom: 4px;
}

.justification-preview .j-label {
    color: var(--slate-500);
    font-weight: 500;
}

/* --- System Status Indicator --- */
.sys-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 500;
}

.sys-status.online {
    background: rgba(16, 185, 129, 0.1);
    color: var(--green-400);
}

.sys-status.offline {
    background: rgba(245, 158, 11, 0.1);
    color: var(--gold-400);
}

.sys-status .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
}

.sys-status.online .dot {
    background: var(--green-400);
    box-shadow: 0 0 6px var(--green-400);
    animation: pulse-dot 2s ease-in-out infinite;
}

.sys-status.offline .dot {
    background: var(--gold-400);
}

/* --- Footer --- */
.sipval-footer {
    text-align: center;
    color: var(--slate-500);
    font-size: 0.72rem;
    padding: 20px 0 10px 0;
    border-top: 1px solid rgba(30, 58, 95, 0.3);
    margin-top: 40px;
}

/* --- Animations --- */
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.fade-in {
    animation: fadeInUp 0.4s ease forwards;
}

/* --- Utility --- */
.spacer-sm { height: 8px; }
.spacer-md { height: 16px; }
.spacer-lg { height: 28px; }

.text-muted { color: var(--slate-400) !important; font-size: 0.82rem; }
.text-teal { color: var(--teal-400) !important; }
.text-gold { color: var(--gold-400) !important; }
.text-green { color: var(--green-400) !important; }
.text-red { color: var(--red-400) !important; }

/* ============================================================
   Procurement Items Table — Custom Interactive Table
   ============================================================ */

.proc-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 4px;
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
}

.proc-table-header {
    display: grid;
    grid-template-columns: 80px 1fr 140px 140px 110px 130px 200px;
    gap: 8px;
    padding: 10px 16px;
    background: rgba(14, 26, 46, 0.8);
    border: 1px solid rgba(30, 58, 95, 0.5);
    border-radius: 10px 10px 0 0;
    margin-bottom: 4px;
}

.proc-table-header-cell {
    color: var(--slate-400);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.proc-table-row {
    display: grid;
    grid-template-columns: 80px 1fr 140px 140px 110px 130px 200px;
    gap: 8px;
    align-items: center;
    padding: 12px 16px;
    background: linear-gradient(135deg, rgba(26, 39, 66, 0.5) 0%, rgba(14, 26, 46, 0.7) 100%);
    border: 1px solid rgba(30, 58, 95, 0.35);
    border-radius: 8px;
    margin-bottom: 3px;
    transition: all 0.2s ease;
    cursor: pointer;
}

.proc-table-row:hover {
    border-color: rgba(13, 148, 136, 0.35);
    background: linear-gradient(135deg, rgba(26, 39, 66, 0.7) 0%, rgba(14, 26, 46, 0.85) 100%);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.proc-table-row.selected {
    border-color: rgba(13, 148, 136, 0.6);
    background: linear-gradient(135deg, rgba(13, 148, 136, 0.08) 0%, rgba(14, 26, 46, 0.85) 100%);
    box-shadow: 0 4px 16px rgba(13, 148, 136, 0.12);
}

.proc-cell-id {
    color: var(--slate-500);
    font-size: 0.72rem;
    font-weight: 600;
    font-family: 'Inter', monospace;
}

.proc-cell-name {
    color: var(--slate-100);
    font-size: 0.84rem;
    font-weight: 500;
    line-height: 1.35;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

.proc-cell-category {
    color: var(--slate-400);
    font-size: 0.78rem;
}

.proc-cell-price {
    color: var(--gold-400);
    font-size: 0.82rem;
    font-weight: 600;
}

.confidence-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.02em;
}

.confidence-pill.high {
    background: rgba(16, 185, 129, 0.15);
    color: var(--green-400);
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.confidence-pill.medium {
    background: rgba(245, 158, 11, 0.15);
    color: var(--gold-400);
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.confidence-pill.low {
    background: rgba(239, 68, 68, 0.15);
    color: var(--red-400);
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.confidence-pill.none {
    background: rgba(148, 163, 184, 0.1);
    color: var(--slate-400);
    border: 1px solid rgba(148, 163, 184, 0.2);
}

/* ============================================================
   Detail Drawer
   ============================================================ */

.detail-drawer {
    background: linear-gradient(180deg, rgba(10, 22, 40, 0.95) 0%, rgba(6, 15, 30, 0.98) 100%);
    border: 1px solid rgba(13, 148, 136, 0.35);
    border-radius: 14px;
    padding: 0;
    margin: 12px 0 20px 0;
    overflow: hidden;
    animation: fadeInUp 0.35s ease forwards;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(13, 148, 136, 0.1);
}

.drawer-header {
    background: linear-gradient(135deg, rgba(13, 148, 136, 0.12) 0%, rgba(26, 39, 66, 0.6) 100%);
    border-bottom: 1px solid rgba(30, 58, 95, 0.4);
    padding: 20px 28px;
}

.drawer-section {
    padding: 20px 28px;
    border-bottom: 1px solid rgba(30, 58, 95, 0.25);
}

.drawer-section:last-child {
    border-bottom: none;
}

.drawer-section-title {
    color: var(--teal-400);
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ============================================================
   Extracted Specification Grid
   ============================================================ */

.spec-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
}

.spec-attr {
    background: rgba(26, 39, 66, 0.5);
    border: 1px solid rgba(30, 58, 95, 0.4);
    border-radius: 8px;
    padding: 10px 14px;
    transition: border-color 0.2s ease;
}

.spec-attr:hover {
    border-color: rgba(13, 148, 136, 0.3);
}

.spec-attr-label {
    color: var(--slate-500);
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
}

.spec-attr-value {
    color: var(--slate-200);
    font-size: 0.85rem;
    font-weight: 500;
    line-height: 1.4;
}

/* ============================================================
   Validation Checklist
   ============================================================ */

.checklist-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
}

.checklist-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 8px;
    border: 1px solid transparent;
    transition: all 0.2s ease;
}

.checklist-item.pass {
    background: rgba(16, 185, 129, 0.08);
    border-color: rgba(16, 185, 129, 0.25);
}

.checklist-item.review {
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.25);
}

.checklist-item.fail {
    background: rgba(239, 68, 68, 0.08);
    border-color: rgba(239, 68, 68, 0.25);
}

.checklist-item.unknown {
    background: rgba(148, 163, 184, 0.05);
    border-color: rgba(148, 163, 184, 0.15);
}

.checklist-icon {
    font-size: 1rem;
    flex-shrink: 0;
}

.checklist-label {
    font-size: 0.82rem;
    font-weight: 500;
    flex: 1;
}

.checklist-item.pass .checklist-label { color: var(--green-400); }
.checklist-item.review .checklist-label { color: var(--gold-400); }
.checklist-item.fail .checklist-label { color: var(--red-400); }
.checklist-item.unknown .checklist-label { color: var(--slate-400); }

.checklist-status-text {
    font-size: 0.67rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 2px 8px;
    border-radius: 10px;
}

.checklist-item.pass .checklist-status-text {
    background: rgba(16, 185, 129, 0.15);
    color: var(--green-400);
}
.checklist-item.review .checklist-status-text {
    background: rgba(245, 158, 11, 0.15);
    color: var(--gold-400);
}
.checklist-item.fail .checklist-status-text {
    background: rgba(239, 68, 68, 0.15);
    color: var(--red-400);
}
.checklist-item.unknown .checklist-status-text {
    background: rgba(148, 163, 184, 0.1);
    color: var(--slate-400);
}

/* ============================================================
   Candidate Comparison Table
   ============================================================ */

.cand-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 4px;
}

.cand-table-header {
    display: grid;
    grid-template-columns: 90px 130px 1fr 110px 130px 90px 110px 110px 120px;
    gap: 6px;
    padding: 8px 14px;
    background: rgba(14, 26, 46, 0.8);
    border-radius: 8px;
    margin-bottom: 4px;
}

.cand-table-header-cell {
    color: var(--slate-500);
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.cand-table-row {
    display: grid;
    grid-template-columns: 90px 130px 1fr 110px 130px 90px 110px 110px 120px;
    gap: 6px;
    align-items: center;
    padding: 10px 14px;
    background: rgba(26, 39, 66, 0.4);
    border: 1px solid rgba(30, 58, 95, 0.3);
    border-radius: 8px;
    margin-bottom: 3px;
    transition: border-color 0.2s ease;
}

.cand-table-row:hover {
    border-color: rgba(13, 148, 136, 0.3);
    background: rgba(26, 39, 66, 0.6);
}

.cand-table-row.selected-cand {
    border-color: rgba(16, 185, 129, 0.5);
    background: rgba(16, 185, 129, 0.05);
}

.cand-table-row.rejected-cand {
    opacity: 0.4;
    border-color: rgba(239, 68, 68, 0.3);
}

.source-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.67rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.source-badge.inaproc {
    background: rgba(13, 148, 136, 0.2);
    color: var(--teal-400);
    border: 1px solid rgba(13, 148, 136, 0.35);
}

.source-badge.tokopedia {
    background: rgba(78, 205, 196, 0.12);
    color: #4ECDC4;
    border: 1px solid rgba(78, 205, 196, 0.25);
}

.source-badge.shopee {
    background: rgba(245, 101, 39, 0.12);
    color: #F5652A;
    border: 1px solid rgba(245, 101, 39, 0.25);
}

.source-badge.vendor {
    background: rgba(245, 158, 11, 0.12);
    color: var(--gold-400);
    border: 1px solid rgba(245, 158, 11, 0.25);
}

.location-badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.67rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.location-badge.jakarta {
    background: rgba(99, 102, 241, 0.15);
    color: #818CF8;
    border: 1px solid rgba(99, 102, 241, 0.25);
}

.location-badge.jabodetabek {
    background: rgba(139, 92, 246, 0.12);
    color: #A78BFA;
    border: 1px solid rgba(139, 92, 246, 0.22);
}

.location-badge.national {
    background: rgba(148, 163, 184, 0.1);
    color: var(--slate-400);
    border: 1px solid rgba(148, 163, 184, 0.2);
}

.deviation-cell {
    font-size: 0.8rem;
    font-weight: 700;
}

.deviation-cell.positive { color: var(--red-400); }
.deviation-cell.negative { color: var(--green-400); }
.deviation-cell.neutral { color: var(--slate-400); }

/* ============================================================
   Procurement Reasoning Block
   ============================================================ */

.reasoning-block {
    background: linear-gradient(135deg, rgba(13, 148, 136, 0.06) 0%, rgba(26, 39, 66, 0.5) 100%);
    border: 1px solid rgba(13, 148, 136, 0.2);
    border-radius: 10px;
    padding: 18px 22px;
}

.reasoning-verdict {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 5px 14px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 14px;
}

.reasoning-verdict.valid {
    background: rgba(16, 185, 129, 0.15);
    color: var(--green-400);
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.reasoning-verdict.partial {
    background: rgba(245, 158, 11, 0.15);
    color: var(--gold-400);
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.reasoning-verdict.invalid {
    background: rgba(239, 68, 68, 0.15);
    color: var(--red-400);
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.reasoning-bullet {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 5px 0;
    color: var(--slate-300);
    font-size: 0.82rem;
    line-height: 1.5;
}

.reasoning-bullet::before {
    content: '→';
    color: var(--teal-500);
    font-weight: 600;
    flex-shrink: 0;
    margin-top: 1px;
}

.reasoning-summary {
    margin-top: 14px;
    padding: 12px 14px;
    background: rgba(14, 26, 46, 0.5);
    border-radius: 8px;
    border-left: 3px solid var(--teal-600);
    color: var(--slate-300);
    font-size: 0.83rem;
    line-height: 1.6;
    font-style: italic;
}

/* ============================================================
   High Deviation Warning
   ============================================================ */

.deviation-warning {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(14, 26, 46, 0.7) 100%);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 10px;
    padding: 16px 20px;
    margin-top: 12px;
}

.deviation-warning-title {
    color: var(--gold-400);
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.deviation-warning-reason {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 3px 0;
    color: var(--slate-400);
    font-size: 0.8rem;
    line-height: 1.5;
}

.deviation-warning-reason::before {
    content: '•';
    color: var(--gold-500);
    flex-shrink: 0;
}

/* ============================================================
   Item Info Header (in Drawer)
   ============================================================ */

.drawer-item-header {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin-top: 14px;
}

.drawer-info-block {
    display: flex;
    flex-direction: column;
}

.drawer-info-label {
    color: var(--slate-500);
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 4px;
}

.drawer-info-value {
    color: var(--slate-100);
    font-size: 0.9rem;
    font-weight: 600;
    line-height: 1.35;
}

.drawer-info-value.price {
    color: var(--gold-400);
    font-size: 1.05rem;
}

/* ============================================================
   Savings Banner — Dashboard business value highlight
   ============================================================ */

.savings-banner {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.10) 0%, rgba(251, 191, 36, 0.05) 60%, rgba(14, 26, 46, 0.4) 100%);
    border: 1px solid rgba(245, 158, 11, 0.30);
    border-left: 4px solid var(--gold-500);
    border-radius: 12px;
    padding: 18px 28px;
    margin: 16px 0;
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
}

.savings-banner .sb-icon {
    font-size: 2.2rem;
    flex-shrink: 0;
}

.savings-banner .sb-block {
    display: flex;
    flex-direction: column;
    min-width: 120px;
}

.savings-banner .sb-label {
    color: var(--slate-400);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 3px;
}

.savings-banner .sb-value {
    color: var(--gold-400);
    font-size: 1.45rem;
    font-weight: 800;
    line-height: 1.1;
}

.savings-banner .sb-sub {
    color: var(--slate-500);
    font-size: 0.72rem;
    margin-top: 3px;
}

.savings-banner .sb-divider {
    width: 1px;
    height: 52px;
    background: rgba(245, 158, 11, 0.2);
    flex-shrink: 0;
}

.savings-banner .sb-message {
    flex: 1;
    color: var(--slate-300);
    font-size: 0.85rem;
    line-height: 1.5;
    min-width: 200px;
}

.savings-banner .sb-message strong {
    color: var(--gold-300);
}

/* ============================================================
   Kewajaran Chip — inline SHBJ status indicator
   ============================================================ */

.kewajaran-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    vertical-align: middle;
}

.kewajaran-chip.wajar {
    background: rgba(16, 185, 129, 0.15);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.30);
}

.kewajaran-chip.perhatian {
    background: rgba(245, 158, 11, 0.15);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.30);
}

.kewajaran-chip.deviasi {
    background: rgba(239, 68, 68, 0.15);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.30);
}

/* ============================================================
   App Shell — Top-level layout wrapper
   ============================================================ */

.app-shell {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ============================================================
   Topbar — Page-level header strip
   ============================================================ */

.topbar {
    background: linear-gradient(135deg, rgba(13, 148, 136, 0.10) 0%, rgba(245, 158, 11, 0.04) 100%);
    border: 1px solid rgba(13, 148, 136, 0.18);
    border-radius: 14px;
    padding: 16px 24px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
}

.topbar-title {
    background: linear-gradient(135deg, var(--teal-400), var(--gold-400));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 0;
}

.topbar-subtitle {
    color: var(--slate-400);
    font-size: 0.82rem;
    margin-top: 2px;
}

.topbar-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

/* ============================================================
   Detail Grid — Two-column enterprise item detail layout
   ============================================================ */

.detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 16px;
}

.detail-grid-left,
.detail-grid-right {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.detail-card {
    background: linear-gradient(135deg, rgba(26, 39, 66, 0.6) 0%, rgba(14, 26, 46, 0.8) 100%);
    border: 1px solid rgba(30, 58, 95, 0.4);
    border-radius: 12px;
    padding: 20px 24px;
    transition: border-color 0.2s ease;
}

.detail-card:hover {
    border-color: rgba(13, 148, 136, 0.25);
}

.detail-card-title {
    color: var(--teal-400);
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 7px;
}

@media (max-width: 900px) {
    .detail-grid {
        grid-template-columns: 1fr;
    }
}

/* ============================================================
   Comparison Table — Standalone wrapper for candidate tables
   ============================================================ */

.comparison-table {
    background: rgba(14, 26, 46, 0.4);
    border: 1px solid rgba(30, 58, 95, 0.35);
    border-radius: 12px;
    overflow: hidden;
    margin: 8px 0;
}

.comparison-table-header {
    background: rgba(14, 26, 46, 0.7);
    padding: 10px 16px;
    border-bottom: 1px solid rgba(30, 58, 95, 0.4);
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.comparison-table-title {
    color: var(--teal-400);
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.comparison-table-count {
    color: var(--slate-500);
    font-size: 0.72rem;
    font-weight: 500;
}

.comparison-table-body {
    padding: 12px 16px;
}

/* ============================================================
   Reasoning Box — Standalone procurement reasoning block
   ============================================================ */

.reasoning-box {
    background: linear-gradient(135deg, rgba(13, 148, 136, 0.07) 0%, rgba(26, 39, 66, 0.55) 100%);
    border: 1px solid rgba(13, 148, 136, 0.22);
    border-left: 4px solid var(--teal-600);
    border-radius: 10px;
    padding: 18px 22px;
    margin: 8px 0;
}

.reasoning-box-title {
    color: var(--teal-400);
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.reasoning-box-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 8px;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
}

.reasoning-box-status.valid {
    background: rgba(16, 185, 129, 0.15);
    color: var(--green-400);
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.reasoning-box-status.partial {
    background: rgba(245, 158, 11, 0.15);
    color: var(--gold-400);
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.reasoning-box-status.invalid {
    background: rgba(239, 68, 68, 0.15);
    color: var(--red-400);
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.reasoning-box-note {
    color: var(--slate-400);
    font-size: 0.82rem;
    line-height: 1.6;
    margin-top: 10px;
    padding: 10px 14px;
    background: rgba(14, 26, 46, 0.4);
    border-radius: 8px;
    font-style: italic;
}

</style>
"""

