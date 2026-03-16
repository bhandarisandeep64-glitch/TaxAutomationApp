import pandas as pd
import numpy as np
import io
import re
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font

# 1. Tax Doubling Magic
def format_tax_rate(val):
    if pd.isna(val): return val
    val_str = str(val)
    match = re.search(r'([0-9.]+)', val_str)
    if match:
        num = float(match.group(1))
        doubled = num * 2
        return f"{doubled:g}% GST S"
    return val_str

# 2. Upgraded Cleaner (Keeps your logic, adds duplicate column protection)
def clean_purchase_data(df, is_rcm=False, is_import=False):
    # Reset index and drop duplicate columns immediately
    df = df.reset_index(drop=True)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Ensure required columns exist
    for col in ['Account', 'Label', 'Date', 'Debit', 'Credit', 'Taxable Amt.']:
        if col not in df.columns: df[col] = 0.0 if 'Amt' in col or col in ['Debit', 'Credit'] else ''

    df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
    df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
    df['Taxable Amt.'] = pd.to_numeric(df['Taxable Amt.'], errors='coerce').fillna(0)

    # Tax Amount (Keeping positive for Reco)
    tax_amount = df[['Debit', 'Credit']].max(axis=1)

    account_series = df['Account'].astype(str)
    is_igst = account_series.str.contains('igst', case=False, na=False)
    is_cgst = account_series.str.contains('cgst', case=False, na=False)
    is_sgst = account_series.str.contains('sgst', case=False, na=False)

    df['IGST'] = np.where(is_igst, tax_amount, 0.0)
    df['CGST'] = np.where(is_cgst, tax_amount, 0.0)
    df['SGST'] = np.where(is_sgst, tax_amount, 0.0)

    mask_missing_sgst = (df['CGST'] != 0) & (df['SGST'] == 0)
    df.loc[mask_missing_sgst, 'SGST'] = df.loc[mask_missing_sgst, 'CGST']

    # Rename to Master Format
    df = df.rename(columns={
        'Partner': 'Vendor Name',
        'Number': 'Invoice Number',
        'Label': 'Tax Rate',
        'Taxable Amt.': 'Taxable Amount'
    })
    
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df['Tax Rate'] = df['Tax Rate'].apply(format_tax_rate)
    df['Total'] = df['Taxable Amount'] + df['IGST'] + df['CGST'] + df['SGST']

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%d-%m-%Y')

    # Assign specific type
    if is_rcm: df['Type'] = 'RCM'
    elif is_import: df['Type'] = 'Import'
    else: df['Type'] = 'Regular'

    final_columns = [
        'Vendor Name', 'GSTIN', 'Date', 'Reference', 'Invoice Number', 
        'Account', 'Tax Rate', 'Type', 'Total', 'Taxable Amount', 'IGST', 'CGST', 'SGST'
    ]
    
    for col in final_columns:
        if col not in df.columns: df[col] = '' 
            
    return df[final_columns]

# 3. Wrapper Engine using YOUR original Dictionary & Mask logic
def generate_mario_purchase_report(files_dict):
    processed_results = {}

    def load_slot(key):
        if key in files_dict and files_dict[key].filename != '':
            return pd.read_excel(files_dict[key])
        return None

    # A. REGULAR
    reg_cgst = load_slot('file_reg_cgst')
    reg_igst = load_slot('file_reg_igst')
    reg_dfs = [df for df in [reg_cgst, reg_igst] if df is not None]

    if reg_dfs:
        reg_df = pd.concat(reg_dfs, ignore_index=True)
        if 'Credit' in reg_df.columns:
            v_cn_mask = pd.to_numeric(reg_df['Credit'], errors='coerce').fillna(0) != 0
            reg_normal = reg_df[~v_cn_mask].copy()
            reg_cn = reg_df[v_cn_mask].copy()
            
            if not reg_normal.empty: processed_results['B2B as per Books'] = clean_purchase_data(reg_normal, is_rcm=False)
            if not reg_cn.empty: processed_results['V CN as per Books'] = clean_purchase_data(reg_cn, is_rcm=False)
        else:
            processed_results['B2B as per Books'] = clean_purchase_data(reg_df, is_rcm=False)

    # B. RCM
    rcm_cgst = load_slot('file_rcm_cgst')
    rcm_igst = load_slot('file_rcm_igst')
    rcm_dfs = [df for df in [rcm_cgst, rcm_igst] if df is not None]

    if rcm_dfs:
        rcm_df = pd.concat(rcm_dfs, ignore_index=True)
        if 'Debit' in rcm_df.columns:
            rcm_cn_mask = pd.to_numeric(rcm_df['Debit'], errors='coerce').fillna(0) != 0
            rcm_normal = rcm_df[~rcm_cn_mask].copy()
            rcm_cn = rcm_df[rcm_cn_mask].copy()
            
            if not rcm_normal.empty: processed_results['RCM as per Books'] = clean_purchase_data(rcm_normal, is_rcm=True)
            if not rcm_cn.empty: processed_results['V CN RCM as per Books'] = clean_purchase_data(rcm_cn, is_rcm=True)
        else:
            processed_results['RCM as per Books'] = clean_purchase_data(rcm_df, is_rcm=True)

    # C. IMPORT
    imp_cgst = load_slot('file_import_cgst')
    imp_igst = load_slot('file_import_igst')
    imp_dfs = [df for df in [imp_cgst, imp_igst] if df is not None]

    if imp_dfs:
        imp_df = pd.concat(imp_dfs, ignore_index=True)
        if 'Credit' in imp_df.columns:
            imp_cn_mask = pd.to_numeric(imp_df['Credit'], errors='coerce').fillna(0) != 0
            imp_normal = imp_df[~imp_cn_mask].copy()
            imp_cn = imp_df[imp_cn_mask].copy()
            
            if not imp_normal.empty: processed_results['Import as per Books'] = clean_purchase_data(imp_normal, is_import=True)
            if not imp_cn.empty: processed_results['Import CN as per Books'] = clean_purchase_data(imp_cn, is_import=True)
        else:
            processed_results['Import as per Books'] = clean_purchase_data(imp_df, is_import=True)

    if not processed_results:
        raise ValueError("No valid data found in uploaded files.")

    # 4. Stream to Excel & Apply Your Original Openpyxl Subtotal Formulas
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in processed_results.items():
            if not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    # Reload with openpyxl in memory to add formatting
    output.seek(0)
    wb = openpyxl.load_workbook(output)
    sum_cols = ['Total', 'Taxable Amount', 'IGST', 'CGST', 'SGST']

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        max_row = ws.max_row
        if max_row < 2: continue

        ws.auto_filter.ref = ws.dimensions
        
        total_row_idx = max_row + 1
        ws.cell(row=total_row_idx, column=1).value = "GRAND TOTAL"
        ws.cell(row=total_row_idx, column=1).font = Font(bold=True)

        headers = [cell.value for cell in ws[1]]
        for col_name in sum_cols:
            if col_name in headers:
                col_idx = headers.index(col_name) + 1
                col_letter = get_column_letter(col_idx)
                
                # Excel Subtotal Formula (Updates if you filter rows!)
                formula = f"=SUBTOTAL(9, {col_letter}2:{col_letter}{max_row})"
                
                cell = ws.cell(row=total_row_idx, column=col_idx)
                cell.value = formula
                cell.font = Font(bold=True)
                cell.number_format = '#,##0.00'

    final_output = io.BytesIO()
    wb.save(final_output)
    final_output.seek(0)

    return final_output