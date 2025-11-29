import pandas as pd
from io import BytesIO
import numpy as np
from xlsxwriter.utility import xl_col_to_name

# ==========================================
#  SECTION 1: SHARED UTILITIES
# ==========================================

def add_formatting_and_subtotals(writer, df, sheet_name):
    if df.empty: return 
    
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
    
    # Subtotals
    target_cols = [
        'Taxable Value', 'Invoice Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount',
        'IGST', 'CGST', 'SGST', 'Cess', 'Total', 'Taxable Amt.', 'Debit', 'Credit',
        'As per portal', 'As per Books', 'Difference'
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
    # 1. Header Logic
    header_idx = -1
    search_terms = ['gstin of supplier', 'invoice number', 'note number', 'bill of entry number']
    for i in range(min(10, len(df_raw))):
        row_str = " ".join(df_raw.iloc[i].astype(str).fillna('').values).lower()
        if any(term in row_str for term in search_terms):
            header_idx = i; break
    if header_idx == -1: return pd.DataFrame()

    # Create DF starting after header
    df_data = df_raw.iloc[header_idx+1:].reset_index(drop=True)
    # Capture Row 1 as list (Fix for 'Columns must be same length' error)
    row1 = df_raw.iloc[header_idx].astype(str).replace('nan', '').str.strip().tolist()
    
    if header_idx + 1 < len(df_raw):
        # Capture Row 2 as list
        row2 = df_raw.iloc[header_idx+1].astype(str).replace('nan', '').str.strip().tolist()
        
        if any('tax' in val.lower() for val in row2):
            # Multi-row header detected
            df_data = df_raw.iloc[header_idx+2:].reset_index(drop=True)
            new_cols = [c2 if c2 else c1 if c1 else "Unknown" for c1, c2 in zip(row1, row2)]
            
            # Safe Assignment
            if len(new_cols) == df_data.shape[1]:
                df_data.columns = new_cols
        else: 
            # Single row header
            if len(row1) == df_data.shape[1]:
                df_data.columns = row1
    else: 
        # Fallback single row header
        if len(row1) == df_data.shape[1]:
            df_data.columns = row1

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
#  SECTION 3: ODOO CLEANING LOGIC (4 SLOTS)
# ==========================================

def clean_odoo_data(df, is_rcm=False):
    required_cols = ['Account', 'Label', 'Date']
    for col in required_cols:
        if col not in df.columns: df[col] = ''

    if 'Debit' not in df.columns: df['Debit'] = 0.0
    if 'Credit' not in df.columns: df['Credit'] = 0.0
    
    df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
    df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)

    # Tax Calculation
    account_series = df['Account'].astype(str)
    is_igst = account_series.str.contains('igst', case=False, na=False)
    is_cgst = account_series.str.contains('cgst', case=False, na=False)
    is_sgst = account_series.str.contains('sgst', case=False, na=False)
    
    if is_rcm:
        condition = df['Debit'] != 0
        df['Tax_Amount'] = np.where(condition, df['Debit'], df['Credit'])
    else:
        condition = df['Credit'] != 0
        df['Tax_Amount'] = np.where(condition, df['Credit'], df['Debit'])

    df['IGST'] = np.where(is_igst, df['Tax_Amount'], 0.0)
    df['CGST'] = np.where(is_cgst, df['Tax_Amount'], 0.0)
    df['SGST'] = np.where(is_sgst, df['Tax_Amount'], 0.0)

    mask_missing_sgst = (df['CGST'] != 0) & (df['SGST'] == 0)
    df.loc[mask_missing_sgst, 'SGST'] = df.loc[mask_missing_sgst, 'CGST']

    if 'Label' in df.columns:
        df['Rate'] = df['Label'].astype(str).str.extract(r'(\d+\.?\d*)%').astype(float)
        df['Rate_Str'] = df['Rate'].map('{:.2f}%'.format, na_action='ignore')
    else:
        df['Rate'] = 0.0; df['Rate_Str'] = '0.00%'
    
    if 'Taxable Amt.' not in df.columns: df['Taxable Amt.'] = 0.0
    df['Taxable Amt.'] = pd.to_numeric(df['Taxable Amt.'], errors='coerce').fillna(0)
    df['Total'] = df['Taxable Amt.'] + df['IGST'] + df['CGST'] + df['SGST']
    
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%d-%m-%Y')

    # Mapping Reference/Number to Invoice Number
    if 'Reference' in df.columns:
        df['Invoice Number'] = df['Reference'].fillna(df['Number'] if 'Number' in df.columns else '')
    elif 'Number' in df.columns:
        df['Invoice Number'] = df['Number']

    final_columns = [
        'Partner', 'GSTIN', 'Date', 'Invoice Number', 'Number', 'Reference', 'Account', 
        'Label', 'Rate_Str', 'Total', 'Taxable Amt.', 'IGST', 'CGST', 'SGST',
        'As per Portal', 'Difference', 'Remarks'
    ]
    for col in final_columns:
        if col not in df.columns: df[col] = '' 
    return df[final_columns]

