import os
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# --- 1. AUTH & CHAT IMPORTS ---
from modules.auth import load_users, save_users, authenticate_user
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

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'temp_uploads'
OUTPUT_FOLDER = 'outputs'

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

@app.route('/')
def home():
    return jsonify({"message": "Tax Automation API is Running"})

@app.route('/api/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# ==========================================
#  AUTHENTICATION ROUTES
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    result = authenticate_user(username, password)
    
    if result['success']:
        return jsonify(result)
    return jsonify(result), 401

@app.route('/api/auth/users', methods=['GET'])
def get_users():
    return jsonify(load_users())

@app.route('/api/auth/users', methods=['POST'])
def update_users():
    data = request.json
    if save_users(data):
        return jsonify({"success": True})
    return jsonify({"error": "Failed to save"}), 500

# ==========================================
#  CHAT ROUTES
# ==========================================

@app.route('/api/chat', methods=['GET'])
def get_chat_messages():
    return jsonify(load_messages())

@app.route('/api/chat', methods=['POST'])
def send_chat_message():
    result = save_message(request.json)
    return jsonify(result)

@app.route('/api/chat/handle-request', methods=['POST'])
def handle_access_request():
    data = request.json
    username = data.get('username')
    action = data.get('action') # 'approve' or 'reject'
    message_id = data.get('message_id')

    if not username or not action:
        return jsonify({"error": "Missing data"}), 400

    # 1. Load Users
    users = load_users()
    user_found = False
    
    # 2. Update User Status (if Approve)
    if action == 'approve':
        for u in users:
            if u['username'] == username:
                u['status'] = 'Active'
                user_found = True
                break
        if user_found:
            save_users(users)
    
    # 3. Log the Action in Chat
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
def run_tds_odoo():
    if 'files' not in request.files: return jsonify({"error": "No file part"}), 400
    files = request.files.getlist('files')
    custom_name = request.form.get('custom_name', '')
    saved_paths = []
    try:
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(fp)
                saved_paths.append(fp)
        result = process_tds_odoo(saved_paths, app.config['OUTPUT_FOLDER'], custom_name)
        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/direct-tax/tds-zoho', methods=['POST'])
def run_tds_zoho():
    if 'files' not in request.files: return jsonify({"error": "No file part"}), 400
    files = request.files.getlist('files')
    custom_name = request.form.get('custom_name', '')
    saved_paths = []
    try:
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(fp)
                saved_paths.append(fp)
        result = process_tds_zoho(saved_paths, app.config['OUTPUT_FOLDER'], custom_name)
        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/direct-tax/challan/analyze', methods=['POST'])
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
def update_challan():
    data = request.json
    file_path = data.get('file_path')
    user_inputs = data.get('inputs')
    custom_name = data.get('custom_name', '')
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Session expired. Please upload file again."}), 400
    base_name = os.path.basename(file_path)
    original_name = base_name.replace("TEMP_CHALLAN_", "")
    result = update_with_manual_challan(file_path, user_inputs, app.config['OUTPUT_FOLDER'], custom_name, original_name)
    if os.path.exists(file_path): os.remove(file_path)
    if result.get("success"): return jsonify(result), 200
    else: return jsonify(result), 500

@app.route('/api/direct-tax/26as-reco', methods=['POST'])
def run_26as_reco():
    portal_file = request.files.get('portal_file')
    book_file = request.files.get('book_file')
    custom_name = request.form.get('custom_name', '')

    if not portal_file:
        return jsonify({"error": "Please upload the 26AS Text File."}), 400
        
    try:
        p_filename = secure_filename(portal_file.filename)
        p_path = os.path.join(app.config['UPLOAD_FOLDER'], p_filename)
        portal_file.save(p_path)
        
        b_path = None
        if book_file:
            b_filename = secure_filename(book_file.filename)
            b_path = os.path.join(app.config['UPLOAD_FOLDER'], b_filename)
            book_file.save(b_path)

        result = process_26as_reco(p_path, b_path, app.config['OUTPUT_FOLDER'], custom_name)
        
        # Cleanup
        if os.path.exists(p_path): os.remove(p_path)
        if b_path and os.path.exists(b_path): os.remove(b_path)

        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- COMPLIANCE ---
@app.route('/api/compliance', methods=['GET'])
def get_compliance():
    user_id = request.args.get('user_id')
    data = load_compliance_data(user_id)
    return jsonify(data)

@app.route('/api/compliance', methods=['POST'])
def update_compliance():
    data = request.json
    user_id = data.get('user_id')
    clients = data.get('clients')
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
        
    result = save_compliance_data(user_id, clients)
    return jsonify(result)

# --- INDIRECT TAX ---
@app.route('/api/indirect-tax/gstr1-odoo', methods=['POST'])
def run_gstr1_odoo():
    if 'files' not in request.files: return jsonify({"error": "No file part"}), 400
    files = request.files.getlist('files')
    custom_name = request.form.get('custom_name', '')
    saved_paths = []
    try:
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(fp)
                saved_paths.append(fp)
        result = process_gstr1_odoo(saved_paths, app.config['OUTPUT_FOLDER'], custom_name)
        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/indirect-tax/gstr2b-odoo', methods=['POST'])
def run_gstr2b_odoo():
    custom_name = request.form.get('custom_name', '')
    slot_keys = ['regular_cgst', 'regular_igst', 'rcm_cgst', 'rcm_igst']
    file_paths_dict = {}
    try:
        for key in slot_keys:
            if key in request.files:
                file = request.files[key]
                if file and file.filename != '':
                    filename = secure_filename(f"{key}_{file.filename}")
                    fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(fp)
                    file_paths_dict[key] = fp
        if not file_paths_dict: return jsonify({"error": "No files uploaded"}), 400
        result = process_gstr2b_odoo(file_paths_dict, app.config['OUTPUT_FOLDER'], custom_name)
        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/indirect-tax/gstr2b-zoho', methods=['POST'])
def run_gstr2b_zoho():
    if 'file' not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    custom_name = request.form.get('custom_name', '')
    try:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(fp)
            result = process_gstr2b_zoho(fp, app.config['OUTPUT_FOLDER'], custom_name)
            return jsonify(result), (200 if result.get("success") else 500)
        return jsonify({"error": "File invalid"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/indirect-tax/gstr1-zoho', methods=['POST'])
def run_gstr1_zoho():
    slot_keys = ['file_invoice_details', 'file_credit_note_details', 'file_invoice_credit_notes', 'file_export_invoices']
    file_paths_dict = {}
    custom_name = request.form.get('custom_name', '')
    try:
        for key in slot_keys:
            if key in request.files:
                file = request.files[key]
                if file and file.filename != '':
                    filename = secure_filename(f"{key}_{file.filename}")
                    fp = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(fp)
                    file_paths_dict[key] = fp
        
        if not file_paths_dict:
            return jsonify({"error": "No valid files uploaded."}), 400

        result = process_gstr1_zoho(file_paths_dict, app.config['OUTPUT_FOLDER'], custom_name)
        return jsonify(result), (200 if result.get("success") else 500)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- GSTR-2B MASTER RECONCILIATION ROUTE (FIXED) ---
@app.route('/api/indirect-tax/reco-gstr2b', methods=['POST'])
def reco_gstr2b_route():
    try:
        # 1. Check Portal File
        if 'file_portal' not in request.files:
            return jsonify({'error': 'Portal file is missing.'}), 400
        
        file_portal = request.files['file_portal']

        # 2. Check Odoo Files (The 4 slots)
        odoo_files = {
            'odoo_reg_cgst': request.files.get('odoo_reg_cgst'),
            'odoo_reg_igst': request.files.get('odoo_reg_igst'),
            'odoo_rcm_cgst': request.files.get('odoo_rcm_cgst'),
            'odoo_rcm_igst': request.files.get('odoo_rcm_igst')
        }

        # Ensure at least one Odoo file was uploaded
        if not any(f for f in odoo_files.values() if f and f.filename != ''):
            return jsonify({'error': 'Please upload at least one Odoo register file.'}), 400

        # 3. Call the Engine
        excel_file = generate_reco_report(file_portal, odoo_files)

        # 4. Return Result
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='Odoo_Portal_Reco.xlsx',
            as_attachment=True
        )

    except Exception as e:
        print(f"GSTR-2B Reco Error: {e}") # Log to terminal
        return jsonify({'error': str(e)}), 500

# --- DEPRECIATION CALCULATOR ROUTE ---
@app.route('/api/fixed-assets/calculate', methods=['POST'])
def calculate_fixed_assets():
    try:
        if 'file_assets' not in request.files:
            return jsonify({'error': 'Please upload the Asset Excel file.'}), 400
        
        file_assets = request.files['file_assets']
        
        # Call the engine from the imported module
        excel_output = fixed_assets.calculate_depreciation_engine(file_assets)
        
        return send_file(
            excel_output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='Fixed_Asset_Register.xlsx',
            as_attachment=True
        )

    except Exception as e:
        # Log error if you have a logger, otherwise just return
        print(f"FAR Error: {e}")
        return jsonify({'error': str(e)}), 500
    # --- GSTR-2B RECO (ZOHO vs PORTAL) ---
@app.route('/api/indirect-tax/reco-gstr2b-zoho', methods=['POST'])
def reco_gstr2b_zoho_route():
    try:
        if 'file_portal' not in request.files or 'file_zoho' not in request.files:
            return jsonify({'error': 'Both Portal and Zoho files are required.'}), 400

        file_portal = request.files['file_portal']
        file_zoho = request.files['file_zoho']

        # Call the Zoho Engine
        excel_file = generate_reco_report_zoho(file_portal, file_zoho)

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            download_name='Zoho_Portal_Reco.xlsx',
            as_attachment=True
        )

    except Exception as e:
        print(f"Zoho Reco Error: {e}")
        return jsonify({'error': str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True, port=5000)