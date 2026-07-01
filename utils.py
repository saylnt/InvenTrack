import json
import os
import csv
from datetime import datetime
import math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')
SALES_FILE = os.path.join(DATA_DIR, 'sales.json')
ACCOUNT_FILE = os.path.join(DATA_DIR, 'account.json')

# --- 1. Fungsi Input/Output File ---
def read_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        return json.load(f)

def write_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def get_account():
    if not os.path.exists(ACCOUNT_FILE):
        return {"email": "khash.elektronik@gmail.com", "password": "admin123", "language": "id"}
    with open(ACCOUNT_FILE, 'r') as f:
        return json.load(f)

def save_account(data):
    with open(ACCOUNT_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- 2. Logika Pengambilan Keputusan (If-Else) & Fungsi ---
def get_safety_stock_status(stock, safety_stock_limit):
    """
    Menentukan status stok (aman, cukup, terbatas).
    Mengembalikan Tuple (status_text, color_class)
    """
    if stock <= 5:
        return ("Terbatas", "danger") # Merah
    elif 6 <= stock <= 9:
        return ("Cukup", "warning") # Kuning
    else: # 10 - 20+
        return ("Aman", "success") # Hijau

def format_currency(amount):
    return f"Rp {amount:,.0f}".replace(',', '.')

# --- Image upload helpers ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file_storage):
    """Save uploaded image to static/uploads with a unique name and return the relative path."""
    import uuid, os
    if file_storage and allowed_file(file_storage.filename):
        ext = file_storage.filename.rsplit('.', 1)[1].lower()
        filename = f"prod_{uuid.uuid4().hex}.{ext}"
        upload_dir = os.path.join(BASE_DIR, 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        file_storage.save(filepath)
        # Return relative path for HTML usage
        return f"uploads/{filename}"
    return None

def calculate_total_revenue(sales_data):
    """Menggunakan list comprehension dan sum"""
    return sum(sales_data.values())

def get_inventory():
    return read_json(INVENTORY_FILE)

def save_inventory(data):
    write_json(INVENTORY_FILE, data)

def get_history():
    return read_json(HISTORY_FILE)

def add_history(type_trans, items):
    # type_trans: "IN" or "OUT"
    # items: list of dicts {"name": "...", "qty": x}
    history = get_history()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    
    entry = {
        "date": date_str,
        "type": type_trans,
        "items": items
    }
    history.append(entry)
    write_json(HISTORY_FILE, history)

def get_sales():
    if not os.path.exists(SALES_FILE):
        return {}
    with open(SALES_FILE, 'r') as f:
        return json.load(f)

def add_sales_amount(amount):
    sales = get_sales()
    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    
    if month_key in sales:
        sales[month_key] += amount
    else:
        sales[month_key] = amount
        
    write_json(SALES_FILE, sales)

def export_history_to_csv(filepath):
    history = get_history()
    sales = get_sales()
    
    with open(filepath, mode='w', newline='') as file:
        writer = csv.writer(file)
        
        writer.writerow(["=== LAPORAN TRANSAKSI BARANG ==="])
        writer.writerow(["Tanggal", "Tipe (IN/OUT)", "Barang", "Jumlah"])
        for h in history:
            date = h.get('date', '')
            trans_type = h.get('type', '')
            for item in h.get('items', []):
                writer.writerow([date, trans_type, item.get('name'), item.get('qty')])
                
        writer.writerow([])
        writer.writerow(["=== LAPORAN KEUNTUNGAN / KERUGIAN (RUGI LABA) ==="])
        writer.writerow(["Bulan", "Penjualan (Sales)", "Pembelian (Purchase)", "Laba/Rugi", "Status"])
        for month, data in sales.items():
            if data['sales'] == 0 and data['purchase'] == 0:
                continue
            s = data['sales']
            p = data['purchase']
            diff = s - p
            status = "Untung" if diff >= 0 else "Rugi"
            writer.writerow([month, s, p, diff, status])

def apply_fifo(product_name, qty_out):
    """
    Simulasi sederhana logika FIFO jika stok dicatat per batch masuk.
    Untuk saat ini, kita kurangi stok di inventory secara langsung.
    """
    inventory = get_inventory()
    for item in inventory:
        if item['name'] == product_name:
            if item['stock'] >= qty_out:
                item['stock'] -= qty_out
                save_inventory(inventory)
                return True
            else:
                return False
    return False

