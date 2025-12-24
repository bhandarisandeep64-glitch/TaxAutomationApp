import pandas as pd
from io import BytesIO
import numpy as np
from xlsxwriter.utility import xl_col_to_name

# ==========================================
#  SECTION 1: SHARED UTILITIES
# ==========================================

def add_formatting_and_subtotals(writer, df, sheet_name):
    if df.empty: return 
    
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
#  SECTION 2: PORTAL CLEANING LOGIC
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
#  SECTION 3: ZOHO CLEANING LOGIC
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
                
            if df_to_keep is not None and not df_to_keep.empty and 'Invoice Number' in df_to_keep.columns:
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
#  SECTION 4: RECO ENGINE (MATCHING)
# ==========================================

def generate_lookup_map(data_source):
    lookup_map = {}
    for key, val in data_source.items():
        if isinstance(val, pd.DataFrame): df = val 
        else: df = val['df'] 
        
        col_inv = 'Invoice Number'
        col_tax = 'Taxable Value'

        if col_inv in df.columns and col_tax in df.columns:
            for _, row in df.iterrows():
                inv = str(row[col_inv]).strip().lower()
                tax_val = float(row[col_tax]) if pd.notnull(row[col_tax]) else 0.0
                if inv not in lookup_map: lookup_map[inv] = tax_val
                else: lookup_map[inv] += tax_val
    return lookup_map

def apply_reco_logic(df, lookup_map, target_col_name, is_portal_sheet):
    df[target_col_name] = 0.0; df['Difference'] = 0.0; df['Remarks'] = ''
    col_inv = 'Invoice Number'
    col_tax = 'Taxable Value'
    
    if col_inv not in df.columns: return df

    def row_logic(row):
        inv_clean = str(row.get(col_inv, '')).strip().lower()
        my_tax = float(row.get(col_tax, 0)) if pd.notnull(row.get(col_tax, 0)) else 0.0
        
        if inv_clean in lookup_map:
            other_val = lookup_map[inv_clean]
            diff = my_tax - other_val
            remark = "Match" if abs(diff) < 2 else "Mismatch"
            return pd.Series([other_val, diff, remark])
        else:
            remark = "Not in Books" if is_portal_sheet else "Not on Portal"
            return pd.Series([0.0, my_tax, remark])

    results = df.apply(row_logic, axis=1)
    if not results.empty:
        df[target_col_name] = results[0]
        df['Difference'] = results[1]
        df['Remarks'] = results[2]
    return df

# ==========================================
#  SECTION 5: MAIN ENTRY POINT (ZOHO)
# ==========================================

def generate_reco_report_zoho(file_portal, file_zoho):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        
        # 1. Portal
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

        # 2. Zoho
        clean_zoho_dict = process_zoho_logic(file_zoho)

        # 3. Indexing
        books_map = generate_lookup_map(clean_zoho_dict)
        portal_map = generate_lookup_map(clean_portal_dict)

        # 4. Write Portal
        for sheet_name, df in clean_portal_dict.items():
            df_final = apply_reco_logic(df, books_map, 'As per Books', True)
            add_formatting_and_subtotals(writer, df_final, f"Portal - {sheet_name}"[:31])

        # 5. Write Zoho
        for key, data in clean_zoho_dict.items():
            df = data['df']
            orig_name = data['original_name']
            df_final = apply_reco_logic(df, portal_map, 'As per Portal', False)
            
            if 'Cess Amount' in df_final.columns:
                if (pd.to_numeric(df_final['Cess Amount'], errors='coerce').fillna(0) <= 0).all():
                    df_final.drop(columns=['Cess Amount'], inplace=True)
                    
            add_formatting_and_subtotals(writer, df_final, f"Books - {orig_name}"[:31])

    output.seek(0)
    return output