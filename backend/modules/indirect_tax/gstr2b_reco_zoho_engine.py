import pandas as pd
from io import BytesIO
import numpy as np
import re
from xlsxwriter.utility import xl_col_to_name

# ==========================================
#  SECTION 1: SHARED UTILITIES
# ==========================================

def add_formatting_and_subtotals(writer, df, sheet_name):
    if df.empty: return 
    
    # Safety: Drop duplicate columns before writing to avoid Excel confusion
    df = df.loc[:, ~df.columns.duplicated()]
    
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    (num_rows, num_cols) = df.shape

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
    
    target_cols = [
        'Taxable Value', 'Invoice Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount',
        'IGST', 'CGST', 'SGST', 'Cess', 'Total', 'Taxable Amt.',
        'As per portal', 'As per Books', 'Difference'
    ]
    
    for col_name in target_cols:
        if col_name in df.columns:
            col_idx = df.columns.get_loc(col_name)
            col_letter = xl_col_to_name(col_idx)
            formula = f'=SUBTOTAL(9,{col_letter}2:{col_letter}{total_row})'
            worksheet.write_formula(total_row, col_idx, formula, number_format)
            
    if 'Remarks' in df.columns:
        rem_idx = df.columns.get_loc('Remarks')
        rem_letter = xl_col_to_name(rem_idx)
        range_str = f"{rem_letter}2:{rem_letter}{total_row}"
        worksheet.conditional_format(range_str, {'type': 'text', 'criteria': 'containing', 'value': 'Not', 'format': red_format})
        worksheet.conditional_format(range_str, {'type': 'text', 'criteria': 'containing', 'value': 'Match', 'format': green_format})

# ==========================================
#  SECTION 2: PORTAL CLEANING LOGIC (ADVANCED)
# ==========================================

def filter_portal_sheets(xls):
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
    header_idx = -1
    search_terms = ['gstin of supplier', 'invoice number', 'note number', 'bill of entry number']
    for i in range(min(10, len(df_raw))):
        row_str = " ".join(df_raw.iloc[i].astype(str).fillna('').values).lower()
        if any(term in row_str for term in search_terms):
            header_idx = i; break
    if header_idx == -1: return pd.DataFrame()

    df_data = df_raw.iloc[header_idx+1:].reset_index(drop=True)
    row1 = df_raw.iloc[header_idx].astype(str).replace('nan', '').str.strip().tolist()
    
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

    # === FIX: DROP DUPLICATE COLUMNS IMMEDIATELY ===
    df_data = df_data.loc[:, ~df_data.columns.duplicated()]

    numeric_cols = ['Taxable Value', 'Invoice Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount', 'Rate']
    for col in numeric_cols:
        if col in df_data.columns: df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)

    unwanted = ['period', 'filing date', 'applicable %', 'source', 'irn']
    cols_to_drop = [c for c in df_data.columns if any(kw in str(c).lower() for kw in unwanted)]
    if cols_to_drop: df_data.drop(columns=cols_to_drop, inplace=True, errors='ignore')

    df_data = df_data.replace(r'^\s*$', np.nan, regex=True).dropna(axis=1, how='all')
    for col in numeric_cols:
        if col in df_data.columns and df_data[col].abs().max() == 0: df_data.drop(columns=[col], inplace=True)
        
    return df_data

# ==========================================
#  SECTION 3: ZOHO CLEANING LOGIC (ADVANCED)
# ==========================================

def process_zoho_logic(file_content):
    xls = pd.ExcelFile(file_content)
    SHEETS_TO_DELETE = ['imp', 'imp_services', 'nil,exempt,non-gst,composition', 'hsn', 'advance paid', 'advance adjusted']
    SHEETS_TO_CHECK = ['b2b', 'b2bur', 'dn', 'dn_ur', 'reverse charge']
    sheet_map = {}

    for sheet_name in xls.sheet_names:
        sheet_lower = sheet_name.lower().strip()
        if sheet_lower in SHEETS_TO_DELETE: continue
        try:
            if sheet_lower in SHEETS_TO_CHECK:
                df_check = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                if len(df_check) < 3 or df_check.iloc[2].isnull().all(): continue
                df_to_keep = pd.read_excel(xls, sheet_name=sheet_name, header=1)
            else:
                df_to_keep = pd.read_excel(xls, sheet_name=sheet_name, header=1)
                
            if df_to_keep is not None and not df_to_keep.empty:
                # === FIX: DROP DUPLICATE COLUMNS ===
                df_to_keep = df_to_keep.loc[:, ~df_to_keep.columns.duplicated()]

                if 'Invoice Number' in df_to_keep.columns:
                    last_idx = df_to_keep['Invoice Number'].last_valid_index()
                    if last_idx is not None:
                        df_to_keep = df_to_keep.iloc[:last_idx + 1]
            
            if df_to_keep is not None:
                sheet_map[sheet_lower] = {'original_name': sheet_name, 'df': df_to_keep}
        except Exception:
            continue

    if 'b2b' in sheet_map and 'reverse charge' in sheet_map:
        b2b_df = sheet_map['b2b']['df']
        rcm_df = sheet_map['reverse charge']['df']
        if 'Invoice Number' in b2b_df.columns and 'Invoice Number' in rcm_df.columns:
            rcm_invoices = rcm_df['Invoice Number'].unique()
            clean_b2b = b2b_df[~b2b_df['Invoice Number'].isin(rcm_invoices)].copy()
            sheet_map['b2b']['df'] = clean_b2b

    return sheet_map

