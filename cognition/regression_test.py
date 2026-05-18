import json
from reasoning_engine import run_reasoning

test_cases = [
    {
        "name": "VALID - Ban Tubeless 265/60 R18",
        "item": {
            "id_item": "212850",
            "nama_barang": "Ban Tubeless",
            "spesifikasi": "Ukuran 265/60 R18",
            "kategori": "Suku Cadang Alat Angkutan",
            "subkategori": "Suku Cadang Alat Angkutan Darat Bermotor",
            "satuan": "pcs",
            "harga_satuan": 2069500
        },
        "candidate": {
            "nama_produk": "Ban Tubeless 265/60 R18",
            "spesifikasi": "Ukuran 265/60 R18 tubeless",
            "vendor": "Sample Vendor",
            "satuan": "pcs",
            "harga": 1800000
        },
        "expected": "VALID"
    },
    {
        "name": "PARTIAL - Ban Tubeless beda aspect ratio",
        "item": {
            "id_item": "212850",
            "nama_barang": "Ban Tubeless",
            "spesifikasi": "Ukuran 265/60 R18",
            "kategori": "Suku Cadang Alat Angkutan",
            "subkategori": "Suku Cadang Alat Angkutan Darat Bermotor",
            "satuan": "pcs",
            "harga_satuan": 2069500
        },
        "candidate": {
            "nama_produk": "Ban Tubeless 265/65 R18",
            "spesifikasi": "Ukuran 265/65 R18 tubeless",
            "vendor": "Sample Vendor",
            "satuan": "pcs",
            "harga": 1750000
        },
        "expected": "PARTIAL_MATCH"
    },
    {
        "name": "INVALID - Ban motor beda ukuran",
        "item": {
            "id_item": "212850",
            "nama_barang": "Ban Tubeless",
            "spesifikasi": "Ukuran 265/60 R18",
            "kategori": "Suku Cadang Alat Angkutan",
            "subkategori": "Suku Cadang Alat Angkutan Darat Bermotor",
            "satuan": "pcs",
            "harga_satuan": 2069500
        },
        "candidate": {
            "nama_produk": "Ban Motor 80/100-17",
            "spesifikasi": "Ban motor ukuran 80/100-17",
            "vendor": "Sample Vendor",
            "satuan": "pcs",
            "harga": 300000
        },
        "expected": "INVALID"
    }
]

passed = 0

for case in test_cases:
    result = run_reasoning(case["item"], case["candidate"])
    actual = result["candidate_evaluation"]["candidate_status"]

    ok = actual == case["expected"]
    status = "PASS" if ok else "FAIL"

    print("=" * 80)
    print(f"{status} | {case['name']}")
    print(f"Expected: {case['expected']}")
    print(f"Actual  : {actual}")
    print(f"Score   : {result['candidate_evaluation']['match_score']}")

    if not ok:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    if ok:
        passed += 1

print("=" * 80)
print(f"REGRESSION RESULT: {passed}/{len(test_cases)} passed")

