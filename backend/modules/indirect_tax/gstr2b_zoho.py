import pandas as pd
import os
import re
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

# --- CONFIGURATION ---
SHEETS_TO_DELETE_ALWAYS = [
    'imp', 'imp_services', 'nil,exempt,non-gst,composition', 
    'hsn', 'advance paid', 'advance adjusted'
]
SHEETS_TO_CHECK = [
    'b2b', 'b2bur', 'dn', 'dn_ur', 'reverse charge'
]

def write_sheet_with_subtotals(writer, df, sheet_name):
    """
    Writes DF to Excel using XlsxWriter and adds:
    1. Bold Filters
    2. Subtotals (Formula = 9) at the bottom
    """
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    (num_rows, num_cols) = df.shape

    bold_format = workbook.add_format({'bold': True})
    number_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})
    
    # Write "Filter Total" label
    worksheet.write(num_rows + 1, 0, 'Filter Total', bold_format)
    
    # Add Subtotal Formulas dynamically
    target_cols = ['Taxable Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount']
    
    for col_name in target_cols:
        if col_name in df.columns:
            col_idx = df.columns.get_loc(col_name)
            col_letter = xl_col_to_name(col_idx)
            # Formula: =SUBTOTAL(9, C2:C100)
            formula = f'=SUBTOTAL(9,{col_letter}2:{col_letter}{num_rows+1})'
            worksheet.write_formula(num_rows + 1, col_idx, formula, number_format)

    # Add AutoFilter
    worksheet.autofilter(0, 0, num_rows, num_cols - 1)

