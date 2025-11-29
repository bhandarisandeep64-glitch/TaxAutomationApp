import pandas as pd
import numpy as np
import re
import os
from openpyxl.utils import get_column_letter

def detect_file_type(df, filename):
    """
    Analyzes content to detect B2B/B2C and Tax Type.
    (Category detection moved to row-level in process_file_core)
    """
    # 1. Detect Tax Type (IGST vs CGST)
    tax = None
    if 'Label' in df.columns:
        label_str = df['Label'].astype(str).str.lower()
        if label_str.str.contains('igst').any():
            tax = 'IGST'
        elif label_str.str.contains('cgst').any() or label_str.str.contains('sgst').any():
            tax = 'CGST'
            
    if not tax:
        if 'igst' in filename.lower(): tax = 'IGST'
        elif 'cgst' in filename.lower() or 'sgst' in filename.lower(): tax = 'CGST'
    
    if not tax: tax = 'CGST' # Default

    # 2. Detect Invoice Type (B2B vs B2C)
    inv_type = 'B2C' # Default
    if 'GSTIN' in df.columns:
        valid_gstins = df['GSTIN'].astype(str).replace(['nan', 'False', ''], np.nan).dropna()
        if len(valid_gstins) > 0:
            inv_type = 'B2B'
    
    if 'b2b' in filename.lower(): inv_type = 'B2B'
    elif 'b2c' in filename.lower(): inv_type = 'B2C'

    return inv_type, tax

def process_file_core(df, filename, invoice_type, tax_type):
    """
    Core Logic:
    - Row-by-Row detection of Credit Notes (fixes misclassification).
    - Standardizes Tax and Amounts.
    """
    try:
        # Basic Clean
        for col in ['GSTIN', 'Number', 'Journal']:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(['nan', 'False'], '').str.strip()
            else:
                df[col] = ''

        # --- LOGIC 1: Detect Nature (Invoice vs CDNR) Row-by-Row ---
        # This fixes the issue where whole files were wrongly marked as CDNR
        
        is_cn_mask = pd.Series([False] * len(df))
        
        # Check Journal Column
        if 'Journal' in df.columns:
            is_cn_mask |= df['Journal'].str.contains('Credit Note|Reversal', case=False, regex=True)
            
        # Check Number Column (Common Odoo patterns: RINV, CN, etc.)
        if 'Number' in df.columns:
            is_cn_mask |= df['Number'].str.contains('RINV|CN|Credit', case=False, regex=True)
            
        # Fallback: If filename strongly implies Credit Note, apply to all (unless contradicted)
        if 'credit' in filename.lower() or 'cdnr' in filename.lower() or 'reversal' in filename.lower():
             # Only apply if we didn't find specific invoice markers? 
             # Actually, safer to trust filename if column data is missing.
             if not is_cn_mask.any(): 
                 is_cn_mask[:] = True

        # Assign Nature based on the mask
        df['Nature'] = np.where(is_cn_mask, f"{invoice_type} CDNR", invoice_type)

        # --- LOGIC 2: Handle Debit/Credit ---
        df['Abs_Tax_Amount'] = 0.0
        if 'Debit' in df.columns and 'Credit' in df.columns:
            df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
            df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
            
            debit_mask = df['Debit'] != 0
            credit_mask = df['Credit'] != 0
            
            df.loc[debit_mask, 'Abs_Tax_Amount'] = df.loc[debit_mask, 'Debit'].abs()
            df.loc[credit_mask, 'Abs_Tax_Amount'] = df.loc[credit_mask, 'Credit'].abs()
            
            # Credit Notes usually appear in Debit column in Odoo Ledger, so we negate them for reporting
            df.loc[debit_mask, 'Credit'] = df.loc[debit_mask, 'Debit'].abs() * -1
        elif 'Credit' in df.columns:
            df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
            df['Abs_Tax_Amount'] = df['Credit'].abs()

        # --- LOGIC 3: Recalculate Taxable Value ---
        if 'Label' in df.columns:
            df['extracted_rate'] = df['Label'].astype(str).str.extract(r'(\d*\.?\d+)%').astype(float)
            mask_valid = df['extracted_rate'] > 0
            
            # Taxable = Tax / (Rate/100)
            df.loc[mask_valid, 'Taxable Amt.'] = (df.loc[mask_valid, 'Abs_Tax_Amount'] / (df.loc[mask_valid, 'extracted_rate'] / 100)).round(2)
            
            # Handle Negative Sign for Taxable Amount
            # If it's a credit note row (determined by mask), value should likely be negative
            # Or if Credit column is negative.
            if 'Credit' in df.columns:
                neg_mask = df['Credit'] < 0
                df.loc[neg_mask, 'Taxable Amt.'] = df.loc[neg_mask, 'Taxable Amt.'].abs() * -1

        # --- LOGIC 4: Tax Columns ---
        df['IGST'] = 0.0
        df['CGST'] = 0.0
        df['SGST'] = 0.0

        if tax_type == 'CGST':
            df['CGST'] = df['Credit']
            df['SGST'] = df['Credit']
        elif tax_type == 'IGST':
            df['IGST'] = df['Credit']
        
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%d-%m-%Y')
            
        return df

    except Exception as e:
        print(f"Error inside core logic: {e}")
        return pd.DataFrame()

