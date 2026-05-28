import random
from typing import Dict, Any, List

def generate_placeholder_candidates(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Internal placeholder search function.
    Simulates finding candidate comparison products from an API or marketplace.
    Generates 3 synthetic candidates based on the input item specifications.
    """
    
    # Extract details from input, handling both expected column names and the combined Excel column
    nama_barang = str(item.get("nama_barang") or item.get("Nama Barang dan Spesifikasi") or "Item Unknown")
    spesifikasi = str(item.get("spesifikasi") or "")
    
    satuan = str(item.get("satuan") or item.get("Satuan") or "unit")
    
    # Combined description if spesifikasi is empty (common in the Excel format)
    full_desc = nama_barang if not spesifikasi else f"{nama_barang} {spesifikasi}"
    
    candidates = []
    
    # Candidate 1: Strong Match (Exact or very close)
    candidates.append({
        "nama_produk": f"{nama_barang} (Placeholder Match)",
        "spesifikasi": f"{spesifikasi} (Vendor Spec)" if spesifikasi else f"Spesifikasi sesuai {nama_barang}",
        "vendor": "Vendor A (Mock)",
        "satuan": satuan,
        "harga": random.randint(100000, 5000000)
    })
    
    # Candidate 2: Partial Match (Slightly altered name/spec)
    candidates.append({
        "nama_produk": f"{nama_barang} - Alternatif",
        "spesifikasi": f"{spesifikasi} (Beda Merk/Grade)" if spesifikasi else f"Spesifikasi mirip {nama_barang}",
        "vendor": "Vendor B (Mock)",
        "satuan": satuan,
        "harga": random.randint(100000, 5000000)
    })
    
    # Candidate 3: Weak Match / Different Grade
    candidates.append({
        "nama_produk": f"Produk Serupa {nama_barang.split()[0] if nama_barang.split() else 'Umum'}",
        "spesifikasi": "Spesifikasi standar (Consumer Grade)",
        "vendor": "Vendor C (Mock)",
        "satuan": satuan,
        "harga": random.randint(50000, 2000000)
    })
    
    return candidates