# ==========================================
#  SECTION 4: RECO ENGINE (FUZZY & SMART)
# ==========================================

def clean_inv_str(s):
    if pd.isna(s): return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(s).lower())

def generate_lookup_map(data_source):
    exact_map = {}
    amount_map = {} 
    
    for key, val in data_source.items():
        if isinstance(val, pd.DataFrame): df = val 
        else: df = val['df'] 
        
        col_inv = 'Invoice Number'
        col_tax = 'Taxable Value'

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
                    'tax_val': tax_val
                })

    return exact_map, amount_map

def apply_reco_logic(df, lookup_maps, target_col_name, is_portal_sheet, reco_month_dt=None):
    exact_map, amount_map = lookup_maps
    
    df[target_col_name] = 0.0; df['Difference'] = 0.0; df['Remarks'] = ''
    col_inv = 'Invoice Number'
    col_tax = 'Taxable Value'
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
        
        # 1. Exact Match
        if inv_exact_key in exact_map:
            other_val = exact_map[inv_exact_key]
            if abs(my_tax - other_val) < 2:
                match_found = True
                remark = "Match"
            else:
                 match_found = True 
                 remark = "Mismatch"

        # 2. Fuzzy Match (Amount Based)
        if not match_found:
            amt_key = f"{my_tax:.2f}"
            if amt_key in amount_map:
                candidates = amount_map[amt_key]
                for cand in candidates:
                    cand_clean = cand['clean_inv']
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

        # 3. Date Check
        if is_portal_sheet and reco_month_dt and pd.notnull(row.get(col_date)):
            inv_dt = row[col_date]
            if inv_dt < reco_month_dt:
                if "Match" in remark: remark += " (Old Inv)" 
                else: remark = "Previous Period Inv" 

        return pd.Series([other_val, diff, remark])

    results = df.apply(row_logic, axis=1)
    if not results.empty:
        df[target_col_name] = results[0]
        df['Difference'] = results[1]
        df['Remarks'] = results[2]
    return df

# ==========================================
#  SECTION 5: SMART SORTING & NAMING
# ==========================================

def get_smart_sorted_order(portal_dict, books_dict):
    portal_invs = {}
    for k, df in portal_dict.items():
        if 'Invoice Number' in df.columns:
            unique_invs = set(df['Invoice Number'].astype(str).str.lower().str.strip())
            portal_invs[k] = unique_invs
            
    books_invs = {}
    for k, d in books_dict.items():
        df = d['df']
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
            b_data = books_dict[best_match_name]
            b_sheet_title = f"{base_name} (Books)"
            final_order.append((b_sheet_title, b_data['df']))
            used_books.add(best_match_name)

    for b_name, b_data in books_dict.items():
        if b_name not in used_books:
            orig_name = b_data['original_name'][:20].strip()
            title = f"{orig_name} (Books)"
            final_order.append((title, b_data['df']))
            
    return final_order

# ==========================================
#  SECTION 6: MAIN ENTRY POINT (ZOHO)
# ==========================================

def generate_reco_report_zoho(file_portal, file_zoho, month_str=None):
    output = BytesIO()
    reco_dt = None
    
    # Try to parse month if provided
    if month_str:
        try:
            reco_dt = pd.to_datetime(month_str + "-01")
        except:
            pass 

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # 1. Portal Processing
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

        # 2. Zoho Processing
        clean_zoho_dict = process_zoho_logic(file_zoho)

        # 3. Indexing (Exact + Amount Based)
        books_maps_tuple = generate_lookup_map(clean_zoho_dict) 
        portal_maps_tuple = generate_lookup_map(clean_portal_dict)

        # 4. Apply Logic (Portal Sheets)
        processed_portal = {}
        for sheet_name, df in clean_portal_dict.items():
            df_final = apply_reco_logic(df, books_maps_tuple, 'As per Books', True, reco_dt)
            processed_portal[sheet_name] = df_final

        # 5. Apply Logic (Books Sheets)
        processed_books = {}
        for key, data in clean_zoho_dict.items():
            df = data['df']
            df_final = apply_reco_logic(df, portal_maps_tuple, 'As per Portal', False, None) 
            
            # Smart cleanup of empty Cess columns
            if 'Cess Amount' in df_final.columns:
                 if (pd.to_numeric(df_final['Cess Amount'], errors='coerce').fillna(0) <= 0).all():
                    df_final.drop(columns=['Cess Amount'], inplace=True)
            processed_books[key] = {'original_name': data['original_name'], 'df': df_final}

        # 6. Smart Sorting & Writing
        sorted_sheets = get_smart_sorted_order(processed_portal, processed_books)
        
        for sheet_title, df_final in sorted_sheets:
            add_formatting_and_subtotals(writer, df_final, sheet_title)

    output.seek(0)
    return output