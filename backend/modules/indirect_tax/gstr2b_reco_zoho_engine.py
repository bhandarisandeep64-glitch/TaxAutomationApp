import pandas as pd
import numpy as np
import re
import logging
from io import BytesIO
from difflib import SequenceMatcher
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

# ==========================================
#  CONFIGURATION
# ==========================================

PORTAL_SHEETS_TO_IGNORE = [
    "Read me", "ITC Available", "ITC not available", "ITC Reversal", "ITC Rejected"
]

RENAME_MAP = {
    'Invoice number': 'Invoice Number', 'Note number': 'Invoice Number', 'Bill of entry number': 'Invoice Number',
    'Invoice Value (₹)': 'Invoice Value', 'Taxable Value (₹)': 'Taxable Value',
    'Integrated Tax (₹)': 'IGST Tax Amount', 'Central Tax (₹)': 'CGST Tax Amount', 'State/UT Tax (₹)': 'SGST Tax Amount',
    'Cess Amount (₹)': 'Cess Amount', 'Trade/Legal name': 'Vendor Name', 'GSTIN of supplier': 'GSTIN',
    'Invoice Date': 'Invoice date', 'Place of supply': 'Place Of Supply',
    'Supply Attract Reverse Charge': 'Reverse Charge', 'Rate (%)': 'Rate'
}

# ==========================================
#  UTILITIES
# ==========================================

def clean_inv_str(s):
    if pd.isna(s): return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(s).lower())

def robust_safe_float(val):
    if pd.isna(val) or val == '': return 0.0
    try:
        val_str = str(val).replace(',', '').strip()
        return float(val_str)
    except:
        return 0.0

def clean_gstin(val):
    if pd.isna(val): return ""
    s = str(val).upper().strip().replace(" ", "").replace("-", "")
    return s[:15] if len(s) >= 15 else s

def clean_date_robust(val):
    if pd.isna(val) or val == '': return None
    try:
        if isinstance(val, pd.Timestamp): return val.normalize()
        return pd.to_datetime(val, dayfirst=True, errors='coerce').normalize()
    except:
        return None

def get_similarity_score(a, b):
    return SequenceMatcher(None, a, b).ratio()

# ==========================================
#  EXCEL WRITER HELPERS
# ==========================================

def add_formatting(writer, df, sheet_name):
    if df.empty: return
    df = df.loc[:, ~df.columns.duplicated()]
    df.to_excel(writer, sheet_name=sheet_name, index=False)

    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    (num_rows, num_cols) = df.shape

    fmt_header = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
    fmt_num = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})
    fmt_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    fmt_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
    fmt_bold = workbook.add_format({'bold': True})

    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, fmt_header)
        worksheet.set_column(col_num, col_num, 15)

    if num_rows > 0:
        worksheet.autofilter(0, 0, num_rows, num_cols - 1)

    total_row = num_rows + 1
    worksheet.write(total_row, 0, 'Filter Total', fmt_bold)

    keywords_to_sum = ['taxable', 'igst', 'cgst', 'sgst', 'cess', 'total', 'difference', 'val', 'rate', 'integrated', 'central', 'state']
    
    for col_idx, col_name in enumerate(df.columns):
        c_name = str(col_name).lower()
        if any(k in c_name for k in keywords_to_sum) and 'number' not in c_name and 'date' not in c_name:
             col_letter = xl_col_to_name(col_idx)
             worksheet.write_formula(total_row, col_idx, f'=SUBTOTAL(9,{col_letter}2:{col_letter}{total_row})', fmt_num)

    if 'Remarks' in df.columns:
        rem_idx = df.columns.get_loc('Remarks')
        rem_letter = xl_col_to_name(rem_idx)
        rng = f"{rem_letter}2:{rem_letter}{total_row}"
        worksheet.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': 'Mismatch', 'format': fmt_red})
        worksheet.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': 'Not', 'format': fmt_red})
        worksheet.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': 'Match', 'format': fmt_green})

# ==========================================
#  DATA CLEANERS
# ==========================================

