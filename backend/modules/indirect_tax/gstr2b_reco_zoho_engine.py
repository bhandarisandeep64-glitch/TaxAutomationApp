import pandas as pd
import numpy as np
import re
import logging
from io import BytesIO
from xlsxwriter.utility import xl_col_to_name

# ==========================================
#  SECTION 1: SHARED UTILITIES & FORMATTING
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

def add_formatting_and_subtotals(writer, df, sheet_name):
    """
    Advanced formatting from the standalone app: 
    Adds Subtotals, Filters, and Conditional Formatting.
    """
    if df.empty: return 
    
    # Safety: Drop duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Write dataframe
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    (num_rows, num_cols) = df.shape

    # Formats
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
    bold_format = workbook.add_format({'bold': True})
    number_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})
    red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'}) 
    green_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'}) 
    
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(col_num, col_num, 15)

    if num_rows > 0:
        worksheet.autofilter(0, 0, num_rows, num_cols - 1)

    total_row = num_rows + 1
    worksheet.write(total_row, 0, 'Filter Total', bold_format)
    
    # Subtotals for key columns
    target_cols = [
        'Taxable Value', 'Invoice Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount',
        'IGST', 'CGST', 'SGST', 'Cess', 'Total', 'Taxable Amt.', 'Debit', 'Credit',
        'As per Portal', 'As per Books', 'Difference'
    ]
    
    for col_name in target_cols:
        if col_name in df.columns:
            col_idx = df.columns.get_loc(col_name)
            col_letter = xl_col_to_name(col_idx)
            formula = f'=SUBTOTAL(9,{col_letter}2:{col_letter}{total_row})'
            worksheet.write_formula(total_row, col_idx, formula, number_format)
            
    # Conditional Formatting for Remarks
    if 'Remarks' in df.columns:
        rem_idx = df.columns.get_loc('Remarks')
        rem_letter = xl_col_to_name(rem_idx)
        range_str = f"{rem_letter}2:{rem_letter}{total_row}"
        worksheet.conditional_format(range_str, {'type': 'text', 'criteria': 'containing', 'value': 'Not', 'format': red_format})
        worksheet.conditional_format(range_str, {'type': 'text', 'criteria': 'containing', 'value': 'Mismatch', 'format': red_format})
        worksheet.conditional_format(range_str, {'type': 'text', 'criteria': 'containing', 'value': 'Match', 'format': green_format})

# ==========================================
#  SECTION 2: PORTAL CLEANING (ADVANCED)
# ==========================================

def filter_portal_sheets(xls):
    """Smart filtering of portal sheets to avoid junk tabs."""
    sheets_to_delete_always = ["Read me", "ITC Available", "ITC not available", "ITC Reversal", "ITC Rejected"]
    conditional_delete_map = {
        "B2B": 7, "B2B-CDNR": 7, "ECO": 7, "ISD": 7, "IMPG": 7, "IMPGSEZ": 7,
        "B2B (ITC Reversal)": 7, "B2B-DNR": 7, "B2BA": 8, "B2B-CDNRA": 8
    }
    kept_dataframes = {}
    for sheet in xls.sheet_names:
        sheet_clean = sheet.strip()
        if sheet_clean in sheets_to_delete_always: continue
        try:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
            if sheet_clean in conditional_delete_map:
                target_idx = conditional_delete_map[sheet_clean] - 1
                if len(df) <= target_idx or df.iloc[target_idx].isna().all(): continue
            kept_dataframes[sheet] = df
        except: continue
    return kept_dataframes

