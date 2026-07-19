import pandas as pd
import os
from modules.excel_styles import style_header_row, style_data_rows, autofit_columns
from modules.direct_tax.tds_section_mapping import lookup_new_section


def process_tds_odoo(file_paths, output_folder, custom_filename=None):
    """
    Processes Multiple Odoo files.
    - Merges all uploaded files.
    - Appends Summary to the SAME sheet.

    Unlike Zoho (one file = one section, from the filename), Odoo's ledger
    export carries BOTH the rate and the old section as text inside a single
    "Label" column per row (e.g. "2% 194C") -- so a single upload can mix
    multiple sections, and Old Section/rate are derived per row rather than
    per file. New Section/Section Code use the same Income Tax Act 2025
    mapping as tds_zoho.py (shared via tds_section_mapping.py).
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
        df['Old Section'] = df['Label'].apply(lambda x: x.split('% ')[1] if isinstance(x, str) and '% ' in x else 'N/A')

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

        # New Section / Section Code (Income Tax Act 2025 mapping)
        new_sections, section_codes = [], []
        for _, row in df.iterrows():
            new_sec, code = lookup_new_section(row['Old Section'], row['Rate at which deducted'])
            new_sections.append(new_sec)
            section_codes.append(code)
        df['New Section'] = new_sections
        df['Section Code'] = section_codes

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

        # Reorder (blank Challan placeholder columns removed -- handled by
        # the separate TDS Challan Mapper tool instead)
        final_column_order = [
            'Vendor', 'Permanent Account Number (PAN)', 'Date', 'Reference', 'Transaction#',
            'Account', 'Transaction Type', 'Label', 'Total', 'Tax Deducted at Source',
            'Checking for rates', 'Difference', 'Remarks', 'Interest', 'Rate at which deducted',
            'Old Section', 'New Section', 'Section Code', 'Co./Non Co.',
        ]

        existing_cols = [c for c in final_column_order if c in df.columns]
        detailed_df = df[existing_cols].copy()

        # Section Summary
        summary_df = pd.DataFrame()
        if {'Old Section', 'New Section', 'Section Code', 'Co./Non Co.'}.issubset(detailed_df.columns):
            summary_df = pd.pivot_table(detailed_df, index=['Old Section', 'New Section', 'Section Code', 'Co./Non Co.'],
                                    values=['Tax Deducted at Source', 'Interest'],
                                    aggfunc='sum', margins=True, margins_name='Total')
            summary_df.reset_index(inplace=True)
            summary_df.rename(columns={'Tax Deducted at Source': 'Total Tax Deducted', 'Interest': 'Total Interest'}, inplace=True)
            summary_df['Total Tax Deducted'] = summary_df['Total Tax Deducted'].round(0)
            summary_df['Total Interest'] = summary_df['Total Interest'].round(0)

        # Vendor Summary
        if 'Vendor' in detailed_df.columns:
            vendor_summary_df = detailed_df.groupby('Vendor').agg(
                **{'Total Taxable Value': ('Total', 'sum'), 'Total TDS': ('Tax Deducted at Source', 'sum')}
            ).reset_index().rename(columns={'Vendor': 'Vendor Name'})
            vendor_summary_df = vendor_summary_df.sort_values('Vendor Name').reset_index(drop=True)
        else:
            vendor_summary_df = pd.DataFrame(columns=['Vendor Name', 'Total Taxable Value', 'Total TDS'])

        # --- SAVING LOGIC ---
        if custom_filename and custom_filename.strip():
            clean_name = custom_filename.strip()
            output_filename = f"{clean_name} TDS Working.xlsx"
        else:
            output_filename = f"Processed_TDS_Working.xlsx"

        output_full_path = os.path.join(output_folder, output_filename)

        with pd.ExcelWriter(output_full_path, engine='openpyxl') as writer:
            detailed_df.to_excel(writer, sheet_name='TDS Working', index=False)
            summary_start_row = len(detailed_df) + 4
            if not summary_df.empty:
                summary_df.to_excel(writer, sheet_name='TDS Working', index=False, startrow=summary_start_row)
            vendor_summary_df.to_excel(writer, sheet_name='Vendor Summary', index=False)

        # --- POST-PROCESSING (formatting) ---
        import openpyxl
        wb = openpyxl.load_workbook(output_full_path)
        ws = wb['TDS Working']

        ws.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(ws.max_column)}{len(detailed_df) + 1}"
        ws.freeze_panes = "A2"
        style_header_row(ws, len(detailed_df.columns))
        autofit_columns(ws, detailed_df)

        numeric_cols = {detailed_df.columns.get_loc(c) + 1 for c in
                         ['Total', 'Tax Deducted at Source', 'Total After TDS Deduction', 'Checking for rates',
                          'Difference', 'Interest'] if c in detailed_df.columns}
        style_data_rows(ws, 2, len(detailed_df) + 1, 1, len(detailed_df.columns), numeric_cols)

        if not summary_df.empty:
            style_header_row(ws, len(summary_df.columns), row=summary_start_row + 1)
            summary_numeric_cols = {summary_df.columns.get_loc(c) + 1 for c in
                                     ['Total Tax Deducted', 'Total Interest'] if c in summary_df.columns}
            style_data_rows(ws, summary_start_row + 2, summary_start_row + 1 + len(summary_df),
                             1, len(summary_df.columns), summary_numeric_cols)

        vendor_ws = wb['Vendor Summary']
        if not vendor_summary_df.empty:
            vendor_ws.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(vendor_ws.max_column)}{len(vendor_summary_df) + 1}"
        vendor_ws.freeze_panes = "A2"
        style_header_row(vendor_ws, len(vendor_summary_df.columns))
        autofit_columns(vendor_ws, vendor_summary_df)
        vendor_numeric_cols = {vendor_summary_df.columns.get_loc(c) + 1 for c in
                                ['Total Taxable Value', 'Total TDS'] if c in vendor_summary_df.columns}
        style_data_rows(vendor_ws, 2, len(vendor_summary_df) + 1, 1, len(vendor_summary_df.columns), vendor_numeric_cols)

        wb.save(output_full_path)

        # Clean up input files
        for fp in file_paths:
            if os.path.exists(fp):
                os.remove(fp)

        return {
            "success": True,
            "message": f"Processed {len(file_paths)} file(s) successfully.",
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename,
            "summary_data": summary_df.to_dict(orient='records') if not summary_df.empty else []
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
