# AI-Assisted Procurement Validation System

Automated procurement item validation through specification extraction, internal comparison search, and deviation analysis — built with Streamlit.

---

## Project Overview

This system helps procurement surveyors and analysts validate benchmark comparison items more efficiently and consistently.

Instead of only searching for the cheapest product, the system focuses on:

- Specification extraction and normalization
- Dimension, function, material, and grade matching
- Automated comparison candidate generation
- Match scoring and validation status
- Price deviation context

The long-term vision is to build an intelligent procurement validation assistant capable of evaluating benchmark items faster and more accurately, eventually integrating with INAPROC and marketplace APIs.

---

## Current MVP Flow

```text
User uploads procurement file (CSV/Excel)
        ↓
System parses items (flexible header detection)
        ↓
System splits nama_barang + spesifikasi
        ↓
Internal placeholder search generates comparison candidates
        ↓
Reasoning engine validates each candidate match
        ↓
System picks best match per item
        ↓
Structured output table with status, score, and deviation notes
```

> **Note:** The current MVP uses internally generated placeholder comparison data.
> Real INAPROC/API/marketplace integration is planned for a future phase.

---

## How to Run Locally

### Prerequisites

- Python 3.10+
- pip

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

### Run Regression Tests

```bash
python -m cognition.regression_test
```

---

## Input Format

### Recommended: Clean CSV

Export your procurement spreadsheet from Google Sheets or Excel as CSV. The CSV should contain these columns:

| Column | Required | Description |
|---|---|---|
| `nama_barang` | ✅ | Item name |
| `spesifikasi` | Optional | Technical specifications |
| `kategori` | Optional | Item category |
| `subkategori` | Optional | Item subcategory |
| `satuan` | Optional | Unit of measure |
| `harga_satuan` | Optional | Reference unit price |

### Also Supported: SHBJ Excel Format

The system can also parse SHBJ-format Excel files with merged/offset headers. It will:

- Auto-detect the correct header row
- Map `Nama Barang dan Spesifikasi` → `nama_barang` + `spesifikasi`
- Map `Kategori`, `Sub kategori`, `Satuan`, `Harga Satuan` to their expected keys
- Drop rows where the item name is empty or NaN

---

## Architecture Overview

```text
automationSurvey/
├── app.py                              # Streamlit UI (single-upload MVP)
├── cognition/
│   ├── __init__.py
│   ├── reasoning_engine.py             # Core validation logic (unchanged)
│   ├── candidate_generator.py          # Internal placeholder search
│   └── regression_test.py              # Validation regression tests
├── requirements.txt                    # Python dependencies
└── README.md
```

### Key Components

| File | Role |
|---|---|
| `app.py` | Streamlit dashboard — file upload, parsing, column normalization, orchestration, results display |
| `reasoning_engine.py` | Pure-function reasoning: dimension match, function match, material equivalence, industrial grade check, unit match, final status |
| `candidate_generator.py` | Internal placeholder that generates deterministic mock comparison candidates per item (future: replaced by INAPROC/marketplace search) |
| `regression_test.py` | 5 test cases validating reasoning engine accuracy |

---

## Output Columns

The validation results table contains:

| Column | Description |
|---|---|
| `id_item` | Procurement item ID |
| `nama_barang` | Cleaned item name |
| `satuan` | Unit of measure |
| `harga_satuan` | Reference price from procurement input |
| `comparison_product` | Best matching comparison product name |
| `comparison_specification` | Comparison product specification |
| `vendor` | Comparison vendor |
| `comparison_price` | Comparison product price |
| `status` | `VALID`, `PARTIAL_MATCH`, or `INVALID` |
| `score` | Match score (0.0 – 1.0) |
| `deviation_notes` | Reasoning notes on deviations |

---

## Known Limitations

- **Placeholder comparison data only** — Comparison candidates are generated internally from the item's own specifications, not from real market data.
- **No real INAPROC/API integration yet** — The placeholder generator is a stand-in for future marketplace/API search.
- **No BigQuery integration yet** — Data processing is fully local.
- **Reasoning regression: 3/5 passing** — Two test cases (kontainer capacity mismatch, mesin bevel thickness) produce incorrect VALID status due to pre-existing reasoning logic limitations.
- **No price deviation calculation** — Harga deviation between reference and comparison prices is not yet computed.

---

## Next Roadmap

1. **Fix reasoning engine** — Improve dimension-aware validation for container capacity and machine spec ranges.
2. **INAPROC/marketplace integration** — Replace placeholder generator with real comparison search.
3. **Price deviation calculation** — Compute and display percentage deviation between reference and comparison prices.
4. **BigQuery integration** — Centralized data storage for procurement items and validation results.
5. **Export functionality** — Allow downloading validation results as CSV/Excel.
6. **Multi-user support** — Surveyor identification and session management.
