import os
from dotenv import load_dotenv

# Loads backend/.env into the process environment for local dev.
# In production (Render), real env vars are already set on the dashboard, so
# this is a no-op there -- load_dotenv() never overrides existing env vars.
load_dotenv()

from flask import Flask, jsonify, request, send_from_directory, send_file, g
from flask_cors import CORS
from werkzeug.utils import secure_filename

from database import init_db

# --- 1. AUTH & CHAT IMPORTS ---
from modules.auth import (
    load_users, authenticate_user, public_user,
    create_user, update_user, delete_user,
)
from modules.auth_guard import require_auth, require_admin
from modules.chat import load_messages, save_message

# --- 2. DIRECT TAX IMPORTS ---
from modules.direct_tax.tds_odoo import process_tds_odoo
from modules.direct_tax.tds_zoho import process_tds_zoho
from modules.direct_tax.tds_challan import analyze_for_challan, update_with_manual_challan
from modules.direct_tax.reco_26as import process_26as_reco
from modules.direct_tax import fixed_assets

# --- 3. COMPLIANCE IMPORT ---
from modules.compliance import load_compliance_data, save_compliance_data

# --- 4. INDIRECT TAX IMPORTS ---
from modules.indirect_tax.gstr1_odoo import process_gstr1_odoo
from modules.indirect_tax.gstr2b_odoo import process_gstr2b_odoo
from modules.indirect_tax.gstr2b_zoho import process_gstr2b_zoho
from modules.indirect_tax.gstr1_zoho import process_gstr1_zoho
from modules.indirect_tax.gstr2b_reco_engine import generate_reco_report
from modules.indirect_tax.gstr2b_reco_zoho_engine import generate_reco_report_zoho
from modules.indirect_tax.gstr3b_engine import generate_gstr3b_report

# --- 5. MARIO IMPORTS ---
from modules.mario.sales import generate_mario_sales_report
from modules.mario.purchase import generate_mario_purchase_report

app = Flask(__name__)
init_db(app)

# CORS is restricted to known frontend origins. Set via the ALLOWED_ORIGINS
# env var (comma-separated) to override without a code change; otherwise
# falls back to the known production frontend + local dev.
_default_origins = ['https://taxautomationapp-1.onrender.com', 'http://localhost:3000']
_allowed_origins = [o.strip() for o in os.environ.get('ALLOWED_ORIGINS', '').split(',') if o.strip()]
CORS(app, origins=_allowed_origins or _default_origins)

UPLOAD_FOLDER = 'temp_uploads'
OUTPUT_FOLDER = 'outputs'

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


# ==========================================
#  UPLOAD HELPERS (shared by every tax route)
# ==========================================

def save_files_list(form_key='files'):
    """Saves every uploaded file under form_key and returns their saved paths."""
    if form_key not in request.files:
        return []
    saved_paths = []
    for file in request.files.getlist(form_key):
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(fp)
            saved_paths.append(fp)
    return saved_paths


def save_files_dict(slot_keys, prefix_with_key=True):
    """Saves one uploaded file per named slot key, returns {slot_key: saved_path}."""
    file_paths = {}
    for key in slot_keys:
        file = request.files.get(key)
        if file and file.filename != '':
            filename = secure_filename(f"{key}_{file.filename}" if prefix_with_key else file.filename)
            fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(fp)
            file_paths[key] = fp
    return file_paths


def run_processor(processor_fn, *args):
    """Calls a processor_fn(*args) that returns a result dict, and turns it into a Flask response."""
    try:
        result = processor_fn(*args)
        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/')
def home():
    return jsonify({"message": "Tax Automation API is Running"})

@app.route('/api/download/<filename>')
@require_auth
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# ==========================================
#  AUTHENTICATION ROUTES
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required"}), 400

    result = authenticate_user(username, password)

    if result['success']:
        return jsonify(result)
    return jsonify(result), 401

@app.route('/api/auth/users', methods=['GET'])
@require_admin
def get_users():
    return jsonify([public_user(u) for u in load_users()])

@app.route('/api/auth/users', methods=['POST'])
@require_admin
def add_user():
    result = create_user(request.json or {})
    return jsonify(result), (201 if result.get("success") else 400)

@app.route('/api/auth/users/<int:user_id>', methods=['PATCH'])
@require_admin
def edit_user(user_id):
    result = update_user(user_id, request.json or {})
    return jsonify(result), (200 if result.get("success") else 400)

