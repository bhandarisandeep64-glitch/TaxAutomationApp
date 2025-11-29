import pandas as pd
import os
import re
import xlsxwriter
from io import BytesIO

# --- 1. HELPER: READ FILE ---
def read_file_from_path(filepath):
    """Reads Excel/CSV from disk path into DataFrame."""
    try:
        if str(filepath).lower().endswith('.csv'):
            return pd.read_csv(filepath, low_memory=False)
        else:
            return pd.read_excel(filepath)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return pd.DataFrame()

# --- 2. CLEANING LOGIC (Your Code) ---
def apply_cleaning_logic(df, sheet_name):
    """
    Applies the cleaning and transformation rules.
    """
    print(f"Starting cleanup for {sheet_name}...")

    # Standardize column names
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace('[^a-z0-9_]', '', regex=True)
    
    # Define Columns to Keep and Rename
    columns_to_keep_and_rename = {
        'date': 'Date',
        'entry_number': 'Entry Number',
        'invoicenumber': 'Entry Number',
        'invoice': 'Entry Number',
        'transaction_type': 'Transaction Type',
        'taxable_amount': 'Taxable Amount',
        'integratedtax': 'Integrated Tax',
        'centraltax': 'Central Tax',
        'stateuttax': 'State/UT Tax',
        'cessamount': 'Cess Amount',
        'customername': 'Customer Name',
        'gstin': 'GSTIN'
    }

    current_columns = df.columns.tolist()
    cols_to_select = [col for col in columns_to_keep_and_rename.keys() if col in current_columns]
    
    df_cleaned = df[cols_to_select].copy()
    
    rename_mapping = {std_name: proper_name for std_name, proper_name in columns_to_keep_and_rename.items() if std_name in df_cleaned.columns}
    df_cleaned = df_cleaned.rename(columns=rename_mapping)

    # Date Formatting
    if 'Date' in df_cleaned.columns:
        try:
            df_cleaned['Date'] = pd.to_datetime(df_cleaned['Date'], errors='coerce')
            df_cleaned['Date'] = df_cleaned['Date'].dt.strftime('%d-%m-%Y')
        except Exception as e:
            print(f"Warning: Could not format 'Date' column: {e}")

    # Add New Empty Columns
    if 'Date' in df_cleaned.columns:
        date_idx = df_cleaned.columns.get_loc('Date')
        if 'Customer Name' not in df_cleaned.columns:
            df_cleaned.insert(date_idx + 1, 'Customer Name', pd.NA)
        if 'GSTIN' not in df_cleaned.columns:
            df_cleaned.insert(date_idx + 2, 'GSTIN', pd.NA)

    # Calculate 'Total Value'
    tax_cols = ['Taxable Amount', 'Integrated Tax', 'Central Tax', 'State/UT Tax']
    for col in tax_cols:
        if col in df_cleaned.columns:
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce').fillna(0)

    calc_df = df_cleaned[[c for c in tax_cols if c in df_cleaned.columns]].fillna(0)
    df_cleaned['Total Value'] = calc_df.sum(axis=1)

    if 'Taxable Amount' in df_cleaned.columns:
        taxable_idx = df_cleaned.columns.get_loc('Taxable Amount')
        cols = df_cleaned.columns.tolist()
        cols.insert(taxable_idx, cols.pop(cols.index('Total Value')))
        df_cleaned = df_cleaned[cols]

    # Conditional Drop Logic for 'Cess Amount'
    if 'Cess Amount' in df_cleaned.columns:
        if df_cleaned['Cess Amount'].fillna(0).max() == 0:
            df_cleaned = df_cleaned.drop(columns=['Cess Amount'])

    return df_cleaned