def clean_portal_df(df_raw, sheet_name):
    # 1. Header Logic
    header_idx = -1
    search_terms = ['gstin of supplier', 'invoice number', 'note number', 'bill of entry number']
    for i in range(min(10, len(df_raw))):
        row_str = " ".join(df_raw.iloc[i].astype(str).fillna('').values).lower()
        if any(term in row_str for term in search_terms):
            header_idx = i; break
    if header_idx == -1: return pd.DataFrame()

    df_data = df_raw.iloc[header_idx+1:].reset_index(drop=True)
    row1 = df_raw.iloc[header_idx].astype(str).replace('nan', '').str.strip().tolist()
    
    # Handle multi-row headers if present
    if header_idx + 1 < len(df_raw):
        row2 = df_raw.iloc[header_idx+1].astype(str).replace('nan', '').str.strip().tolist()
        if any('tax' in val.lower() for val in row2):
            df_data = df_raw.iloc[header_idx+2:].reset_index(drop=True)
            new_cols = [c2 if c2 else c1 if c1 else "Unknown" for c1, c2 in zip(row1, row2)]
            if len(new_cols) == df_data.shape[1]: df_data.columns = new_cols
        else: 
            if len(row1) == df_data.shape[1]: df_data.columns = row1
    else: 
        if len(row1) == df_data.shape[1]: df_data.columns = row1

    # 2. Rename & Clean
    rename_map = {
        'Invoice number': 'Invoice Number', 'Note number': 'Invoice Number', 'Bill of entry number': 'Invoice Number',
        'Invoice Value (₹)': 'Invoice Value', 'Taxable Value (₹)': 'Taxable Value',
        'Integrated Tax (₹)': 'IGST Tax Amount', 'Central Tax (₹)': 'CGST Tax Amount', 'State/UT Tax (₹)': 'SGST Tax Amount',
        'Cess Amount (₹)': 'Cess Amount', 'Trade/Legal name': 'Vendor Name', 'GSTIN of supplier': 'GSTIN',
        'Invoice Date': 'Invoice date', 'Place of supply': 'Place Of Supply',
        'Supply Attract Reverse Charge': 'Reverse Charge', 'Rate (%)': 'Rate'
    }
    final_cols = []
    for col in df_data.columns:
        mapped = col
        for k, v in rename_map.items():
            if k.lower() == str(col).lower().strip(): mapped = v; break
        final_cols.append(mapped)
    
    df_data.columns = final_cols
    df_data = df_data.loc[:, ~df_data.columns.duplicated()]

    numeric_cols = ['Taxable Value', 'Invoice Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount', 'Rate']
    for col in numeric_cols:
        if col in df_data.columns: df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)

    # Drop useless columns
    unwanted = ['period', 'filing date', 'applicable %', 'source', 'irn']
    cols_to_drop = [c for c in df_data.columns if any(kw in str(c).lower() for kw in unwanted)]
    if cols_to_drop: df_data.drop(columns=cols_to_drop, inplace=True, errors='ignore')

    df_data = df_data.replace(r'^\s*$', np.nan, regex=True).dropna(axis=1, how='all')
    return df_data

# ==========================================
#  SECTION 3: ZOHO CLEANING (PRESERVED FROM APP.PY)
# ==========================================

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

            # Standardize Columns for Advanced Engine
            if 'Taxable Value' in df.columns: df['Taxable Amt.'] = df['Taxable Value']
            if 'Invoice Date' in df.columns: df['Invoice date'] = df['Invoice Date']

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
#  SECTION 4: ADVANCED RECO ENGINE (MAP BASED)
# ==========================================

def generate_lookup_map(data_source):
    """
    Creates an optimized hash map for O(1) matching speed.
    """
    exact_map = {}
    amount_map = {} 
    
    for key, val in data_source.items():
        if isinstance(val, pd.DataFrame): df = val 
        else: df = val['df'] 
        
        # Support both Taxable Value and Taxable Amt.
        col_inv = 'Invoice Number'
        col_tax = 'Taxable Value' if 'Taxable Value' in df.columns else 'Taxable Amt.'

        if col_inv in df.columns and col_tax in df.columns:
            for _, row in df.iterrows():
                inv_raw = str(row[col_inv]).strip()
                inv_clean = clean_inv_str(inv_raw)
                
                try:
                    raw_tax = float(row[col_tax])
                    tax_val = raw_tax if pd.notnull(raw_tax) else 0.0
                except:
                    tax_val = 0.0

                exact_key = str(row[col_inv]).strip().lower()
                if exact_key not in exact_map: exact_map[exact_key] = tax_val
                
                amt_key = f"{tax_val:.2f}"
                if amt_key not in amount_map: amount_map[amt_key] = []
                
                amount_map[amt_key].append({
                    'clean_inv': inv_clean,
                    'tax_val': tax_val,
                    'inv_raw': inv_raw
                })

    return exact_map, amount_map

