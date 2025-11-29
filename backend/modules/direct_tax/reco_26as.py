import pandas as pd
import os
import xlsxwriter
from io import BytesIO

def parse_traces_text_file(file_path):
    """
    Parses the hierarchical 26AS text file format.
    """
    try:
        # Read file from disk
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        lines = content.splitlines()

        # Data Containers
        general_info = []
        tds_data = [] # For Part I
        
        # State Variables
        current_section = None
        current_deductor = {} # To hold parent row info (Name, TAN)

        # --- Loop through lines ---
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split('^')]

            # 1. Detect Section Headers
            if "Annual Tax Statement" in line:
                current_section = "HEADER"
                continue
            elif "PART-I" in line and "Details of Tax Deducted at Source" in line:
                current_section = "PART_I"
                continue
            # (Add other parts here if needed in future)
            
            # 2. Process General Info (Header Data)
            if current_section == "HEADER":
                if len(parts) > 5 and len(parts[1]) == 10: 
                    info_dict = {
                        'File Date': parts[0],
                        'PAN': parts[1],
                        'Status': parts[2],
                        'Financial Year': parts[3],
                        'Assessment Year': parts[4],
                        'Name': parts[5],
                        'Address': ", ".join(parts[6:])
                    }
                    general_info.append(info_dict)
            
            # 3. Process Part I (TDS)
            elif current_section == "PART_I":
                if line.startswith('^Sr. No.') or line.startswith('Sr. No.^Name of Deductor'):
                    continue
                
                # Transaction Row
                if line.startswith('^') and len(parts) > 3 and parts[1].isdigit():
                    row = {
                        'Deductor Name': current_deductor.get('name', ''),
                        'Deductor TAN': current_deductor.get('tan', ''),
                        'Section': parts[2],
                        'Transaction Date': parts[3],
                        'Status': parts[4],
                        'Booking Date': parts[5],
                        'Remarks': parts[6],
                        'Amount Paid/Credited': float(parts[7]) if parts[7].replace('.','').isdigit() else 0,
                        'Tax Deducted': float(parts[8]) if parts[8].replace('.','').isdigit() else 0,
                        'TDS Deposited': float(parts[9]) if parts[9].replace('.','').isdigit() else 0
                    }
                    tds_data.append(row)
                    
                # Deductor Row (Parent)
                elif parts[0].isdigit() and not line.startswith('^'):
                    current_deductor = {
                        'name': parts[1],
                        'tan': parts[2]
                    }

        # Convert to DataFrames
        dfs = {}
        if general_info:
            dfs['General Info'] = pd.DataFrame(general_info)
        if tds_data:
            # RENAMED HERE: This key becomes the Excel Sheet Name
            dfs['As per 26AS'] = pd.DataFrame(tds_data)
        
        return dfs

    except Exception as e:
        print(f"Error parsing text file: {e}")
        return {}

