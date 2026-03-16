import pandas as pd
import numpy as np
import io
import re

# 1. The Tax Doubling Magic
def format_tax_rate(val):
    if pd.isna(val): return val
    val_str = str(val)
    match = re.search(r'([0-9.]+)', val_str)
    if match:
        num = float(match.group(1))
        doubled = num * 2
        return f"{doubled:g}% GST S"
    return val_str

def clean_purchase_data(df, purchase_type='Regular'):
    # Ensure required columns exist to avoid crashes
    for col in ['Account', 'Label', 'Date', 'Debit', 'Credit', 'Taxable Amt.']:
        if col not in df.columns: df[col] = 0.0 if 'Amt' in col or col in ['Debit', 'Credit'] else ''

    df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
    df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
    df['Taxable Amt.'] = pd.to_numeric(df['Taxable Amt.'], errors='coerce').fillna(0)

    # 2. Extract Tax Amount (Keeping it positive for Reco as requested!)
    # Since Odoo puts the amount in either Debit OR Credit, taking the max gets the exact positive value
    tax_amount = df[['Debit', 'Credit']].max(axis=1)

    # Identify tax types from the Account column
    account_series = df['Account'].astype(str)
    is_igst = account_series.str.contains('igst', case=False, na=False)
    is_cgst = account_series.str.contains('cgst', case=False, na=False)
    is_sgst = account_series.str.contains('sgst', case=False, na=False)

    df['IGST'] = np.where(is_igst, tax_amount, 0.0)
    df['CGST'] = np.where(is_cgst, tax_amount, 0.0)
    df['SGST'] = np.where(is_sgst, tax_amount, 0.0)

    # Auto-fill SGST if missing
    mask_missing_sgst = (df['CGST'] != 0) & (df['SGST'] == 0)
    df.loc[mask_missing_sgst, 'SGST'] = df.loc[mask_missing_sgst, 'CGST']

    # Rename and Format Columns to match Mario Sales
    df = df.rename(columns={
        'Partner': 'Vendor Name',
        'Number': 'Invoice Number',
        'Label': 'Tax Rate',
        'Taxable Amt.': 'Taxable Amount'
    })
    
    df['Tax Rate'] = df['Tax Rate'].apply(format_tax_rate)
    
    # Calculate Total based on the raw positive values
    df['Total'] = df['Taxable Amount'] + df['IGST'] + df['CGST'] + df['SGST']

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

    # Add the specific category tag (Regular, RCM, or Import)
    df['Type'] = purchase_type

    final_columns = [
        'Vendor Name', 'GSTIN', 'Date', 'Reference', 'Invoice Number', 
        'Account', 'Tax Rate', 'Type', 'Total', 'Taxable Amount', 'IGST', 'CGST', 'SGST'
    ]
    
    for col in final_columns:
        if col not in df.columns: df[col] = '' 
            
    return df[final_columns]

# --- THE MAIN ENGINE ROUTE ---
def generate_mario_purchase_report(files_dict):
    dataframes = []

    def load_and_process(file_key, purchase_type):
        if file_key in files_dict and files_dict[file_key].filename != '':
            df = pd.read_excel(files_dict[file_key])
            cleaned_df = clean_purchase_data(df, purchase_type=purchase_type)
            dataframes.append(cleaned_df)

    # Process all 6 possible uploaded files into their correct categories
    load_and_process('file_reg_cgst', 'Regular')
    load_and_process('file_reg_igst', 'Regular')
    load_and_process('file_rcm_cgst', 'RCM')
    load_and_process('file_rcm_igst', 'RCM')
    load_and_process('file_import_cgst', 'Import')
    load_and_process('file_import_igst', 'Import')

    if not dataframes:
        raise ValueError("Please upload at least one valid file.")

    combined_df = pd.concat(dataframes, ignore_index=True)

    # 3. Create the Grand Total Row
    totals = {
        'Vendor Name': 'GRAND TOTAL',
        'Total': combined_df['Total'].sum(),
        'Taxable Amount': combined_df['Taxable Amount'].sum(),
        'IGST': combined_df['IGST'].sum(),
        'CGST': combined_df['CGST'].sum(),
        'SGST': combined_df['SGST'].sum()
    }
    
    summary_row = pd.DataFrame([totals])
    final_df = pd.concat([combined_df, summary_row], ignore_index=True)

    # Stream the file directly
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False)
    output.seek(0)
    
    return output