def apply_reco_logic(df, lookup_maps, target_col_name, is_portal_sheet, reco_month_dt=None):
    """
    The Advanced Logic: Uses fuzzy matching and date checking.
    """
    exact_map, amount_map = lookup_maps
    
    df[target_col_name] = 0.0; df['Difference'] = 0.0; df['Remarks'] = ''
    col_inv = 'Invoice Number'
    col_tax = 'Taxable Value' if 'Taxable Value' in df.columns else 'Taxable Amt.'
    col_date = 'Invoice date' 
    
    if col_inv not in df.columns: return df

    if is_portal_sheet and reco_month_dt and col_date in df.columns:
        df[col_date] = pd.to_datetime(df[col_date], dayfirst=True, errors='coerce')

    def row_logic(row):
        inv_raw = str(row.get(col_inv, '')).strip()
        inv_clean = clean_inv_str(inv_raw)
        inv_exact_key = inv_raw.lower()
        
        my_tax = float(row.get(col_tax, 0)) if pd.notnull(row.get(col_tax, 0)) else 0.0
        
        remark = ""
        other_val = 0.0
        diff = 0.0
        match_found = False
        
        # 1. Exact Match (Fastest)
        if inv_exact_key in exact_map:
            other_val = exact_map[inv_exact_key]
            if abs(my_tax - other_val) < 2:
                match_found = True
                remark = "Match"
            else:
                 match_found = True 
                 remark = "Mismatch"

        # 2. Fuzzy Match (Amount Based - Intelligent)
        if not match_found:
            amt_key = f"{my_tax:.2f}"
            if amt_key in amount_map:
                candidates = amount_map[amt_key]
                for cand in candidates:
                    cand_clean = cand['clean_inv']
                    # Fuzzy Logic: Check substrings or typo similarity
                    if (inv_clean and cand_clean) and ((inv_clean in cand_clean) or (cand_clean in inv_clean)):
                        other_val = cand['tax_val']
                        match_found = True
                        remark = "Match (Fuzzy)"
                        break 
        
        if match_found:
            diff = my_tax - other_val
            if abs(diff) > 2: remark = "Mismatch"
        else:
            remark = "Not in Books" if is_portal_sheet else "Not on Portal"
            diff = my_tax

        # 3. Date Check (For Portal Sheets)
        if is_portal_sheet and reco_month_dt and pd.notnull(row.get(col_date)):
            try:
                inv_dt = row[col_date]
                if isinstance(inv_dt, str): pass 
                elif inv_dt < reco_month_dt:
                    if "Match" in remark: remark += " (Old Inv)" 
                    else: remark = "Previous Period Inv" 
            except: pass

        return pd.Series([other_val, diff, remark])

    results = df.apply(row_logic, axis=1)
    if not results.empty:
        df[target_col_name] = results[0]
        df['Difference'] = results[1]
        df['Remarks'] = results[2]
    return df

# ==========================================
#  SECTION 5: DASHBOARD & SORTING
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
    """Preserved from App.py for Input Tax Credit Summary"""
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

    tot_rcm = {k: sums['rcm_reg'][k] for k in ['i','c','s']} 
    net_itc = {k: tot_rcm[k] + sums['all_other'][k] for k in ['i','c','s']}

    # Offset Logic
    sales = manual_inputs.get('sales', {'igst':0, 'cgst':0, 'sgst':0})
    op = manual_inputs.get('opening', {'igst':0, 'cgst':0, 'sgst':0})
    
    L_fwd = {'i': sales['igst'], 'c': sales['cgst'], 's': sales['sgst']}
    C_avail = {'i': op['igst'] + net_itc['i'], 'c': op['cgst'] + net_itc['c'], 's': op['sgst'] + net_itc['s']}
    
    paid = calculate_smart_offset(L_fwd, C_avail)

    data = []
    def r(d, s, i, c, sg): data.append([d, s, i, c, sg, i+c+sg])
    r("OUTPUT LIABILITY", "", 0, 0, 0)
    r("1. Sales", "", sales['igst'], sales['cgst'], sales['sgst'])
    r("OFFSET SUMMARY", "", 0, 0, 0)
    r("Paid by IGST", "", paid['i_i'], paid['i_c'], paid['i_s'])
    
    df = pd.DataFrame(data, columns=["Particulars", "Details", "IGST", "CGST", "SGST", "Total"])
    # Use advanced formatting here too
    add_formatting_and_subtotals(writer, df, "Master Dashboard")

