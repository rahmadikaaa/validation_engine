import json
from cognition.reasoning_engine import run_reasoning

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
    ,
    {
        "name": "INVALID - Kontainer kapasitas dan plat berbeda",
        "item": {
            "id_item": "226130",
            "nama_barang": "Bak Kontainer Sampah 10 m3",
            "spesifikasi": "kapasitas 10 m3 ukuran P 3.60M L 2.30M T 1.55M plat 2 mm lantai 3 mm",
            "kategori": "Alat Kebersihan",
            "subkategori": "Kontainer Sampah",
            "satuan": "unit",
            "harga_satuan": None
        },
        "candidate": {
            "nama_produk": "Bak Sampah Container 6 m3",
            "spesifikasi": "kapasitas 6 m3 plat 1.2 mm",
            "vendor": "Vendor X",
            "satuan": "unit",
            "harga": 12000000
        },
        "expected": "INVALID"
    },
    {
        "name": "PARTIAL - Mesin bevel thickness lebih rendah",
        "item": {
            "id_item": "227485",
            "nama_barang": "Mesin Potong Plat Bevel",
            "spesifikasi": "power source AC 220V cutting speed 50-750 mm/min cutting thickness 5-100 mm groove angle 0-45 degree",
            "kategori": "Peralatan Mesin",
            "subkategori": "Mesin Industri",
            "satuan": "unit",
            "harga_satuan": None
        },
        "candidate": {
            "nama_produk": "Mesin Bevel Plate Cutter",
            "spesifikasi": "AC 220V cutting speed 50-750 mm/min cutting thickness 5-80 mm groove angle 0-45 degree",
            "vendor": "Vendor Y",
            "satuan": "unit",
            "harga": 25000000
        },
        "expected": "PARTIAL_MATCH"
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