def save_to_excel(data_frames, output_path):
    """
    Saves parsed data to Excel with advanced formatting.
    """
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Formats
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
        currency_format = workbook.add_format({'num_format': '#,##0.00'})
        bold_currency_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})
        bold_format = workbook.add_format({'bold': True})
        diff_format = workbook.add_format({'num_format': '#,##0.00', 'font_color': 'red'})

        # --- 1. Standard Sheets (General Info, As per 26AS, etc.) ---
        for sheet_name, df in data_frames.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
            worksheet = writer.sheets[safe_name]
            
            (max_row, max_col) = df.shape
            if max_row > 0:
                worksheet.autofilter(0, 0, max_row, max_col - 1)
                
            # Formatting
            for i, col in enumerate(df.columns):
                worksheet.write(0, i, col, header_format)
                if 'Amount' in col or 'Tax' in col or 'Deposited' in col:
                    worksheet.set_column(i, i, 18, currency_format)
                    # Add Subtotal at bottom
                    if sheet_name != 'General Info':
                        col_letter = chr(ord('A') + i)
                        formula = f'=SUBTOTAL(9, {col_letter}2:{col_letter}{max_row + 1})'
                        worksheet.write(max_row + 1, i, formula, bold_currency_format)
                elif 'Date' in col:
                    worksheet.set_column(i, i, 15)
                else:
                    worksheet.set_column(i, i, 20)
            
            if sheet_name != 'General Info':
                 worksheet.write(max_row + 1, 0, 'TOTAL', bold_format)


        # --- 2. "Individual" Reco Sheet ---
        # UPDATED REFERENCE to match new key
        if 'As per 26AS' in data_frames:
            df_tds = data_frames['As per 26AS']
            
            # Group by Deductor and sum TDS Deposited
            reco_df = df_tds.groupby('Deductor Name', as_index=False)['TDS Deposited'].sum()
            reco_df = reco_df.rename(columns={'TDS Deposited': 'As per 26AS'})
            
            # Add placeholder columns
            reco_df['As per Books'] = ""
            reco_df['Difference'] = ""
            reco_df['Remarks'] = ""
            
            # Reorder
            reco_df = reco_df[['Deductor Name', 'As per 26AS', 'As per Books', 'Difference', 'Remarks']]
            
            sheet_name = "Individual"
            reco_df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            
            (max_row, max_col) = reco_df.shape
            
            # Apply Headers
            for i, col in enumerate(reco_df.columns):
                worksheet.write(0, i, col, header_format)
                worksheet.set_column(i, i, 20)
            
            # Apply Formulas for Difference Column (Column D, Index 3)
            # Formula: =AsPer26AS (B) - AsPerBooks (C)
            for row_num in range(1, max_row + 1):
                # Excel rows are 1-based. Data starts at row 2 (index 1).
                excel_row = row_num + 1
                formula = f'=B{excel_row}-C{excel_row}'
                worksheet.write_formula(row_num, 3, formula, diff_format)
                
            # Formatting for money columns
            worksheet.set_column(1, 3, 18, currency_format)
            
            # Add Total Row for Individual Sheet
            worksheet.write(max_row + 1, 0, "TOTAL", bold_format)
            worksheet.write_formula(max_row + 1, 1, f'=SUM(B2:B{max_row+1})', bold_currency_format)
            worksheet.write_formula(max_row + 1, 2, f'=SUM(C2:C{max_row+1})', bold_currency_format)
            worksheet.write_formula(max_row + 1, 3, f'=SUM(D2:D{max_row+1})', bold_currency_format)


        # --- 3. "As per Books" Sheet (Blank Template) ---
        books_df = pd.DataFrame(columns=["Date", "Deductor Name", "Invoice No", "Taxable Amount", "TDS Amount", "Remarks"])
        books_df.to_excel(writer, sheet_name="As per Books", index=False)
        worksheet = writer.sheets["As per Books"]
        for i, col in enumerate(books_df.columns):
            worksheet.write(0, i, col, header_format)
            worksheet.set_column(i, i, 18)

def process_26as_reco(portal_file_path, book_file_path, output_folder, custom_filename=None):
    """
    Main Wrapper: 
    1. Reads the 26AS Text File (Portal File).
    2. Ignores the Book File for now (since the user code focuses on creating a template).
    3. Generates the Excel Report.
    """
    try:
        # 1. Parse Portal File (Text/HTML)
        if not portal_file_path:
             return {"success": False, "error": "No 26AS file provided."}

        data_frames = parse_traces_text_file(portal_file_path)

        if not data_frames:
             return {"success": False, "error": "Could not parse 26AS file. Ensure it is the correct text format."}

        # 2. Save
        if custom_filename and str(custom_filename).strip():
            output_filename = f"{str(custom_filename).strip()}.xlsx"
        else:
            output_filename = "26AS_Reco_Ready.xlsx"
            
        output_full_path = os.path.join(output_folder, output_filename)
        save_to_excel(data_frames, output_full_path)

        # Generate simple summary for frontend
        summary_data = []
        # UPDATED REFERENCE to match new key
        if 'As per 26AS' in data_frames:
             total_tds = data_frames['As per 26AS']['TDS Deposited'].sum()
             summary_data.append({'Category': 'Total TDS Deposited', 'Amount': total_tds})

        return {
            "success": True,
            "message": "26AS Parsed Successfully.",
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename,
            "summary_data": summary_data
        }

    except Exception as e:
        return {"success": False, "error": str(e)}