def clean_portal_data(file_content):
    xls = pd.ExcelFile(file_content)
    cleaned_sheets = {}
    rcm_frames = []
    
    conditional_delete = {
        "B2B": 7, "B2B-CDNR": 7, "ECO": 7, "ISD": 7, "IMPG": 7, "IMPGSEZ": 7,
        "B2B (ITC Reversal)": 7, "B2B-DNR": 7, "B2BA": 8, "B2B-CDNRA": 8
    }

    for sheet in xls.sheet_names:
        sheet_clean = sheet.strip()
        if sheet_clean in PORTAL_SHEETS_TO_IGNORE: continue

        try:
            df_raw = pd.read_excel(xls, sheet_name=sheet, header=None)
            if sheet_clean in conditional_delete:
                target_idx = conditional_delete[sheet_clean] - 1
                if len(df_raw) <= target_idx or df_raw.iloc[target_idx].isna().all(): continue

            # Extract Header
            header_idx = -1
            search_terms = ['gstin of supplier', 'invoice number', 'note number']
            for i in range(min(10, len(df_raw))):
                row_str = " ".join(df_raw.iloc[i].astype(str).fillna('').values).lower()
                if any(term in row_str for term in search_terms):
                    header_idx = i; break
            
            if header_idx == -1: continue

            df = df_raw.iloc[header_idx+1:].reset_index(drop=True)
            df.columns = df_raw.iloc[header_idx].astype(str).str.strip().tolist()

            # Rename
            final_cols = []
            for col in df.columns:
                mapped = col
                for k, v in RENAME_MAP.items():
                    if k.lower() == str(col).lower().strip(): mapped = v; break
                final_cols.append(mapped)
            df.columns = final_cols

            # Cleanup
            df = df.loc[:, ~df.columns.duplicated()]
            numeric_cols = ['Taxable Value', 'Invoice Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount']
            for col in numeric_cols:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # RCM Separation
            if 'Reverse Charge' in df.columns:
                is_rcm = df['Reverse Charge'].astype(str).str.strip().str.lower().isin(['yes', 'y'])
                if is_rcm.any():
                    rcm_data = df[is_rcm].copy(); rcm_data['Source'] = sheet
                    rcm_frames.append(rcm_data); df = df[~is_rcm]

            cleaned_sheets[sheet] = df
        except Exception: continue
    
    if rcm_frames: cleaned_sheets['RCM Combined'] = pd.concat(rcm_frames, ignore_index=True)
    return cleaned_sheets

def clean_zoho_data(file_content):
    xls = pd.ExcelFile(file_content)
    SHEETS_TO_DELETE = ['imp', 'imp_services', 'nil,exempt,non-gst,composition', 'hsn', 'advance paid', 'advance adjusted', 'docs']
    sheet_map = {}

    for sheet_name in xls.sheet_names:
        sheet_lower = sheet_name.lower().strip()
        if any(x in sheet_lower for x in SHEETS_TO_DELETE): continue
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=1)
            if df.empty: continue
            df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
            
            # Validation
            if 'Invoice Number' in df.columns:
                if df['Invoice Number'].dropna().empty: continue
                last_idx = df['Invoice Number'].last_valid_index()
                if last_idx is not None: df = df.iloc[:last_idx + 1]
            elif 'Taxable Value' not in df.columns: continue

            sheet_map[sheet_lower] = {'original_name': sheet_name, 'df': df}
        except: continue

    # Remove RCM invoices from B2B if present
    if 'b2b' in sheet_map and 'reverse charge' in sheet_map:
        b2b_df = sheet_map['b2b']['df']
        rcm_df = sheet_map['reverse charge']['df']
        if 'Invoice Number' in b2b_df.columns and 'Invoice Number' in rcm_df.columns:
            rcm_invoices = rcm_df['Invoice Number'].unique()
            clean_b2b = b2b_df[~b2b_df['Invoice Number'].isin(rcm_invoices)].copy()
            if clean_b2b.empty: del sheet_map['b2b']
            else: sheet_map['b2b']['df'] = clean_b2b
    return sheet_map

# ==========================================
#  RECONCILIATION LOGIC
# ==========================================

