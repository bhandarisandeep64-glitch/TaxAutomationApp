import pandas as pd
import os
import datetime

def process_tds_odoo(file_paths, output_folder, custom_filename=None):
    """
    Processes Multiple Odoo files.
    - Merges all uploaded files.
    - Appends Summary to the SAME sheet.
    """
    try:
        all_data = []
        
        # 1. Read All Files
        for fp in file_paths:
            try:
                if fp.endswith('.csv'):
                    df_temp = pd.read_csv(fp)
                else:
                    df_temp = pd.read_excel(fp)
                all_data.append(df_temp)
            except Exception as e:
                return {"success": False, "error": f"Failed to read file {os.path.basename(fp)}: {str(e)}"}

        if not all_data:
            return {"success": False, "error": "No valid data found in uploaded files."}

        # 2. Merge DataFrames
        df = pd.concat(all_data, ignore_index=True)

        if 'Credit' in df.columns:
            df.rename(columns={'Credit': 'TDS'}, inplace=True)
        
        # --- LOGIC BLOCK ---
        df['Rates'] = df['Label'].str.extract(r'(\d*\.?\d+)%').astype(float)
        df['Section'] = df['Label'].apply(lambda x: x.split('% ')[1] if isinstance(x, str) and '% ' in x else 'N/A')

        def get_pan_type(pan):
            pan_str = str(pan)
            return 'Co.' if len(pan_str) >= 4 and pan_str[3].upper() == 'C' else 'Non Co.'

        df['Co./Non Co.'] = df['PAN No.'].apply(get_pan_type)
        df['Checking for rates'] = df['Taxable Amt.'] * (df['Rates'] / 100)
        df['Difference'] = df['TDS'] - df['Checking for rates']
        df['Remarks'] = df['Difference'].apply(lambda x: 'match' if abs(x) < 1 else 'mismatch')
        
        rename_map = {
            'Partner': 'Vendor', 'PAN No.': 'Permanent Account Number (PAN)', 'Number': 'Transaction#',
            'Journal': 'Transaction Type', 'Taxable Amt.': 'Total', 'TDS': 'Tax Deducted at Source',
            'Rates': 'Rate at which deducted'
        }
        df.rename(columns=rename_map, inplace=True)

        df['Total After TDS Deduction'] = df['Total'] - df['Tax Deducted at Source']
        
        df['Date_dt'] = pd.to_datetime(df['Date'], errors='coerce')
        valid_dates = df['Date_dt'].dropna()
        
        report_month_period = None
        if not valid_dates.empty:
             modes = valid_dates.dt.to_period('M').mode()
             if not modes.empty:
                report_month_period = modes[0]

        if report_month_period:
            df['Months Difference'] = df['Date_dt'].dt.to_period('M').apply(
                lambda x: (report_month_period - x).n if pd.notna(x) else 0)
            df['Interest'] = df.apply(
                lambda row: row['Tax Deducted at Source'] * 0.015 * (row['Months Difference'] + 1) 
                if row['Months Difference'] > 0 else 0, axis=1).round(0)
        else:
            df['Interest'] = 0

        df['Date'] = df['Date_dt'].dt.strftime('%Y-%m-%d').fillna('')

        for col in ['Challan No.', 'Challan Date', 'BSR Code', 'Challan Amount', 'Paid Interest', 'Challan Total Amount']:
            df[col] = ''

        final_column_order = [
            'Vendor', 'Permanent Account Number (PAN)', 'Date', 'Reference', 'Transaction#',
            'Account', 'Transaction Type', 'Label', 'Total', 'Tax Deducted at Source',
            'Checking for rates', 'Difference', 'Remarks', 'Interest', 'Rate at which deducted',
            'Section', 'Co./Non Co.',
            'Challan No.', 'Challan Date', 'BSR Code', 'Challan Amount', 'Paid Interest', 'Challan Total Amount'
        ]
        
        existing_cols = [c for c in final_column_order if c in df.columns]
        detailed_df = df[existing_cols].copy()
        
        summary_df = pd.DataFrame()
        if 'Section' in detailed_df.columns and 'Co./Non Co.' in detailed_df.columns:
            summary_df = pd.pivot_table(detailed_df, index=['Section', 'Co./Non Co.'], 
                                    values=['Tax Deducted at Source', 'Interest'], 
                                    aggfunc='sum', margins=True, margins_name='Total')
            summary_df.reset_index(inplace=True)
            summary_df.rename(columns={'Tax Deducted at Source': 'Total Tax Deducted', 'Interest': 'Total Interest'}, inplace=True)
            summary_df['Total Tax Deducted'] = summary_df['Total Tax Deducted'].round(0)
            summary_df['Total Interest'] = summary_df['Total Interest'].round(0)

        # --- SAVING LOGIC ---
        if custom_filename and custom_filename.strip():
            clean_name = custom_filename.strip()
            output_filename = f"{clean_name} TDS Working.xlsx"
        else:
            output_filename = f"Processed_TDS_Working.xlsx"

        output_full_path = os.path.join(output_folder, output_filename)

        with pd.ExcelWriter(output_full_path, engine='openpyxl') as writer:
            detailed_df.to_excel(writer, sheet_name='TDS Working', index=False)
            if not summary_df.empty:
                start_row = len(detailed_df) + 4
                summary_df.to_excel(writer, sheet_name='TDS Working', index=False, startrow=start_row)

        # Clean up input files
        for fp in file_paths:
            if os.path.exists(fp):
                os.remove(fp)

        return {
            "success": True, 
            "message": f"Processed {len(file_paths)} file(s) successfully.",
            "download_url": f"/api/download/{output_filename}",
            "summary_data": summary_df.to_dict(orient='records') if not summary_df.empty else []
        }

    except Exception as e:
        return {"success": False, "error": str(e)}