@app.route('/api/auth/users/<int:user_id>', methods=['DELETE'])
@require_admin
def remove_user(user_id):
    result = delete_user(user_id)
    return jsonify(result), (200 if result.get("success") else 400)

# ==========================================
#  CHAT ROUTES
# ==========================================

@app.route('/api/chat', methods=['GET'])
@require_auth
def get_chat_messages():
    return jsonify(load_messages())

@app.route('/api/chat', methods=['POST'])
@require_auth
def send_chat_message():
    result = save_message(request.json or {})
    return jsonify(result)

@app.route('/api/chat/handle-request', methods=['POST'])
@require_admin
def handle_access_request():
    data = request.json or {}
    username = data.get('username')
    action = data.get('action') # 'approve' or 'reject'
    message_id = data.get('message_id')

    if not username or not action:
        return jsonify({"error": "Missing data"}), 400

    # 1. Update user status (if approve)
    if action == 'approve':
        users = load_users()
        target = next((u for u in users if u['username'] == username), None)
        if target:
            update_user(target['id'], {"status": "Active"})

    # 2. Log the action in chat
    system_msg = {
        "username": "System",
        "content": f"Access request for {username} was {action.upper()}D by Admin.",
        "type": "system",
        "related_message_id": message_id
    }
    save_message(system_msg)

    return jsonify({"success": True, "message": f"User {action}d successfully."})

# ==========================================
#  TAX MODULE ROUTES
# ==========================================

# --- DIRECT TAX ---
@app.route('/api/direct-tax/tds-odoo', methods=['POST'])
@require_auth
def run_tds_odoo():
    if 'files' not in request.files: return jsonify({"error": "No file part"}), 400
    saved_paths = save_files_list('files')
    custom_name = request.form.get('custom_name', '')
    return run_processor(process_tds_odoo, saved_paths, app.config['OUTPUT_FOLDER'], custom_name)

@app.route('/api/direct-tax/tds-zoho', methods=['POST'])
@require_auth
def run_tds_zoho():
    if 'files' not in request.files: return jsonify({"error": "No file part"}), 400
    saved_paths = save_files_list('files')
    custom_name = request.form.get('custom_name', '')
    return run_processor(process_tds_zoho, saved_paths, app.config['OUTPUT_FOLDER'], custom_name)

@app.route('/api/direct-tax/challan/analyze', methods=['POST'])
@require_auth
def analyze_challan():
    if 'file' not in request.files: return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"TEMP_CHALLAN_{filename}")
    file.save(filepath)
    result = analyze_for_challan(filepath)
    if result.get("success"):
        result['temp_file_path'] = filepath
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/api/direct-tax/challan/update', methods=['POST'])
@require_auth
def update_challan():
    data = request.json or {}
    file_path = data.get('file_path')
    user_inputs = data.get('inputs')
    custom_name = data.get('custom_name', '')
    upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
    resolved = os.path.abspath(file_path) if file_path else ''
    if not file_path or not resolved.startswith(upload_dir) or not os.path.exists(resolved):
        return jsonify({"error": "Session expired. Please upload file again."}), 400
    base_name = os.path.basename(resolved)
    original_name = base_name.replace("TEMP_CHALLAN_", "")
    result = update_with_manual_challan(resolved, user_inputs, app.config['OUTPUT_FOLDER'], custom_name, original_name)
    if os.path.exists(resolved): os.remove(resolved)
    if result.get("success"): return jsonify(result), 200
    else: return jsonify(result), 500

@app.route('/api/direct-tax/26as-reco', methods=['POST'])
@require_auth
def run_26as_reco():
    portal_file = request.files.get('portal_file')
    custom_name = request.form.get('custom_name', '')

    if not portal_file:
        return jsonify({"error": "Please upload the 26AS Text File."}), 400

    try:
        paths = save_files_dict(['portal_file', 'book_file'], prefix_with_key=False)
        p_path = paths.get('portal_file')
        b_path = paths.get('book_file')

        result = process_26as_reco(p_path, b_path, app.config['OUTPUT_FOLDER'], custom_name)

        # Cleanup
        if p_path and os.path.exists(p_path): os.remove(p_path)
        if b_path and os.path.exists(b_path): os.remove(b_path)

        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- COMPLIANCE ---
@app.route('/api/compliance', methods=['GET'])
@require_auth
def get_compliance():
    user_id = request.args.get('user_id')
    # Non-admins can only ever see their own clients, regardless of what's requested.
    if g.current_user['role'] != 'admin':
        user_id = str(g.current_user['id'])
    data = load_compliance_data(user_id)
    return jsonify(data)

