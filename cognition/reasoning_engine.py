import json
import re
from typing import Dict, Any, List


def extract_dimensions(text: str) -> List[str]:
    patterns = [
        r"\d+[/.,]?\d*\s*x\s*\d+[/.,]?\d*",
        r"\d+[/.,]?\d*\s*(mm|cm|m|inch|in|r\d+\.?\d*)",
        r"\d+[/.,]?\d*\s*/\s*\d+\s*r\d+",
        r"\d+\.?\d*-\d+",
        r"\d+\s*pr",
        r"\d+\s*m3",
    ]

    found = []

    for p in patterns:
        found += re.findall(p, text.lower())

    return list(set([str(x) for x in found]))


def summarize_item(item: Dict[str, Any]) -> Dict[str, Any]:

    text = f"""
    {item.get('nama_barang', '')}
    {item.get('spesifikasi', '')}
    {item.get('kategori', '')}
    {item.get('subkategori', '')}
    """.lower()

    if "ban" in text:

        product_type = "vehicle tire"

        main_function = (
            "sebagai komponen roda kendaraan untuk menopang beban dan traksi"
        )

        critical_criteria = [
            "ukuran ban",
            "tipe tubeless/non-tubeless",
            "PR/load rating",
            "brand equivalence",
            "satuan",
        ]

        mismatch_risks = [
            "ukuran ring berbeda",
            "load rating tidak sesuai",
            "ban consumer dipakai untuk kebutuhan heavy duty",
            "satuan tidak sama",
        ]

    elif "kontainer" in text or "container" in text:

        product_type = "industrial waste/container equipment"

        main_function = (
            "penampungan dan pengangkutan material/sampah dalam kapasitas besar"
        )

        critical_criteria = [
            "kapasitas",
            "dimensi",
            "ketebalan plat",
            "struktur rangka",
            "material",
            "scope pekerjaan",
        ]

        mismatch_risks = [
            "kapasitas berbeda",
            "plat lebih tipis",
            "rangka lebih ringan",
            "bukan industrial grade",
            "tidak termasuk pemasangan",
        ]

    elif "mesin" in text:

        product_type = "industrial machine/equipment"

        main_function = (
            "alat kerja teknis untuk proses pemotongan/pengerjaan material"
        )

        critical_criteria = [
            "power source",
            "kapasitas kerja",
            "cutting speed",
            "cutting thickness",
            "angle/range",
            "industrial grade",
        ]

        mismatch_risks = [
            "kapasitas kerja berbeda",
            "spesifikasi daya tidak sesuai",
            "consumer grade",
            "range kerja lebih rendah",
        ]

    else:

        product_type = "general procurement item"

        main_function = "fungsi mengikuti spesifikasi teknis barang"

        critical_criteria = [
            "fungsi",
            "dimensi",
            "material",
            "satuan",
            "brand equivalence",
        ]

        mismatch_risks = [
            "nama mirip tetapi fungsi berbeda",
            "spesifikasi kurang lengkap",
            "material tidak setara",
        ]

    return {
        "product_type": product_type,
        "main_function": main_function,
        "important_parameters": critical_criteria,
        "risk_of_mismatch": mismatch_risks,
        "detected_dimensions_or_specs": extract_dimensions(text),
    }