def process_gstr1_odoo(file_paths, output_folder, custom_filename=None):
    """
    Main Wrapper:
    1. Reads files.
    2. Processes rows.
    3. Generates formatted Excel with Subtotals and AutoFilter.
    """
    try:
        processed_dfs = []
        
        for fp in file_paths:
            try:
                if fp.endswith('.csv'):
                    df = pd.read_csv(fp)
                else:
                    df = pd.read_excel(fp)
                
                filename = os.path.basename(fp).lower()
                inv_type, tax = detect_file_type(df, filename)
                
                print(f"Processing {filename}: Detected {inv_type} | {tax}")
                
                df_processed = process_file_core(df, filename, inv_type, tax)
                if not df_processed.empty:
                    processed_dfs.append(df_processed)
                    
            except Exception as e:
                print(f"Failed to process file {fp}: {str(e)}")
                continue

        if not processed_dfs:
            return {"success": False, "error": "Could not process any valid data."}

        # 2. Merge
        merged_df = pd.concat(processed_dfs, ignore_index=True)

        # 3. Calculate Lines
        merged_df['Line_Total'] = (
            merged_df['Taxable Amt.'].fillna(0) + 
            merged_df['IGST'].fillna(0) + 
            merged_df['CGST'].fillna(0) + 
            merged_df['SGST'].fillna(0)
        )
        
        # Invoice Totals
        if 'Number' in merged_df.columns:
            inv_totals = merged_df.groupby('Number')['Line_Total'].sum().reset_index()
            inv_totals.rename(columns={'Line_Total': 'Invoice Total'}, inplace=True)
            if 'Invoice Total' in merged_df.columns: del merged_df['Invoice Total']
            merged_df = pd.merge(merged_df, inv_totals, on='Number', how='left')

        # 4. Prepare Final Data
        final_cols = [
            'Nature', 'Partner', 'GSTIN', 'PAN No.', 'Date', 'Number', 
            'Reference', 'Label', 'Invoice Total', 'Taxable Amt.', 'IGST', 'CGST', 'SGST'
        ]
        existing_cols = [c for c in final_cols if c in merged_df.columns]
        final_df = merged_df[existing_cols].copy()

        # 5. Create Summary
        summary = merged_df.groupby('Nature').agg(
            Taxable=('Taxable Amt.', 'sum'),
            IGST=('IGST', 'sum'),
            CGST=('CGST', 'sum'),
            SGST=('SGST', 'sum')
        ).reset_index()
        summary.rename(columns={'Nature': 'Category'}, inplace=True)
        
        # Add Grand Total Row to Summary
        total_row = pd.DataFrame([{
            'Category': 'GRAND TOTAL',
            'Taxable': summary['Taxable'].sum(),
            'IGST': summary['IGST'].sum(),
            'CGST': summary['CGST'].sum(),
            'SGST': summary['SGST'].sum()
        }])
        summary = pd.concat([summary, total_row], ignore_index=True)

        # Rounding
        for col in ['Taxable', 'IGST', 'CGST', 'SGST']:
            summary[col] = summary[col].round(2)

        # --- 6. EXCEL GENERATION WITH SUBTOTALS & FILTERS ---
        if custom_filename and str(custom_filename).strip():
            clean_name = re.sub(r'[\\/*?:"<>|]', '-', str(custom_filename).strip())
            output_filename = f"{clean_name} GSTR1.xlsx"
        else:
            output_filename = "GSTR1_Report.xlsx"

        output_full_path = os.path.join(output_folder, output_filename)

        # We use Pandas to write data, then openpyxl to add filters/styles
        with pd.ExcelWriter(output_full_path, engine='openpyxl') as writer:
            # Write Main Data
            final_df.to_excel(writer, sheet_name='GSTR1 Data', index=False)
            
            # Add a Total Row at the bottom of detailed data
            worksheet = writer.sheets['GSTR1 Data']
            last_row = len(final_df) + 2 # +1 for header, +1 for next row
            
            # Write Summary 4 rows below the data (Single Sheet Request)
            summary_start_row = last_row + 4
            summary.to_excel(writer, sheet_name='GSTR1 Data', index=False, startrow=summary_start_row)

        # --- POST-PROCESSING (Formatting) ---
        import openpyxl
        wb = openpyxl.load_workbook(output_full_path)
        ws = wb['GSTR1 Data']

        # 1. Add AutoFilter to the main table headers
        ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{len(final_df) + 1}"

        # 2. Add Bold Total Row for Data
        ws.cell(row=last_row, column=1).value = "GRAND TOTAL"
        ws.cell(row=last_row, column=1).font = openpyxl.styles.Font(bold=True)
        
        # Sum columns K, L, M, N (Taxable, IGST, CGST, SGST) - assuming standard layout
        # Dynamic mapping based on final_df columns
        for col_name in ['Taxable Amt.', 'IGST', 'CGST', 'SGST']:
            if col_name in final_df.columns:
                col_idx = final_df.columns.get_loc(col_name) + 1
                # Excel Formula for Subtotal (9 = SUM, supports filters)
                col_letter = get_column_letter(col_idx)
                ws.cell(row=last_row, column=col_idx).value = f"=SUBTOTAL(9, {col_letter}2:{col_letter}{len(final_df)+1})"
                ws.cell(row=last_row, column=col_idx).font = openpyxl.styles.Font(bold=True)

        wb.save(output_full_path)

        # Cleanup
        for fp in file_paths:
            if os.path.exists(fp): os.remove(fp)

        return {
            "success": True,
            "message": "GSTR-1 Report Generated.",
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename,
            "summary_data": summary.to_dict(orient='records')
        }

    except Exception as e:
        return {"success": False, "error": str(e)}