@app.route('/api/compliance', methods=['POST'])
@require_auth
def update_compliance():
    data = request.json or {}
    user_id = data.get('user_id')
    clients = data.get('clients')

    if g.current_user['role'] != 'admin':
        user_id = str(g.current_user['id'])

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    result = save_compliance_data(user_id, clients)
    return jsonify(result)

# --- INDIRECT TAX ---
@app.route('/api/indirect-tax/gstr1-odoo', methods=['POST'])
@require_auth
def run_gstr1_odoo():
    if 'files' not in request.files: return jsonify({"error": "No file part"}), 400
    saved_paths = save_files_list('files')
    custom_name = request.form.get('custom_name', '')
    return run_processor(process_gstr1_odoo, saved_paths, app.config['OUTPUT_FOLDER'], custom_name)

@app.route('/api/indirect-tax/gstr2b-odoo', methods=['POST'])
@require_auth
def run_gstr2b_odoo():
    custom_name = request.form.get('custom_name', '')
    slot_keys = ['regular_cgst', 'regular_igst', 'rcm_cgst', 'rcm_igst']
    file_paths_dict = save_files_dict(slot_keys)
    if not file_paths_dict: return jsonify({"error": "No files uploaded"}), 400
    return run_processor(process_gstr2b_odoo, file_paths_dict, app.config['OUTPUT_FOLDER'], custom_name)

@app.route('/api/indirect-tax/gstr2b-zoho', methods=['POST'])
@require_auth
def run_gstr2b_zoho():
    if 'file' not in request.files: return jsonify({"error": "No file part"}), 400
    custom_name = request.form.get('custom_name', '')
    paths = save_files_dict(['file'], prefix_with_key=False)
    fp = paths.get('file')
    if not fp:
        return jsonify({"error": "File invalid"}), 400
    return run_processor(process_gstr2b_zoho, fp, app.config['OUTPUT_FOLDER'], custom_name)

@app.route('/api/indirect-tax/gstr1-zoho', methods=['POST'])
@require_auth
def run_gstr1_zoho():
    slot_keys = ['file_invoice_details', 'file_credit_note_details', 'file_invoice_credit_notes', 'file_export_invoices']
    custom_name = request.form.get('custom_name', '')
    file_paths_dict = save_files_dict(slot_keys)
    if not file_paths_dict:
        return jsonify({"error": "No valid files uploaded."}), 400
    return run_processor(process_gstr1_zoho, file_paths_dict, app.config['OUTPUT_FOLDER'], custom_name)

# --- GSTR-2B MASTER RECONCILIATION ROUTE ---
@app.route('/api/indirect-tax/reco-gstr2b', methods=['POST'])
@require_auth
def reco_gstr2b_route():
    try:
        if 'file_portal' not in request.files:
            return jsonify({'error': 'Portal file is missing.'}), 400

        file_portal = request.files['file_portal']

        odoo_files = {
            'odoo_reg_cgst': request.files.get('odoo_reg_cgst'),
            'odoo_reg_igst': request.files.get('odoo_reg_igst'),
            'odoo_rcm_cgst': request.files.get('odoo_rcm_cgst'),
            'odoo_rcm_igst': request.files.get('odoo_rcm_igst')
        }

        if not any(f for f in odoo_files.values() if f and f.filename != ''):
            return jsonify({'error': 'Please upload at least one Odoo register file.'}), 400

        month_str = request.form.get('month')  # e.g. "2025-12", used to flag prior-period invoices
        excel_file = generate_reco_report(file_portal, odoo_files, month_str)

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='Odoo_Portal_Reco.xlsx',
            as_attachment=True
        )

    except Exception as e:
        print(f"GSTR-2B Reco Error: {e}")
        return jsonify({'error': str(e)}), 500

# --- DEPRECIATION CALCULATOR ROUTE ---
@app.route('/api/fixed-assets/calculate', methods=['POST'])
@require_auth
def calculate_fixed_assets():
    try:
        if 'file_assets' not in request.files:
            return jsonify({'error': 'Please upload the Asset Excel file.'}), 400

        file_assets = request.files['file_assets']
        excel_output = fixed_assets.calculate_depreciation_engine(file_assets)

        return send_file(
            excel_output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='Fixed_Asset_Register.xlsx',
            as_attachment=True
        )

    except Exception as e:
        print(f"FAR Error: {e}")
        return jsonify({'error': str(e)}), 500