def process_odoo_logic_4files(file_dict):
    """
    Processes the 4 distinct Odoo files:
    - reg_cgst, reg_igst (Combines to B2B + V CN)
    - rcm_cgst, rcm_igst (Combines to RCM + V CN RCM)
    """
    processed_results = {}

    def load_df(key):
        file = file_dict.get(key)
        if not file: return None
        try:
            # Check filename extension manually or try reading as excel then csv
            try:
                return pd.read_excel(file)
            except:
                file.seek(0)
                return pd.read_csv(file)
        except: return None

    # --- 1. REGULAR (B2B) ---
    reg_cgst = load_df('odoo_reg_cgst')
    reg_igst = load_df('odoo_reg_igst')
    regular_dfs = [d for d in [reg_cgst, reg_igst] if d is not None]

    if regular_dfs:
        reg_df = pd.concat(regular_dfs, ignore_index=True)
        if 'Credit' in reg_df.columns:
            v_cn_mask = reg_df['Credit'] != 0
            processed_results['B2B as per Books'] = clean_odoo_data(reg_df[~v_cn_mask].copy(), is_rcm=False)
            processed_results['V CN as per Books'] = clean_odoo_data(reg_df[v_cn_mask].copy(), is_rcm=False)
        else:
            processed_results['B2B as per Books'] = clean_odoo_data(reg_df, is_rcm=False)

    # --- 2. RCM ---
    rcm_cgst = load_df('odoo_rcm_cgst')
    rcm_igst = load_df('odoo_rcm_igst')
    rcm_dfs = [d for d in [rcm_cgst, rcm_igst] if d is not None]

    if rcm_dfs:
        rcm_df = pd.concat(rcm_dfs, ignore_index=True)
        if 'Debit' in rcm_df.columns:
            # For RCM, Credit Notes usually have Debit values
            rcm_cn_mask = rcm_df['Debit'] != 0
            
            rcm_cn_data = rcm_df[rcm_cn_mask].copy()
            # Flip Taxable for RCM CN
            if 'Taxable Amt.' in rcm_cn_data.columns: 
                rcm_cn_data['Taxable Amt.'] = rcm_cn_data['Taxable Amt.'] * -1
            
            processed_results['RCM as per Books'] = clean_odoo_data(rcm_df[~rcm_cn_mask].copy(), is_rcm=True)
            processed_results['V CN RCM as per Books'] = clean_odoo_data(rcm_cn_data, is_rcm=True)
        else:
            processed_results['RCM as per Books'] = clean_odoo_data(rcm_df, is_rcm=True)

    return processed_results

# ==========================================
#  SECTION 4: RECO ENGINE (MATCHING)
# ==========================================

def generate_lookup_map(data_source):
    lookup_map = {}
    for key, val in data_source.items():
        df = val if isinstance(val, pd.DataFrame) else val
        col_inv = 'Invoice Number'
        col_tax = 'Taxable Value' if 'Taxable Value' in df.columns else 'Taxable Amt.'

        if col_inv in df.columns and col_tax in df.columns:
            for _, row in df.iterrows():
                inv = str(row[col_inv]).strip().lower()
                tax_val = float(row[col_tax])
                if inv not in lookup_map: lookup_map[inv] = tax_val
    return lookup_map

def apply_reco_logic(df, lookup_map, target_col, is_portal_sheet):
    # Initialize columns
    df[target_col] = 0.0
    df['Difference'] = 0.0
    df['Remarks'] = ''
    
    col_inv = 'Invoice Number'
    col_tax = 'Taxable Value' if 'Taxable Value' in df.columns else 'Taxable Amt.'
    
    if col_inv not in df.columns: return df

    def row_logic(row):
        inv_clean = str(row.get(col_inv, '')).strip().lower()
        my_tax = float(row.get(col_tax, 0))
        if inv_clean in lookup_map:
            other_val = lookup_map[inv_clean]
            diff = my_tax - other_val
            remark = "Match" if abs(diff) < 2 else "Mismatch"
            return pd.Series([other_val, diff, remark])
        else:
            remark = "Not in Books" if is_portal_sheet else "Not on Portal"
            return pd.Series([0.0, my_tax, remark])

    # Fix for 'Columns must be same length as key' error
    # Instead of direct DataFrame assignment, we split results
    results = df.apply(row_logic, axis=1)
    
    if not results.empty:
        # Access column indices of the results Series
        df[target_col] = results[0]
        df['Difference'] = results[1]
        df['Remarks'] = results[2]
        
    return df

# ==========================================
#  SECTION 5: MAIN ENTRY POINT
# ==========================================

def generate_reco_report(file_portal, odoo_files_dict):
    output = BytesIO()
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

        # 2. Odoo Processing (4 Files)
        clean_odoo_dict = process_odoo_logic_4files(odoo_files_dict)

        # 3. Indexing
        books_map = generate_lookup_map(clean_odoo_dict)
        portal_map = generate_lookup_map(clean_portal_dict)

        # 4. Write Portal
        for sheet_name, df in clean_portal_dict.items():
            df_final = apply_reco_logic(df, books_map, 'As per Books', True)
            add_formatting_and_subtotals(writer, df_final, f"Portal - {sheet_name}"[:31])

        # 5. Write Odoo
        for sheet_name, df in clean_odoo_dict.items():
            df_final = apply_reco_logic(df, portal_map, 'As per Portal', False)
            add_formatting_and_subtotals(writer, df_final, sheet_name[:31])

    output.seek(0)
    return output