def get_smart_sorted_order(portal_dict, books_dict):
    """
    Matches Portal sheets to Books sheets side-by-side.
    """
    portal_invs = {}
    for k, df in portal_dict.items():
        if 'Invoice Number' in df.columns:
            unique_invs = set(df['Invoice Number'].astype(str).str.lower().str.strip())
            portal_invs[k] = unique_invs
            
    books_invs = {}
    for k, val in books_dict.items():
        df = val['df']
        if 'Invoice Number' in df.columns:
            unique_invs = set(df['Invoice Number'].astype(str).str.lower().str.strip())
            books_invs[k] = unique_invs
    
    final_order = []
    used_books = set()

    for p_name, p_df in portal_dict.items():
        best_match_name = None
        highest_intersect = 0
        p_set = portal_invs.get(p_name, set())

        if p_set:
            for b_name, b_set in books_invs.items():
                if b_name in used_books: continue
                common_count = len(p_set.intersection(b_set))
                if common_count > highest_intersect:
                    highest_intersect = common_count
                    best_match_name = b_name

        base_name = p_name[:20].strip() 
        p_sheet_title = f"{base_name} (Portal)"
        final_order.append((p_sheet_title, p_df))

        if best_match_name and highest_intersect > 0:
            b_df = books_dict[best_match_name]['df']
            b_sheet_title = f"{base_name} (Books)"
            final_order.append((b_sheet_title, b_df))
            used_books.add(best_match_name)

    for b_name, val in books_dict.items():
        if b_name not in used_books:
            title = f"{b_name} (Books)"[:31]
            final_order.append((title, val['df']))
            
    return final_order

# ==========================================
#  SECTION 6: MAIN ENTRY POINT
# ==========================================

def generate_reco_report_zoho(file_portal, file_zoho, month_str=None, manual_inputs=None):
    """
    API Entry Point. 
    Combines 'Advanced Engine' logic with 'Zoho' context inputs.
    """
    output = BytesIO()
    reco_dt = pd.to_datetime(month_str + "-01") if month_str else None
    
    if manual_inputs is None:
        manual_inputs = {
            'sales': {'taxable':0, 'igst':0, 'cgst':0, 'sgst':0},
            'opening': {'igst':0, 'cgst':0, 'sgst':0}
        }

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        try:
            # 1. Cleaning Phase
            # Use Advanced Cleaning for Portal
            xls_p = pd.ExcelFile(file_portal)
            raw_portal = filter_portal_sheets(xls_p)
            clean_portal_dict = {} 
            rcm_frames = []
            
            for sheet, df_raw in raw_portal.items():
                df = clean_portal_df(df_raw, sheet)
                if df.empty: continue
                if 'Reverse Charge' in df.columns:
                    is_rcm = df['Reverse Charge'].astype(str).str.strip().str.lower().isin(['yes', 'y'])
                    if is_rcm.any():
                        rcm_data = df[is_rcm].copy(); rcm_data['Source'] = sheet
                        rcm_frames.append(rcm_data); df = df[~is_rcm]
                clean_portal_dict[sheet] = df
            if rcm_frames: clean_portal_dict['RCM Combined'] = pd.concat(rcm_frames, ignore_index=True)

            # Use Zoho Cleaning for Books (Context Preserved)
            clean_zoho_dict = clean_zoho_data(file_zoho)

            # 2. Engine Phase (Advanced Map-Based Logic)
            books_maps_tuple = generate_lookup_map(clean_zoho_dict) 
            portal_maps_tuple = generate_lookup_map(clean_portal_dict)

            # 3. Processing Phase
            processed_portal = {}
            for sheet_name, df in clean_portal_dict.items():
                df_final = apply_reco_logic(df, books_maps_tuple, 'As per Books', True, reco_dt)
                processed_portal[sheet_name] = df_final

            # Process Books (Zoho)
            for sheet_name, data in clean_zoho_dict.items():
                df_final = apply_reco_logic(data['df'], portal_maps_tuple, 'As per Portal', False, None)
                # Update the df inside the dictionary
                clean_zoho_dict[sheet_name]['df'] = df_final

            # 4. Reporting Phase
            generate_master_dashboard(writer, processed_portal, clean_zoho_dict, manual_inputs)
            
            sorted_sheets = get_smart_sorted_order(processed_portal, clean_zoho_dict)
            
            for sheet_title, df_final in sorted_sheets:
                add_formatting_and_subtotals(writer, df_final, sheet_title)
                
        except Exception as e:
            logging.error(f"Error in Advanced Zoho Reco Engine: {e}")
            raise e

    output.seek(0)
    return output