# --- GSTR-2B RECO (ZOHO vs PORTAL) ---
@app.route('/api/indirect-tax/reco-gstr2b-zoho', methods=['POST'])
@require_auth
def reco_gstr2b_zoho_route():
    try:
        if 'file_portal' not in request.files or 'file_zoho' not in request.files:
            return jsonify({'error': 'Both Portal and Zoho files are required.'}), 400

        file_portal = request.files['file_portal']
        file_zoho = request.files['file_zoho']

        def get_float(key):
            val = request.form.get(key)
            if not val or val.strip() == '':
                return 0.0
            return float(val)

        manual_inputs = {
            'sales': {
                'taxable': get_float('sales_taxable'),
                'igst': get_float('sales_igst'),
                'cgst': get_float('sales_cgst'),
                'sgst': get_float('sales_sgst'),
            },
            'opening': {
                'igst': get_float('op_igst'),
                'cgst': get_float('op_cgst'),
                'sgst': get_float('op_sgst'),
            }
        }

        month_str = request.form.get('month')  # e.g. "2025-12", used to flag prior-period invoices
        excel_file = generate_reco_report_zoho(file_portal, file_zoho, manual_inputs, month_str)

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='Zoho_Portal_Reco.xlsx',
            as_attachment=True
        )

    except Exception as e:
        print(f"Zoho Reco Error: {e}")
        return jsonify({'error': str(e)}), 500

# --- GSTR-3B WORKING PAPER (ODOO) ---
@app.route('/api/indirect-tax/gstr3b-odoo', methods=['POST'])
@require_auth
def run_gstr3b_odoo():
    saved_gstr1_paths = []
    try:
        client_name = (request.form.get('client_name') or '').strip()
        period = (request.form.get('period') or '').strip()
        if not client_name:
            return jsonify({'error': 'Client name is required.'}), 400
        if not period:
            return jsonify({'error': 'Period (month) is required.'}), 400

        if 'file_portal' not in request.files:
            return jsonify({'error': 'GSTR-2B portal file is required.'}), 400
        file_portal = request.files['file_portal']

        odoo_files = {
            'odoo_reg_cgst': request.files.get('odoo_reg_cgst'),
            'odoo_reg_igst': request.files.get('odoo_reg_igst'),
            'odoo_rcm_cgst': request.files.get('odoo_rcm_cgst'),
            'odoo_rcm_igst': request.files.get('odoo_rcm_igst'),
        }

        for file in request.files.getlist('gstr1_files'):
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(fp)
                saved_gstr1_paths.append(fp)
        if not saved_gstr1_paths:
            return jsonify({'error': 'At least one GSTR-1 Odoo ledger file is required.'}), 400

        opening_itc_override = None
        if any(request.form.get(k) not in (None, '') for k in ('opening_igst', 'opening_cgst', 'opening_sgst')):
            def get_float(key):
                val = request.form.get(key)
                return float(val) if val not in (None, '') else 0.0
            opening_itc_override = {
                'igst': get_float('opening_igst'),
                'cgst': get_float('opening_cgst'),
                'sgst': get_float('opening_sgst'),
            }

        excel_file = generate_gstr3b_report(
            saved_gstr1_paths, file_portal, odoo_files,
            str(g.current_user['id']), client_name, period, opening_itc_override
        )

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name=f'{client_name} GSTR3B {period}.xlsx',
            as_attachment=True
        )

    except Exception as e:
        print(f"GSTR-3B Error: {e}")
        return jsonify({'error': str(e)}), 500

    finally:
        for fp in saved_gstr1_paths:
            if os.path.exists(fp): os.remove(fp)

# ==========================================
#  MARIO CUSTOM ROUTES
# ==========================================

@app.route('/api/mario/sales', methods=['POST'])
@require_auth
def run_mario_sales():
    try:
        excel_file = generate_mario_sales_report(request.files)
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='Mario_Combined_Sales.xlsx',
            as_attachment=True
        )
    except Exception as e:
        print(f"Mario Sales Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/mario/purchase', methods=['POST'])
@require_auth
def run_mario_purchase():
    try:
        excel_file = generate_mario_purchase_report(request.files)
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='Mario_Combined_Purchase.xlsx',
            as_attachment=True
        )
    except Exception as e:
        print(f"Mario Purchase Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