def generate_lookup_maps(dataset):
    candidates = [] 
    for key, val in dataset.items():
        df = val if isinstance(val, pd.DataFrame) else val['df']
        col_inv = 'Invoice Number'
        if col_inv not in df.columns: continue
        
        col_tax = next((c for c in df.columns if 'Taxable' in c), None)
        if not col_tax: continue

        col_gstin = next((c for c in df.columns if 'gstin' in c.lower()), None)
        
        def find_fin_col(keywords): return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)
        col_igst, col_cgst, col_sgst = find_fin_col(['igst']), find_fin_col(['cgst']), find_fin_col(['sgst'])

        for idx, row in df.iterrows():
            candidates.append({
                'id': f"{key}_{idx}", 'used': False,
                'clean_inv': clean_inv_str(str(row[col_inv]).strip()),
                'raw_inv': str(row[col_inv]).strip(),
                'tax_val': robust_safe_float(row[col_tax]), 
                'gstin': clean_gstin(row[col_gstin]) if col_gstin else "",
                'igst': robust_safe_float(row[col_igst]) if col_igst else 0.0,
                'cgst': robust_safe_float(row[col_cgst]) if col_cgst else 0.0,
                'sgst': robust_safe_float(row[col_sgst]) if col_sgst else 0.0
            })
    return candidates

def reconcile_dataframe(df, candidates, target_col_name, is_portal_sheet, reco_month_dt=None):
    df[target_col_name] = 0.0; df['Difference'] = 0.0; df['Remarks'] = ''; df['__matched__'] = False 
    col_inv = 'Invoice Number'; col_tax = 'Taxable Value'
    if col_inv not in df.columns: return df
    
    col_gstin = next((c for c in df.columns if 'gstin' in c.lower()), None)
    col_date = next((c for c in df.columns if 'date' in c.lower() and 'invoice' in c.lower()), None)

    # Clean Date
    if col_date: df[col_date] = df[col_date].apply(clean_date_robust)

    # Exact Match Index
    exact_match_index = {}
    for i, cand in enumerate(candidates):
        key = (cand['clean_inv'], cand['tax_val'], cand['gstin'])
        if key not in exact_match_index: exact_match_index[key] = []
        exact_match_index[key].append(i)

    def write_match(idx, r_tax, cand, remark):
        df.at[idx, target_col_name] = cand['tax_val'] if cand else r_tax
        df.at[idx, 'Difference'] = r_tax - (cand['tax_val'] if cand else r_tax)
        df.at[idx, 'Remarks'] = remark
        df.at[idx, '__matched__'] = True
        if cand: cand['used'] = True

    # 1. Exact Match
    for idx, row in df.iterrows():
        inv = clean_inv_str(row.get(col_inv)); tax = robust_safe_float(row.get(col_tax)); gst = clean_gstin(row.get(col_gstin)) if col_gstin else ""
        if not inv: continue
        key = (inv, tax, gst)
        if key in exact_match_index:
            for cand_idx in exact_match_index[key]:
                cand = candidates[cand_idx]
                if not cand['used']: write_match(idx, tax, cand, "Match"); break
    
    # 2. Fuzzy / Typo Matches
    for idx, row in df.iterrows():
        if df.at[idx, '__matched__']: continue
        inv = clean_inv_str(row.get(col_inv)); tax = robust_safe_float(row.get(col_tax)); gst = clean_gstin(row.get(col_gstin)) if col_gstin else ""
        if not inv: continue
        
        for cand in candidates:
            if cand['used']: continue
            if abs(tax - cand['tax_val']) > 2.0: continue
            if gst and cand['gstin'] and gst != cand['gstin']: continue
            
            # Typo or Fuzzy
            if get_similarity_score(inv, cand['clean_inv']) > 0.85:
                write_match(idx, tax, cand, "Match(Typo)"); break
            
            c_inv, r_inv = cand['clean_inv'], inv
            if (len(r_inv)>3 and len(c_inv)>3) and ((r_inv in c_inv) or (c_inv in r_inv)):
                write_match(idx, tax, cand, "Match(Fuzzy)"); break

    # Cleanup
    for idx, row in df.iterrows():
        if not df.at[idx, '__matched__']:
            df.at[idx, 'Difference'] = robust_safe_float(row.get(col_tax))
            remark = "Not in Books" if is_portal_sheet else "Not on Portal"
            if is_portal_sheet and reco_month_dt and col_date:
                curr_date = clean_date_robust(row[col_date])
                if pd.notnull(curr_date) and curr_date < reco_month_dt: remark = "Previous Period Inv"
            df.at[idx, 'Remarks'] = remark
            
    df.drop(columns=['__matched__'], inplace=True, errors='ignore')
    return df