# --- 3. SMART HEADER SEARCH (Adapted for Disk Read) ---
def clean_and_prepare_details(filepath, sheet_name):
    """
    Cleans the detail file and prepares it for merging (VLOOKUP).
    """
    df = None
    header_found = False
    
    search_terms = ['invoice', 'invoiceno', 'invoice#', 'entrynumber', 'creditnote', 'creditnote#', 'creditnoteno']
    
    # Try finding header in first 10 rows
    for skip_rows in range(10): 
        try:
            if str(filepath).lower().endswith('.csv'):
                df = pd.read_csv(filepath, header=skip_rows, low_memory=False)
            else:
                df = pd.read_excel(filepath, header=skip_rows)
            
            cols_check = df.columns.astype(str).str.strip().str.lower().str.replace('[^a-z0-9]', '', regex=True)
            
            if any(term in cols_check for term in search_terms):
                print(f"[{sheet_name}] Found valid headers on row index {skip_rows}.")
                header_found = True
                break
        except Exception:
            continue 
            
    if not header_found:
        print(f"WARNING: Could not automatically find a valid header row in {sheet_name}. Using default.")
        df = read_file_from_path(filepath)

    if df.empty: return pd.DataFrame()

    # Standard Cleaning Logic
    df.columns = df.columns.astype(str).str.strip().str.lower().str.replace('[^a-z0-9_]', '', regex=True)
    
    possible_keys = {
        'entry_number': ['entrynumber', 'invoice', 'invoiceno', 'invoicenumber', 'creditnote', 'creditnote#', 'creditnoteno', 'creditnotenumber'],
        'customer_name_temp': ['customername', 'partyname', 'clientname', 'customer'],
        'gstin_temp': ['gstin', 'gstinno', 'gstnumber', 'gst']
    }
    
    rename_map = {}
    for col in df.columns:
        for target, variants in possible_keys.items():
            if col in variants:
                rename_map[col] = target
                break
    
    df = df.rename(columns=rename_map)
    
    if 'entry_number' not in df.columns:
         print(f"WARNING: Could not identify Key in {sheet_name}.")
         return pd.DataFrame() 
         
    df = df.rename(columns={'entry_number': 'Entry Number'})
    
    if 'customer_name_temp' in df.columns:
        df = df.rename(columns={'customer_name_temp': 'Customer Name Temp'})
    else:
        df['Customer Name Temp'] = pd.NA
        
    if 'gstin_temp' in df.columns:
        df = df.rename(columns={'gstin_temp': 'GSTIN Temp'})
    else:
        df['GSTIN Temp'] = pd.NA

    df_lookup = df[['Entry Number', 'Customer Name Temp', 'GSTIN Temp']].copy()
    df_lookup = df_lookup.drop_duplicates(subset=['Entry Number'], keep='first')
    
    return df_lookup

# --- 4. MERGE LOGIC ---
def merge_details_to_headers(df_headers, df_details):
    """Performs a left merge to populate Customer Name and GSTIN."""
    if df_details.empty: return df_headers

    df_headers['Entry Number'] = df_headers['Entry Number'].astype(str)
    df_details['Entry Number'] = df_details['Entry Number'].astype(str)

    merged_df = df_headers.merge(df_details, on='Entry Number', how='left')
    
    if 'Customer Name Temp' in merged_df.columns:
        merged_df['Customer Name'] = merged_df['Customer Name'].fillna(merged_df['Customer Name Temp'])
    
    if 'GSTIN Temp' in merged_df.columns:
        merged_df['GSTIN'] = merged_df['GSTIN'].fillna(merged_df['GSTIN Temp'])
    
    merged_df = merged_df.drop(columns=['Customer Name Temp', 'GSTIN Temp'], errors='ignore')
    
    return merged_df

# --- 5. EXCEL SAVING ---
def save_to_excel_with_format(data_frames_dict, output_path):
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        bold_format = workbook.add_format({'bold': True})
        currency_format = workbook.add_format({'num_format': '#,##0.00'}) 
        bold_currency_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})

        for sheet_name, df in data_frames_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            
            (max_row, max_col) = df.shape
            if max_row > 0:
                worksheet.autofilter(0, 0, 0, max_col - 1)
            
            subtotal_cols = ['Total Value', 'Taxable Amount', 'Integrated Tax', 'Central Tax', 'State/UT Tax']
            subtotal_formulas = []
            
            for col_name in df.columns:
                if col_name in subtotal_cols:
                    col_idx = df.columns.get_loc(col_name)
                    worksheet.set_column(col_idx, col_idx, None, currency_format)
                    col_letter = chr(ord('A') + col_idx)
                    if col_idx >= 26: col_letter = 'Z'
                    
                    formula = f'=SUBTOTAL(9, {col_letter}2:{col_letter}{max_row + 1})'
                    subtotal_formulas.append({'index': col_idx, 'formula': formula})

            subtotal_row = max_row + 1 
            worksheet.write(subtotal_row, 0, 'TOTAL', bold_format)
            for item in subtotal_formulas:
                worksheet.write(subtotal_row, item['index'], item['formula'], bold_currency_format)