def process_gstr2b_zoho(file_path, output_folder, custom_filename=None):
    """
    Main Processing Logic with RCM De-duplication.
    """
    try:
        xls = pd.ExcelFile(file_path)
        
        # Naming Logic
        if custom_filename and str(custom_filename).strip():
            clean_name = re.sub(r'[\\/*?:"<>|]', '-', str(custom_filename).strip())
            output_filename = f"{clean_name}.xlsx" if not clean_name.endswith('.xlsx') else clean_name
        else:
            output_filename = "Zoho_2B_Cleaned.xlsx"
            
        output_full_path = os.path.join(output_folder, output_filename)
        
        # Dictionary to hold dataframes in memory before writing
        # Structure: { 'sheet_name_lower': { 'original_name': 'B2B', 'df': DataFrame } }
        sheet_map = {}

        # 1. READ PHASE
        for sheet_name in xls.sheet_names:
            sheet_name_lower = sheet_name.lower().strip()
            
            df_to_keep = None 

            # Filtering Rules
            if sheet_name_lower in SHEETS_TO_DELETE_ALWAYS:
                continue
                
            elif sheet_name_lower in SHEETS_TO_CHECK:
                try:
                    df_check = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                    if len(df_check) < 3 or df_check.iloc[2].isnull().all():
                        continue
                    else:
                        df_to_keep = pd.read_excel(xls, sheet_name=sheet_name, header=1)
                except:
                    continue
            else:
                try:
                    df_to_keep = pd.read_excel(xls, sheet_name=sheet_name, header=1)
                except:
                    continue
            
            if df_to_keep is not None and not df_to_keep.empty:
                # Fix Footer / Ghost Rows
                if 'Invoice Number' in df_to_keep.columns:
                    last_valid_index = df_to_keep['Invoice Number'].last_valid_index()
                    if last_valid_index is not None:
                        df_to_keep = df_to_keep.iloc[:last_valid_index + 1]
                
                sheet_map[sheet_name_lower] = {
                    'original_name': sheet_name,
                    'df': df_to_keep
                }

        # Close source file early
        xls.close()

        # 2. DE-DUPLICATION PHASE (The Fix)
        # If 'b2b' and 'reverse charge' both exist, remove RCM invoices from B2B
        if 'b2b' in sheet_map and 'reverse charge' in sheet_map:
            b2b_df = sheet_map['b2b']['df']
            rcm_df = sheet_map['reverse charge']['df']
            
            if 'Invoice Number' in b2b_df.columns and 'Invoice Number' in rcm_df.columns:
                # Get list of Invoice Numbers present in RCM sheet
                rcm_invoices = rcm_df['Invoice Number'].unique()
                
                # Keep only rows in B2B that are NOT in the RCM list
                # "Consider it in RCM sheet only and delete from B2B"
                clean_b2b_df = b2b_df[~b2b_df['Invoice Number'].isin(rcm_invoices)].copy()
                
                # Update the map
                sheet_map['b2b']['df'] = clean_b2b_df
                
                print(f"De-duplication: Removed {len(b2b_df) - len(clean_b2b_df)} RCM invoices from B2B sheet.")

        # 3. WRITE PHASE
        sheets_kept = 0
        summary_data = [] 

        with pd.ExcelWriter(output_full_path, engine='xlsxwriter') as writer:
            
            for key, data in sheet_map.items():
                df_to_keep = data['df']
                original_name = data['original_name']
                
                if df_to_keep.empty:
                    continue

                # Rename Sheet
                new_sheet_name = f"{original_name} as per Books"
                if len(new_sheet_name) > 31:
                    new_sheet_name = new_sheet_name[:31]

                # Add Columns
                df_to_keep['As per portal'] = ''
                df_to_keep['Difference'] = ''
                df_to_keep['Remarks'] = ''
                
                # Drop Empty Cess
                if 'Cess Amount' in df_to_keep.columns:
                    if (pd.to_numeric(df_to_keep['Cess Amount'], errors='coerce').fillna(0) <= 0).all():
                        df_to_keep = df_to_keep.drop(columns=['Cess Amount'])

                # Reorder Columns
                cess_exists = 'Cess Amount' in df_to_keep.columns
                
                final_order = [
                    'GSTIN/UIN of Recipient', 'Vendor Name', 'Invoice Number', 'Invoice date',
                    'Invoice Value', 'Place Of Supply', 'Rate', 'Taxable Value',
                    'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount',
                    'As per portal', 'Difference', 'Remarks'
                ]
                
                if cess_exists:
                    final_order.insert(11, 'Cess Amount')

                # Select existing cols
                existing_cols = [c for c in final_order if c in df_to_keep.columns]
                df_to_keep = df_to_keep.reindex(columns=existing_cols)
                
                # Write Sheet
                write_sheet_with_subtotals(writer, df_to_keep, new_sheet_name)
                sheets_kept += 1

                # Add to Summary
                for col in ['Taxable Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount']:
                    if col in df_to_keep.columns:
                        df_to_keep[col] = pd.to_numeric(df_to_keep[col], errors='coerce').fillna(0)
                
                summary_data.append({
                    'Category': original_name,
                    'Taxable': df_to_keep['Taxable Value'].sum() if 'Taxable Value' in df_to_keep.columns else 0,
                    'IGST': df_to_keep['IGST Tax Amount'].sum() if 'IGST Tax Amount' in df_to_keep.columns else 0,
                    'CGST': df_to_keep['CGST Tax Amount'].sum() if 'CGST Tax Amount' in df_to_keep.columns else 0,
                    'SGST': df_to_keep['SGST Tax Amount'].sum() if 'SGST Tax Amount' in df_to_keep.columns else 0,
                })

        if sheets_kept == 0:
            return {"success": False, "error": "No valid sheets found (or files were empty)."}

        # Clean up input file
        if os.path.exists(file_path):
            os.remove(file_path)

        return {
            "success": True,
            "message": "Zoho GSTR-2B Processed Successfully.",
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename,
            "summary_data": summary_data
        }

    except Exception as e:
        # Ensure file is closed even on error
        if 'xls' in locals():
            try: xls.close()
            except: pass
        return {"success": False, "error": str(e)}