# ==========================================
#  MASTER DASHBOARD GENERATOR
# ==========================================

def calculate_smart_offset(liability, credit):
    """Section 49 Payment Logic"""
    L = liability.copy(); C = credit.copy()
    paid = {'i_i':0, 'i_c':0, 'i_s':0, 'c_c':0, 'c_i':0, 's_s':0, 's_i':0}
    
    # IGST Credit
    use = min(L['i'], C['i']); paid['i_i'] = use; L['i'] -= use; C['i'] -= use
    if C['i'] > 0: use = min(L['c'], C['i']); paid['i_c'] = use; L['c'] -= use; C['i'] -= use
    if C['i'] > 0: use = min(L['s'], C['i']); paid['i_s'] = use; L['s'] -= use; C['i'] -= use
    
    # CGST Credit
    if L['c'] > 0 and C['c'] > 0: use = min(L['c'], C['c']); paid['c_c'] = use; L['c'] -= use; C['c'] -= use
    if L['i'] > 0 and C['c'] > 0: use = min(L['i'], C['c']); paid['c_i'] = use; L['i'] -= use; C['c'] -= use

    # SGST Credit
    if L['s'] > 0 and C['s'] > 0: use = min(L['s'], C['s']); paid['s_s'] = use; L['s'] -= use; C['s'] -= use
    if L['i'] > 0 and C['s'] > 0: use = min(L['i'], C['s']); paid['s_i'] = use; L['i'] -= use; C['s'] -= use
    return paid

def generate_master_dashboard(writer, portal_dict, books_dict, manual_inputs):
    # 1. Calculate RCM and ITC
    sums = {'all_other': {'i':0,'c':0,'s':0}, 'rcm_reg': {'i':0,'c':0,'s':0}, 'rcm_urd': {'i':0,'c':0,'s':0}}
    
    def get_t(row, df):
        def f(k): return next((c for c in df.columns if any(x in c.lower() for x in k)), None)
        ci, cc, cs = f(['igst']), f(['cgst']), f(['sgst'])
        return robust_safe_float(row.get(ci)), robust_safe_float(row.get(cc)), robust_safe_float(row.get(cs))

    for name, df in portal_dict.items():
        col_rcm = next((c for c in df.columns if 'reverse' in c.lower()), None)
        is_cn = 'cdnr' in name.lower() or 'credit' in name.lower()
        mult = -1 if is_cn else 1
        for _, r in df.iterrows():
            if is_cn and "Not in Books" in str(r.get('Remarks', '')): continue
            i, c, s = get_t(r, df)
            if str(r.get(col_rcm, '')).lower() in ['y', 'yes']:
                sums['rcm_reg']['i'] += i*mult; sums['rcm_reg']['c'] += c*mult; sums['rcm_reg']['s'] += s*mult
            else:
                sums['all_other']['i'] += i*mult; sums['all_other']['c'] += c*mult; sums['all_other']['s'] += s*mult

    tot_rcm = {k: sums['rcm_reg'][k] for k in ['i','c','s']} # Simplified for brevity
    net_itc = {k: tot_rcm[k] + sums['all_other'][k] for k in ['i','c','s']}

    # 2. Offset
    sales = manual_inputs.get('sales', {'igst':0, 'cgst':0, 'sgst':0})
    op = manual_inputs.get('opening', {'igst':0, 'cgst':0, 'sgst':0})
    
    L_fwd = {'i': sales['igst'], 'c': sales['cgst'], 's': sales['sgst']}
    C_avail = {'i': op['igst'] + net_itc['i'], 'c': op['cgst'] + net_itc['c'], 's': op['sgst'] + net_itc['s']}
    
    paid = calculate_smart_offset(L_fwd, C_avail)

    # 3. Write Data
    data = []
    def r(d, s, i, c, sg): data.append([d, s, i, c, sg, i+c+sg])
    r("OUTPUT LIABILITY", "", 0, 0, 0)
    r("1. Sales", "", sales['igst'], sales['cgst'], sales['sgst'])
    r("OFFSET SUMMARY", "", 0, 0, 0)
    r("Paid by IGST", "", paid['i_i'], paid['i_c'], paid['i_s'])
    
    df = pd.DataFrame(data, columns=["Particulars", "Details", "IGST", "CGST", "SGST", "Total"])
    add_formatting(writer, df, "Master Dashboard")