# --- 6. MAIN WRAPPER ---
def process_gstr1_zoho(file_paths_dict, output_folder, custom_filename=None):
    try:
        data_frames_to_save = {}
        lookup_dfs = []
        
        # 1. Invoice Details
        if 'file_invoice_details' in file_paths_dict:
            df_inv = clean_and_prepare_details(file_paths_dict['file_invoice_details'], 'Invoice Details')
            if not df_inv.empty: lookup_dfs.append(df_inv)
        
        # 2. Credit Note Details
        if 'file_credit_note_details' in file_paths_dict:
            df_cn = clean_and_prepare_details(file_paths_dict['file_credit_note_details'], 'Credit Note Details')
            if not df_cn.empty: lookup_dfs.append(df_cn)
        
        df_master_lookup = pd.DataFrame()
        if lookup_dfs:
            df_master_lookup = pd.concat(lookup_dfs, ignore_index=True)
            df_master_lookup = df_master_lookup.drop_duplicates(subset=['Entry Number'], keep='first')

        # 3. ICN Header
        if 'file_invoice_credit_notes' in file_paths_dict:
            df_icn = read_file_from_path(file_paths_dict['file_invoice_credit_notes'])
            df_cleaned_icn = apply_cleaning_logic(df_icn, 'ICN Header')
            if not df_master_lookup.empty:
                df_cleaned_icn = merge_details_to_headers(df_cleaned_icn, df_master_lookup)
            data_frames_to_save['Invoices'] = df_cleaned_icn

        # 4. Export Invoices
        if 'file_export_invoices' in file_paths_dict:
            df_export = read_file_from_path(file_paths_dict['file_export_invoices'])
            df_cleaned_export = apply_cleaning_logic(df_export, 'Export Invoices Header')
            if not df_master_lookup.empty:
                df_cleaned_export = merge_details_to_headers(df_cleaned_export, df_master_lookup)
            if 'GSTIN' in df_cleaned_export.columns:
                df_cleaned_export = df_cleaned_export.drop(columns=['GSTIN'])
            data_frames_to_save['Export Invoices'] = df_cleaned_export

        if not data_frames_to_save:
            return {"success": False, "error": "No Header files uploaded. Please upload 'Inv/CN Headers' or 'Export Invoices'."}

        # Save
        if custom_filename and str(custom_filename).strip():
            clean_name = re.sub(r'[\\/*?:"<>|]', '-', str(custom_filename).strip())
            output_filename = f"{clean_name}.xlsx" if not clean_name.endswith('.xlsx') else clean_name
        else:
            output_filename = "Zoho_Sales_Cleaned.xlsx"

        output_full_path = os.path.join(output_folder, output_filename)
        save_to_excel_with_format(data_frames_to_save, output_full_path)
        
        # Summary for Frontend
        summary_data = []
        for sheet, df in data_frames_to_save.items():
            summary_data.append({
                'Category': sheet,
                'Taxable': df['Taxable Amount'].sum() if 'Taxable Amount' in df.columns else 0,
                'IGST': df['Integrated Tax'].sum() if 'Integrated Tax' in df.columns else 0,
                'CGST': df['Central Tax'].sum() if 'Central Tax' in df.columns else 0,
                'SGST': df['State/UT Tax'].sum() if 'State/UT Tax' in df.columns else 0
            })

        # Cleanup
        for fp in file_paths_dict.values():
            if os.path.exists(fp): os.remove(fp)

        return {
            "success": True,
            "message": "Zoho Sales Processed Successfully.",
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename,
            "summary_data": summary_data
        }

    except Exception as e:
        return {"success": False, "error": f"Processing Error: {str(e)}"}