from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import os
import random
from utils import (
    get_inventory, save_inventory, get_history, add_history, 
    get_sales, add_sales_amount, format_currency, 
    get_safety_stock_status, export_history_to_csv, apply_fifo,
    get_account, save_account, save_image
)

app = Flask(__name__)
app.secret_key = 'inventrack_secret_key_123'

# --- 3. Modul atau Pustaka Bawaan (random) ---
def generate_transaction_id():
    return f"TRX-{random.randint(1000, 9999)}"

# --- ROUTES ---
@app.route('/', methods=['GET', 'POST'])
def login():
    account = get_account()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == account['email'] and password == account['password']:
            session['logged_in'] = True
            session['user'] = 'Admin KHASH'
            session['language'] = account.get('language', 'id')
            return redirect(url_for('dashboard'))
        else:
            flash('Email atau Password salah!', 'danger')
            
    return render_template('login.html', lang=account.get('language', 'id'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    sales_data = get_sales()
    inventory = get_inventory()
    
    total_sales = sum([v['sales'] for v in sales_data.values()])
    total_items = sum([item['stock'] for item in inventory])
    
    return render_template('dashboard.html', 
                           sales_data=sales_data, 
                           total_sales=format_currency(total_sales),
                           total_items=total_items,
                           lang=session.get('language', 'id'))

@app.route('/inventory')
def inventory():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    items = get_inventory()
    for item in items:
        status, color = get_safety_stock_status(item['stock'], item['safety_stock'])
        item['status_text'] = status
        item['status_color'] = color
        item['formatted_price'] = format_currency(item['price'])
        
    return render_template('inventory.html', items=items, lang=session.get('language', 'id'))

@app.route('/edit_product/<prod_id>', methods=['GET', 'POST'])
def edit_product(prod_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    items = get_inventory()
    item_to_edit = next((item for item in items if item['id'] == prod_id), None)
    
    if request.method == 'POST':
        if item_to_edit:
            item_to_edit['name'] = request.form.get('name')
            item_to_edit['stock'] = int(request.form.get('stock'))
            item_to_edit['warehouse_stock'] = int(request.form.get('warehouse_stock'))
            item_to_edit['price'] = int(request.form.get('price'))
            item_to_edit['discount'] = int(request.form.get('discount'))
            item_to_edit['description'] = request.form.get('description')
            # Handle image upload
            if 'image_file' in request.files:
                img = request.files['image_file']
                if img.filename:
                    img_path = save_image(img)
                    if img_path:
                        item_to_edit['image'] = img_path
            save_inventory(items)
            flash('Produk berhasil diupdate!', 'success')
            return redirect(url_for('inventory'))
            
    return render_template('edit_product.html', item=item_to_edit, lang=session.get('language', 'id'))

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        items = get_inventory()
        new_id = f"PRD-{len(items) + 1:03}"
        image_val = "default.png"
        if 'image_file' in request.files:
            img = request.files['image_file']
            if img.filename:
                img_path = save_image(img)
                if img_path:
                    image_val = img_path
        new_item = {
            "id": new_id,
            "name": request.form.get('name'),
            "category": request.form.get('category'),
            "stock": int(request.form.get('stock')),
            "warehouse_stock": int(request.form.get('warehouse_stock', 0)),
            "safety_stock": 5, # default 5
            "price": int(request.form.get('price')),
            "discount": int(request.form.get('discount', 0)),
            "description": request.form.get('description'),
            "image": image_val
        }
        items.append(new_item)
        save_inventory(items)
        flash('Produk berhasil ditambahkan!', 'success')
        return redirect(url_for('inventory'))
        
    return render_template('add_product.html', lang=session.get('language', 'id'))

@app.route('/delete_product/<prod_id>', methods=['POST'])
def delete_product(prod_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    items = get_inventory()
    items = [item for item in items if item['id'] != prod_id]
    save_inventory(items)
    flash('Produk berhasil dihapus!', 'success')
    return redirect(url_for('inventory'))

@app.route('/upload_image/<prod_id>', methods=['POST'])
def upload_image(prod_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    items = get_inventory()
    item = next((i for i in items if i['id'] == prod_id), None)
    if item and 'image_file' in request.files:
        img = request.files['image_file']
        if img.filename:
            img_path = save_image(img)
            if img_path:
                item['image'] = img_path
                save_inventory(items)
                flash('Foto produk berhasil diperbarui!', 'success')
    return redirect(url_for('inventory'))

@app.route('/history')
def history():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    hist = get_history()
    return render_template('history.html', history=hist, lang=session.get('language', 'id'))

@app.route('/download_report')
def download_report():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    filepath = 'data/laporan_penjualan.csv'
    export_history_to_csv(filepath)
    return send_file(filepath, as_attachment=True)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    account = get_account()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_lang':
            new_lang = request.form.get('lang')
            account['language'] = new_lang
            session['language'] = new_lang
            save_account(account)
            flash('Language updated.', 'success')
        elif action == 'change_password':
            account['password'] = request.form.get('new_password')
            save_account(account)
            flash('Password updated successfully.', 'success')
        elif action == 'change_email':
            account['email'] = request.form.get('new_email')
            save_account(account)
            flash('Email updated successfully.', 'success')
        return redirect(url_for('settings'))
        
    return render_template('settings.html', account=account, lang=session.get('language', 'id'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
