import pandas as pd
import os
import re

def get_analysis_dataframe(file_path):
    """
    Reads Excel/CSV for ANALYSIS only.
    Strictly removes summaries and empty rows to ensure accurate grouping.
    """
    if str(file_path).endswith('.csv'):
        df = pd.read_csv(file_path, skip_blank_lines=True)
    else:
        df = pd.read_excel(file_path)

    # 1. Drop completely empty rows
    df.dropna(how='all', inplace=True)

    # 2. Locate and cut off the Old Summary
    col_a = df.iloc[:, 0].astype(str).str.lower().str.strip()
    col_b = df.iloc[:, 1].astype(str).str.lower().str.strip() if df.shape[1] > 1 else col_a

    summary_keywords = ['summary report', 'total tax deducted', 'financial summary', 'section']
    
    # We search from the bottom up or look for specific headers to cut
    cutoff_index = None
    for keyword in summary_keywords:
        # Look for keyword in column A or B
        matches = df.index[col_a.str.contains(keyword, na=False) | col_b.str.contains(keyword, na=False)].tolist()
        # If found, picking the first occurrence might be dangerous if "Section" is the main header.
        # We assume the summary is at the bottom. 
        # A safe bet for "Section" keyword is checking if it appears *after* data starts.
        if matches:
            # Heuristic: If "Section" appears again far down, it's the summary
            if len(matches) > 1: 
                cutoff_index = matches[-1] # Last occurrence
                break
            elif keyword != 'section': # For specific summary words, take first match
                cutoff_index = matches[0]
                break
    
    if cutoff_index is not None:
        # If cutoff is very close to 0 (like the main header), ignore it.
        if cutoff_index > 5: 
            df = df.iloc[:cutoff_index].copy()

    # 3. Filter out invalid transaction rows
    if 'Transaction#' in df.columns:
        df = df[df['Transaction#'].notna()]
        invalid_identifiers = ['nan', 'section', 'transaction#', 'summary']
        df = df[~df['Transaction#'].astype(str).str.lower().str.strip().isin(invalid_identifiers)]

    return df

def analyze_for_challan(file_path):
    """
    Step 1: Analysis (Uses strict cleaning to find groups).
    """
    try:
        df = get_analysis_dataframe(file_path)
        
        if 'Section' not in df.columns or 'Co./Non Co.' not in df.columns:
             return {"success": False, "error": "Columns 'Section' or 'Co./Non Co.' missing."}

        df['Tax Deducted at Source'] = pd.to_numeric(df['Tax Deducted at Source'], errors='coerce').fillna(0)
        df['Section'] = df['Section'].astype(str).str.strip()
        df['Co./Non Co.'] = df['Co./Non Co.'].astype(str).str.strip().fillna('N/A')

        # Remove nan/empty groups
        df = df[~df['Section'].str.lower().isin(['nan', 'none', ''])]

        summary = df.groupby(['Section', 'Co./Non Co.']).agg(
            Total_Tax_Pending=('Tax Deducted at Source', 'sum')
        ).reset_index()
        
        summary = summary[summary['Total_Tax_Pending'] > 0]
        
        groups = summary.to_dict(orient='records')
        
        return {
            "success": True,
            "groups": groups
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

def update_with_manual_challan(file_path, user_inputs, output_folder, custom_filename=None, original_filename=None):
    """
    Step 2: Update.
    - Reads the WHOLE file (preserving original summary).
    - Updates only valid transaction rows.
    - Saves without appending anything new.
    """
    try:
        # Read everything (don't strip summary)
        if str(file_path).endswith('.csv'):
            df = pd.read_csv(file_path, skip_blank_lines=False)
        else:
            df = pd.read_excel(file_path)
        
        # Ensure columns exist
        new_cols = ['Challan No.', 'Challan Date', 'BSR Code', 'Challan Amount', 'Paid Interest', 'Challan Total Amount']
        for col in new_cols:
            if col not in df.columns:
                df[col] = ''
            else:
                df[col] = df[col].astype(str).replace('nan', '')

        # Iterate rows
        for index, row in df.iterrows():
            # SAFELY check if this is a target row.
            # We only update rows that have a valid 'Section' and 'Co./Non Co.' 
            # AND ideally a valid 'Transaction#' to distinguish them from summary rows.
            
            section_val = row.get('Section')
            status_val = row.get('Co./Non Co.')
            
            # Skip if empty or nan
            if pd.isna(section_val) or pd.isna(status_val):
                continue
                
            section = str(section_val).strip()
            status = str(status_val).strip()
            
            # Skip if it looks like a header or summary line
            if section.lower() in ['section', 'nan', 'summary report']:
                continue

            group_key = f"{section}|{status}"
            
            if group_key in user_inputs:
                details = user_inputs[group_key]
                if details.get('challan_no'): df.at[index, 'Challan No.'] = details['challan_no']
                if details.get('date'): df.at[index, 'Challan Date'] = details['date']
                if details.get('bsr'): df.at[index, 'BSR Code'] = details['bsr']
                if details.get('amount'): df.at[index, 'Challan Amount'] = float(details['amount'])
                if details.get('interest'): df.at[index, 'Paid Interest'] = float(details['interest'])
                if details.get('total'): df.at[index, 'Challan Total Amount'] = float(details['total'])

        # --- NAMING LOGIC ---
        if custom_filename and str(custom_filename).strip():
            clean_name = re.sub(r'[\\/*?:"<>|]', '-', str(custom_filename).strip())
            output_filename = f"{clean_name}.xlsx" if not clean_name.endswith('.xlsx') else clean_name
        elif original_filename:
            base = os.path.splitext(original_filename)[0]
            base = base.replace("TEMP_CHALLAN_", "").replace("TARGET_", "")
            output_filename = f"{base}_Mapped.xlsx"
        else:
            output_filename = "Challan_Updated.xlsx"

        output_full_path = os.path.join(output_folder, output_filename)

        # Save WITHOUT appending new summary
        with pd.ExcelWriter(output_full_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='TDS Working', index=False)

        return {
            "success": True,
            "message": "Challan details updated successfully.",
            "download_url": f"/api/download/{output_filename}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}