def generate_vendor_summary(writer, portal_dict, books_dict):
    stats = {}
    def process(d_dict, source):
        for name, data in d_dict.items():
            df = data if isinstance(data, pd.DataFrame) else data['df']
            col_gst = next((c for c in df.columns if 'gstin' in c.lower()), None)
            col_tax = next((c for c in df.columns if 'taxable' in c.lower()), None)
            if not col_gst or not col_tax: continue
            
            for _, r in df.iterrows():
                gst = clean_gstin(r[col_gst])
                if not gst: continue
                if gst not in stats: stats[gst] = {'p':0.0, 'b':0.0}
                val = robust_safe_float(r[col_tax])
                if source == 'portal': stats[gst]['p'] += val
                else: stats[gst]['b'] += val

    process(portal_dict, 'portal')
    process(books_dict, 'books')
    
    summ = [[g, d['p'], d['b'], d['b']-d['p']] for g, d in stats.items()]
    df_s = pd.DataFrame(summ, columns=['GSTIN', 'Portal Taxable', 'Books Taxable', 'Difference'])
    add_formatting(writer, df_s, "Vendor Summary")

def get_smart_sorted_order(portal_dict, books_dict):
    final = []; used = set()
    bk = list(books_dict.keys())
    def clean(n): return n.lower().replace(" ", "").replace("-", "").replace("_", "").replace("(portal)", "").replace("(books)", "")
    
    for p_name, p_df in portal_dict.items():
        best = None; p_cl = clean(p_name)
        for b in bk:
            if b in used: continue
            if p_cl == clean(b): best = b; break
        final.append((f"{p_name[:20]} (Portal)", p_df))
        if best:
            final.append((f"{best[:20]} (Books)", books_dict[best]['df'])); used.add(best)
    
    for b, data in books_dict.items():
        if b not in used: final.append((f"{b[:20]} (Books)", data['df']))
    return final

# ==========================================
#  MAIN ENTRY POINT (API INTEGRATION)
# ==========================================

def generate_reco_report_zoho(file_portal, file_zoho, month_str=None, manual_inputs=None):
    """
    Main entry point for integration.
    Args:
        file_portal: File object or path for Portal Excel
        file_zoho: File object or path for Zoho Excel
        month_str: String 'YYYY-MM'
        manual_inputs: Dictionary (Optional) with 'sales' and 'opening' keys
    """
    output = BytesIO()
    reco_dt = pd.to_datetime(month_str + "-01") if month_str else None
    
    # Default inputs if not provided (Handling Legacy Calls)
    if manual_inputs is None:
        manual_inputs = {
            'sales': {'taxable':0, 'igst':0, 'cgst':0, 'sgst':0},
            'opening': {'igst':0, 'cgst':0, 'sgst':0}
        }

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        try:
            # 1. Clean Data
            portal_data = clean_portal_data(file_portal)
            zoho_data = clean_zoho_data(file_zoho)

            # 2. Generate Maps
            books_maps = generate_lookup_maps(zoho_data)
            portal_maps = generate_lookup_maps(portal_data)

            # 3. Process
            processed_portal = {s: reconcile_dataframe(df, books_maps, 'As per Books', True, reco_dt) for s, df in portal_data.items()}
            for key, data in zoho_data.items():
                data['df'] = reconcile_dataframe(data['df'], portal_maps, 'As per Portal', False, None)

            # 4. Generate Summaries
            generate_master_dashboard(writer, processed_portal, zoho_data, manual_inputs)
            generate_vendor_summary(writer, processed_portal, zoho_data)

            # 5. Write Details
            sorted_sheets = get_smart_sorted_order(processed_portal, zoho_data)
            for sheet_name, df in sorted_sheets:
                add_formatting(writer, df, sheet_name)
                
        except Exception as e:
            logging.error(f"Error in Max Reco Module: {e}")
            raise e

    output.seek(0)
    return output