def evaluate_candidate(
    item: Dict[str, Any],
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    item_text = f"""
    {item.get('nama_barang', '')}
    {item.get('spesifikasi', '')}
    """.lower()

    cand_text = f"""
    {candidate.get('nama_produk', '')}
    {candidate.get('spesifikasi', '')}
    """.lower()

    reasoning = []
    score = 0

    item_dims = extract_dimensions(item_text)
    matched_dims = [d for d in item_dims if d in cand_text]

    # DIMENSION MATCH
    if item_dims and matched_dims:

        score += 30

        reasoning.append({
            "type": "dimension_match",
            "status": "match",
            "notes": f"Parameter ukuran/spesifikasi ditemukan cocok: {matched_dims}"
        })

    elif item_dims:

        reasoning.append({
            "type": "dimension_match",
            "status": "mismatch",
            "notes": (
                f"Item membutuhkan parameter {item_dims}, "
                "tetapi tidak jelas cocok pada kandidat."
            )
        })

    else:

        reasoning.append({
            "type": "dimension_match",
            "status": "unknown",
            "notes": "Parameter dimensi eksplisit tidak cukup terbaca."
        })

    # FUNCTION MATCH
    main_keywords = [
        "ban",
        "kontainer",
        "mesin",
        "plat",
        "tubeless",
        "motorized",
    ]

    matched_keywords = [
        k for k in main_keywords
        if k in item_text and k in cand_text
    ]

    if matched_keywords:

        score += 25

        reasoning.append({
            "type": "function_match",
            "status": "match",
            "notes": (
                "Fungsi/nama utama selaras melalui keyword: "
                f"{matched_keywords}"
            )
        })

    else:

        reasoning.append({
            "type": "function_match",
            "status": "mismatch",
            "notes": (
                "Fungsi utama kandidat belum terbukti sama "
                "dengan item procurement."
            )
        })

    # MATERIAL MATCH
    material_keywords = [
        "steel",
        "plat",
        "besi",
        "karet",
        "kuningan",
        "unp",
    ]

    material_match = [
        m for m in material_keywords
        if m in item_text and m in cand_text
    ]

    if material_match:

        score += 15

        reasoning.append({
            "type": "material_equivalence",
            "status": "match",
            "notes": (
                "Material/komponen teknis terindikasi setara: "
                f"{material_match}"
            )
        })

    else:

        reasoning.append({
            "type": "material_equivalence",
            "status": "partial",
            "notes": (
                "Material kandidat belum cukup lengkap "
                "untuk memastikan kesetaraan."
            )
        })

    # INDUSTRIAL GRADE
    industrial_terms = [
        "industrial",
        "heavy duty",
        "16 pr",
        "8pr",
        "plat",
        "mesin",
    ]

    industrial_match = [
        t for t in industrial_terms
        if t in item_text and t in cand_text
    ]

    if industrial_match:

        score += 15

        reasoning.append({
            "type": "industrial_vs_consumer_grade",
            "status": "match",
            "notes": (
                "Indikasi grade teknis/industrial ditemukan: "
                f"{industrial_match}"
            )
        })

    else:

        reasoning.append({
            "type": "industrial_vs_consumer_grade",
            "status": "partial",
            "notes": (
                "Belum cukup bukti apakah kandidat "
                "setara secara industrial grade."
            )
        })

    # UNIT MATCH
    same_unit = (
        item.get("satuan", "").lower()
        == candidate.get("satuan", "").lower()
    )

    if same_unit and item.get("satuan"):

        score += 15

        reasoning.append({
            "type": "quantity_or_unit",
            "status": "match",
            "notes": f"Satuan sama: {item.get('satuan')}"
        })

    else:

        reasoning.append({
            "type": "quantity_or_unit",
            "status": "partial",
            "notes": (
                "Satuan tidak tersedia atau belum terbukti sama."
            )
        })

       # FINAL STATUS
    is_tire_item = "ban" in item_text
    has_function_match = bool(matched_keywords)

    full_tire_size_pattern = r"\d+[/]\d+\s*r\d+"

    item_tire_sizes = re.findall(full_tire_size_pattern, item_text)
    cand_tire_sizes = re.findall(full_tire_size_pattern, cand_text)

    has_exact_tire_size_match = (
        bool(item_tire_sizes)
        and any(size in cand_tire_sizes for size in item_tire_sizes)
    )

    has_dimension_match = bool(matched_dims)

    if is_tire_item and item_tire_sizes:
        has_dimension_match = has_exact_tire_size_match

    if (
        is_tire_item
        and has_dimension_match
        and has_function_match
        and same_unit
    ):
        status = "VALID"

    elif score >= 80:
        status = "VALID"

    elif score >= 45:
        status = "PARTIAL_MATCH"

    else:
        status = "INVALID"

    return {
        "candidate_status": status,
        "match_score": round(score / 100, 2),
        "reasoning": reasoning,
        "deviation_notes": [
            "Deviasi harga belum dihitung karena harga referensi belum tersedia.",
            (
                "Jika harga berbeda jauh, cek perbedaan material, "
                "grade, brand, kapasitas, dan scope pekerjaan."
            )
        ]
    }

def run_reasoning(
    item: Dict[str, Any],
    candidate: Dict[str, Any]
) -> Dict[str, Any]:

    return {
        "item_summary": summarize_item(item),
        "critical_criteria": summarize_item(item)["important_parameters"],
        "candidate_evaluation": evaluate_candidate(item, candidate),
    }


if __name__ == "__main__":

    procurement_item = {
        "id_item": "213661",
        "nama_barang": "Ban Gerobak Motor",
        "spesifikasi": (
            "Ukuran 4.00-8 8PR, "
            "Komplit set termasuk ban luar & dalam"
        ),
        "kategori": "Suku Cadang Alat Angkutan",
        "subkategori": "Suku Cadang Alat Angkutan Darat Bermotor",
        "satuan": "set",
    }

    candidate_item = {
        "nama_produk": (
            "Ban Gerobak Motor 4.00-8 "
            "8PR Set Ban Luar Dalam"
        ),
        "spesifikasi": (
            "Ukuran 4.00-8, 8PR, "
            "terdiri dari ban luar dan ban dalam"
        ),
        "vendor": "Sample Vendor",
        "satuan": "set",
        "harga": 250000,
    }

    result = run_reasoning(procurement_item, candidate_item)

    print(json.dumps(result, indent=2, ensure_ascii=False))