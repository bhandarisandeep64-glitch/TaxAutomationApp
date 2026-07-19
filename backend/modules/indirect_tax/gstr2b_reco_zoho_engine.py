import pandas as pd
import re
import logging
from io import BytesIO
from difflib import SequenceMatcher
import numpy as np
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

from modules.indirect_tax.gstr_period_balance import get_opening_itc, save_closing_itc

# ==========================================
#  CONFIGURATION & SETTINGS
# ==========================================

PORTAL_SHEETS_TO_IGNORE = ["Read me"]

# These carry ITC-eligibility info rather than a distinct set of transactions.
# Kept and shown in the output workbook for reference, but deliberately NOT
# merged into the reconciliation match logic -- their rows likely overlap
# with invoices already listed in B2B/ECO/etc, and reconciling them too
# would double-count those invoices.
ITC_REFERENCE_SHEETS = {"ITC Available", "ITC not available", "ITC Reversal", "ITC Rejected"}

ZOHO_SHEETS_TO_IGNORE = [
    'imp', 'imp_services', 'nil,exempt,non-gst,composition', 
    'hsn', 'advance paid', 'advance adjusted', 'docs'
]

RENAME_MAP = {
    'Invoice number': 'Invoice Number', 'Note number': 'Invoice Number', 'Bill of entry number': 'Invoice Number',
    'Invoice Value (₹)': 'Invoice Value', 'Taxable Value (₹)': 'Taxable Value',
    'Integrated Tax (₹)': 'IGST Tax Amount', 'Central Tax (₹)': 'CGST Tax Amount', 'State/UT Tax (₹)': 'SGST Tax Amount',
    'Cess Amount (₹)': 'Cess Amount', 'Trade/Legal name': 'Vendor Name', 'GSTIN of supplier': 'GSTIN',
    'Invoice Date': 'Invoice date', 'Place of supply': 'Place Of Supply',
    'Supply Attract Reverse Charge': 'Reverse Charge', 'Rate (%)': 'Rate'
}

# ==========================================
#  UTILITIES
# ==========================================

def clean_inv_str(s):
    """Standardizes invoice numbers: lowercase, removes special chars."""
    if pd.isna(s): return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(s).lower())

def robust_safe_float(val):
    if pd.isna(val) or val == '': return 0.0
    try:
        val_str = str(val).replace(',', '').strip()
        return float(val_str)
    except (ValueError, TypeError):
        return 0.0

def get_itc_deadline(invoice_date):
    """Section 16(4): ITC on an invoice must be claimed by 30th November
    following the end of the financial year (Apr-Mar) it belongs to. Returns
    None if invoice_date isn't a usable date. This is the statutory ceiling,
    not the earlier "date of filing the annual return" cutoff (that filing
    date isn't available here), so it's a conservative/latest bound."""
    if pd.isna(invoice_date): return None
    year, month = invoice_date.year, invoice_date.month
    fy_end_year = year + 1 if month >= 4 else year
    return pd.Timestamp(year=fy_end_year, month=11, day=30)

def clean_gstin(val):
    if pd.isna(val): return ""
    s = str(val).upper().strip().replace(" ", "").replace("-", "")
    return s[:15] if len(s) >= 15 else s

def clean_date_robust(val):
    if pd.isna(val) or val == '': return None
    try:
        if isinstance(val, pd.Timestamp): return val.normalize()
        return pd.to_datetime(val, dayfirst=True, errors='coerce').normalize()
    except (ValueError, TypeError):
        return None

def get_similarity_score(a, b):
    return SequenceMatcher(None, a, b).ratio()

# ==========================================
#  EXCEL WRITER LOGIC
# ==========================================

def add_formatting(writer, df, sheet_name):
    if df.empty: return
    
    # Safety: Drop duplicate columns before writing to avoid Excel confusion
    df = df.loc[:, ~df.columns.duplicated()]
    
    df.to_excel(writer, sheet_name=sheet_name, index=False)

    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    (num_rows, num_cols) = df.shape

    # Define Formats
    fmt_header = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
    fmt_num = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})
    fmt_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    fmt_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
    fmt_bold = workbook.add_format({'bold': True})

    # Apply Header Formatting
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, fmt_header)
        worksheet.set_column(col_num, col_num, 15)

    # Apply Autofilter
    if num_rows > 0:
        worksheet.autofilter(0, 0, num_rows, num_cols - 1)

    # Add Filter Totals Row
    total_row = num_rows + 1
    worksheet.write(total_row, 0, 'Filter Total', fmt_bold)

    # Add Subtotals for Financial Columns
    keywords_to_sum = ['taxable', 'igst', 'cgst', 'sgst', 'cess', 'total', 'difference', 'val', 'rate', 'integrated', 'central', 'state']
    
    for col_idx, col_name in enumerate(df.columns):
        c_name = str(col_name).lower()
        if any(k in c_name for k in keywords_to_sum) and 'number' not in c_name and 'date' not in c_name and 'id' not in c_name:
             col_letter = xl_col_to_name(col_idx)
             worksheet.write_formula(total_row, col_idx, f'=SUBTOTAL(9,{col_letter}2:{col_letter}{total_row})', fmt_num)

    # Apply Conditional Formatting
    if 'Remarks' in df.columns:
        rem_idx = df.columns.get_loc('Remarks')
        rem_letter = xl_col_to_name(rem_idx)
        rng = f"{rem_letter}2:{rem_letter}{total_row}"
        
        worksheet.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': 'Mismatch', 'format': fmt_red})
        worksheet.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': 'Not', 'format': fmt_red})
        worksheet.conditional_format(rng, {'type': 'text', 'criteria': 'containing', 'value': 'Match', 'format': fmt_green})

# ==========================================
#  DATA CLEANERS
# ==========================================

def _extract_header_dynamically(df_raw):
    header_idx = -1
    search_terms = ['gstin of supplier', 'invoice number', 'note number', 'bill of entry number']
    
    for i in range(min(10, len(df_raw))):
        row_str = " ".join(df_raw.iloc[i].astype(str).fillna('').values).lower()
        if any(term in row_str for term in search_terms):
            header_idx = i; break
    
    if header_idx == -1: return pd.DataFrame()

    df_data = df_raw.iloc[header_idx+1:].reset_index(drop=True)
    row1 = df_raw.iloc[header_idx].astype(str).replace('nan', '').str.strip().tolist()
    
    if header_idx + 1 < len(df_raw):
        row2 = df_raw.iloc[header_idx+1].astype(str).replace('nan', '').str.strip().tolist()
        if any('tax' in val.lower() for val in row2):
            df_data = df_raw.iloc[header_idx+2:].reset_index(drop=True)
            new_cols = [c2 if c2 else c1 if c1 else "Unknown" for c1, c2 in zip(row1, row2)]
            df_data.columns = new_cols
        else:
            df_data.columns = row1
    else:
        df_data.columns = row1

    # Rename Columns
    final_cols = []
    for col in df_data.columns:
        mapped = col
        for k, v in RENAME_MAP.items():
            if k.lower() == str(col).lower().strip(): mapped = v; break
        final_cols.append(mapped)
    df_data.columns = final_cols

    # Fix Numerics
    numeric_cols = ['Taxable Value', 'Invoice Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount']
    for col in numeric_cols:
        if col in df_data.columns: 
            df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)

    # Drop Unwanted
    unwanted = ['period', 'filing date', 'applicable %', 'source', 'irn']
    cols_to_drop = [c for c in df_data.columns if any(kw in str(c).lower() for kw in unwanted)]
    
    if cols_to_drop: 
        df_data.drop(columns=cols_to_drop, inplace=True, errors='ignore')

    # Drop Empty Numeric Columns
    for col in numeric_cols:
        if col in df_data.columns and df_data[col].abs().max() == 0: 
            df_data.drop(columns=[col], inplace=True)

    return df_data.loc[:, ~df_data.columns.duplicated()]

def clean_portal_data(file_content):
    xls = pd.ExcelFile(file_content)
    cleaned_sheets = {}
    reference_sheets = {}
    rcm_frames = []

    conditional_delete = {
        "B2B": 7, "B2B-CDNR": 7, "ECO": 7, "ISD": 7, "IMPG": 7, "IMPGSEZ": 7,
        "B2B (ITC Reversal)": 7, "B2B-DNR": 7, "B2BA": 8, "B2B-CDNRA": 8
    }

    for sheet in xls.sheet_names:
        sheet_clean = sheet.strip()
        if sheet_clean in PORTAL_SHEETS_TO_IGNORE: continue

        try:
            df_raw = pd.read_excel(xls, sheet_name=sheet, header=None)

            # Empty Check
            if sheet_clean in conditional_delete:
                target_idx = conditional_delete[sheet_clean] - 1
                if len(df_raw) <= target_idx or df_raw.iloc[target_idx].isna().all(): continue

            df = _extract_header_dynamically(df_raw)
            if df.empty: continue

            if sheet_clean in ITC_REFERENCE_SHEETS:
                reference_sheets[sheet] = df
                continue

            # Separate RCM
            if 'Reverse Charge' in df.columns:
                is_rcm = df['Reverse Charge'].astype(str).str.strip().str.lower().isin(['yes', 'y'])
                if is_rcm.any():
                    rcm_data = df[is_rcm].copy()
                    rcm_data['Source'] = sheet
                    rcm_frames.append(rcm_data)
                    df = df[~is_rcm]

            cleaned_sheets[sheet] = df

        except Exception as e:
            logging.error(f"Error processing Portal sheet {sheet}: {e}")
            continue

    if rcm_frames:
        cleaned_sheets['RCM Combined'] = pd.concat(rcm_frames, ignore_index=True)

    return cleaned_sheets, reference_sheets

def clean_zoho_data(file_content):
    xls = pd.ExcelFile(file_content)
    sheet_map = {}

    for sheet_name in xls.sheet_names:
        sheet_lower = sheet_name.lower().strip()
        if any(x in sheet_lower for x in ZOHO_SHEETS_TO_IGNORE): continue
        
        try:
            # Assume header is on Row 2 (index 1)
            df = pd.read_excel(xls, sheet_name=sheet_name, header=1)
            if df.empty: continue
            
            df = df.dropna(how='all', axis=0) 
            df = df.dropna(how='all', axis=1) 
            if df.empty: continue

            # Strict Check
            if 'Invoice Number' in df.columns:
                if df['Invoice Number'].dropna().empty: continue 
            elif 'Taxable Value' in df.columns:
                if df['Taxable Value'].sum() == 0: continue
            else:
                continue

            df = df.loc[:, ~df.columns.duplicated()]

            # Cut off at last valid invoice
            if 'Invoice Number' in df.columns:
                last_idx = df['Invoice Number'].last_valid_index()
                if last_idx is not None:
                    df = df.iloc[:last_idx + 1]

            sheet_map[sheet_lower] = {'original_name': sheet_name, 'df': df}

        except Exception as e:
            logging.warning(f"Error processing Zoho sheet '{sheet_name}': {e}")
            continue

    # Remove RCM invoices from B2B if they exist in both
    if 'b2b' in sheet_map and 'reverse charge' in sheet_map:
        b2b_df = sheet_map['b2b']['df']
        rcm_df = sheet_map['reverse charge']['df']
        if 'Invoice Number' in b2b_df.columns and 'Invoice Number' in rcm_df.columns:
            rcm_invoices = rcm_df['Invoice Number'].unique()
            clean_b2b = b2b_df[~b2b_df['Invoice Number'].isin(rcm_invoices)].copy()
            if clean_b2b.empty:
                del sheet_map['b2b']
            else:
                sheet_map['b2b']['df'] = clean_b2b

    return sheet_map

# ==========================================
#  RECONCILIATION CORE
# ==========================================

def generate_lookup_maps(dataset):
    candidates = [] 
    for key, val in dataset.items():
        df = val if isinstance(val, pd.DataFrame) else val['df']
        col_inv = 'Invoice Number'
        col_tax = 'Taxable Value'
        if col_inv not in df.columns or col_tax not in df.columns: continue

        col_gstin = next((c for c in df.columns if 'gstin' in c.lower()), None)
        col_date = next((c for c in df.columns if 'date' in c.lower() and 'invoice' in c.lower()), None)
        
        def find_fin_col(keywords):
            return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)

        col_igst = find_fin_col(['igst', 'integrated'])
        col_cgst = find_fin_col(['cgst', 'central'])
        col_sgst = find_fin_col(['sgst', 'state', 'ut'])

        for idx, row in df.iterrows():
            candidates.append({
                'id': f"{key}_{idx}",
                'used': False,
                'clean_inv': clean_inv_str(str(row[col_inv]).strip()),
                'raw_inv': str(row[col_inv]).strip(),
                'tax_val': robust_safe_float(row[col_tax]), 
                'gstin': clean_gstin(row[col_gstin]) if col_gstin else "",
                'date': clean_date_robust(row[col_date]) if col_date else None,
                'igst': robust_safe_float(row[col_igst]) if col_igst else 0.0,
                'cgst': robust_safe_float(row[col_cgst]) if col_cgst else 0.0,
                'sgst': robust_safe_float(row[col_sgst]) if col_sgst else 0.0
            })
    return candidates

def reconcile_dataframe(df, candidates, target_col_name, is_portal_sheet, reco_month_dt=None):
    df[target_col_name] = 0.0
    df['Difference'] = 0.0
    df['Remarks'] = ''
    df['__matched__'] = False
    if is_portal_sheet:
        df['ITC Time-Barred'] = ''
    
    col_inv = 'Invoice Number'
    col_tax = 'Taxable Value'
    col_gstin = next((c for c in df.columns if 'gstin' in c.lower()), None)
    col_date = next((c for c in df.columns if 'date' in c.lower() and 'invoice' in c.lower()), None)
    
    def find_col(keywords):
        return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)
    col_igst = find_col(['igst', 'integrated'])
    col_cgst = find_col(['cgst', 'central'])
    col_sgst = find_col(['sgst', 'state', 'ut'])

    if col_inv not in df.columns: return df
    if col_date: df[col_date] = df[col_date].apply(clean_date_robust)

    exact_match_index = {}
    for i, cand in enumerate(candidates):
        key = (cand['clean_inv'], cand['tax_val'], cand['gstin'])
        if key not in exact_match_index: exact_match_index[key] = []
        exact_match_index[key].append(i)

    def get_row_data(row):
        return {
            'inv': clean_inv_str(row.get(col_inv, '')),
            'tax': robust_safe_float(row.get(col_tax)),
            'gstin': clean_gstin(row.get(col_gstin)) if col_gstin else "",
            'date': row.get(col_date) if col_date else None,
            'igst': robust_safe_float(row.get(col_igst)) if col_igst else 0.0,
            'cgst': robust_safe_float(row.get(col_cgst)) if col_cgst else 0.0,
            'sgst': robust_safe_float(row.get(col_sgst)) if col_sgst else 0.0
        }

    def write_match(idx, r, cand, remark, match_val=None):
        val = match_val if match_val is not None else cand['tax_val']
        
        # Rate Diff Check
        final_remark = remark
        if cand and "Match" in remark and "Rate Diff" not in remark:
            row_tax = r['igst'] + r['cgst'] + r['sgst']
            cand_tax = cand['igst'] + cand['cgst'] + cand['sgst']
            if abs(r['tax'] - val) < 2.0 and abs(row_tax - cand_tax) > 2.0:
                 final_remark = "Mismatch (Rate Diff)"

        df.at[idx, target_col_name] = val
        df.at[idx, 'Difference'] = r['tax'] - val
        df.at[idx, 'Remarks'] = final_remark
        df.at[idx, '__matched__'] = True
        if cand: cand['used'] = True 

    # --- RECONCILIATION PASSES ---
    for idx, row in df.iterrows():
        if df.at[idx, '__matched__']: continue
        r = get_row_data(row)
        if not r['inv']: continue
        key = (r['inv'], r['tax'], r['gstin'])
        if key in exact_match_index:
            for cand_idx in exact_match_index[key]:
                cand = candidates[cand_idx]
                if not cand['used']:
                    write_match(idx, r, cand, "Match")
                    break

    # Pass 1.5: same invoice number + GSTIN, but the amount doesn't match.
    # Every other pass below requires the amount to already be close before
    # it'll even look at the invoice number -- which means a genuine value
    # discrepancy on an otherwise clearly-identified invoice (wrong amount
    # entered on one side) was falling all the way through to "cleanup" and
    # showing up as two disconnected "missing" entries instead of one clear
    # "Mismatch". Invoice number + GSTIN identity is reliable enough that it
    # should win regardless of amount, same as the Odoo reco engine already
    # does.
    for idx, row in df.iterrows():
        if df.at[idx, '__matched__']: continue
        r = get_row_data(row)
        if not r['inv']: continue
        for cand in candidates:
            if cand['used'] or cand['clean_inv'] != r['inv']: continue
            if r['gstin'] and cand['gstin'] and r['gstin'] != cand['gstin']: continue
            write_match(idx, r, cand, "Mismatch")
            break

    for idx, row in df.iterrows():
        if df.at[idx, '__matched__']: continue
        r = get_row_data(row)
        if not r['inv'] or not r['gstin']: continue
        potential_group = [c for c in candidates if not c['used'] and c['clean_inv'] == r['inv'] and c['gstin'] == r['gstin']]
        if len(potential_group) > 1:
            group_sum = sum(c['tax_val'] for c in potential_group)
            if abs(r['tax'] - group_sum) <= 2.0:
                for c in potential_group: c['used'] = True
                write_match(idx, r, None, "Match(Grouped)", group_sum)

    for idx, row in df.iterrows():
        if df.at[idx, '__matched__']: continue
        r = get_row_data(row)
        if not r['inv']: continue
        for cand in candidates:
            if cand['used']: continue
            if abs(r['tax'] - cand['tax_val']) > 2.0: continue
            if r['gstin'] and cand['gstin'] and r['gstin'] != cand['gstin']: continue
            if get_similarity_score(r['inv'], cand['clean_inv']) > 0.85:
                write_match(idx, r, cand, "Match(Typo)"); break
    
    for idx, row in df.iterrows():
        if df.at[idx, '__matched__']: continue
        r = get_row_data(row)
        if not r['inv']: continue
        for cand in candidates:
            if cand['used']: continue
            if abs(r['tax'] - cand['tax_val']) > 2.0: continue
            if abs(r['igst'] - cand['igst']) > 2.0: continue
            if r['gstin'] and cand['gstin'] and r['gstin'] != cand['gstin']: continue
            c_inv, r_inv = cand['clean_inv'], r['inv']
            if (len(r_inv)>3 and len(c_inv)>3) and ((r_inv in c_inv) or (c_inv in r_inv)):
                write_match(idx, r, cand, "Match(Fuzzy)"); break

    for strict in [True, False]:
        remark_lbl = "Match(GSTIN-Strict)" if strict else "Match(GSTIN-Loose)"
        for idx, row in df.iterrows():
            if df.at[idx, '__matched__']: continue
            r = get_row_data(row)
            if not r['gstin']: continue
            for cand in candidates:
                if cand['used'] or cand['gstin'] != r['gstin']: continue
                if abs(r['tax'] - cand['tax_val']) > 2.0: continue
                if strict and (abs(r['igst'] - cand['igst']) > 2.0 or abs(r['cgst'] - cand['cgst']) > 2.0): continue
                write_match(idx, r, cand, remark_lbl); break
    
    unmatched_indices = df[~df['__matched__']].index
    if not unmatched_indices.empty and col_gstin:
        unmatched_df = df.loc[unmatched_indices].copy()
        active_gstins = unmatched_df[col_gstin].dropna().apply(clean_gstin).unique()
        for gstin in active_gstins:
            if not gstin: continue
            df_group_indices = unmatched_df[unmatched_df[col_gstin].apply(clean_gstin) == gstin].index
            my_sum = df.loc[df_group_indices, col_tax].apply(robust_safe_float).sum()
            cand_group = [c for c in candidates if not c['used'] and c['gstin'] == gstin]
            cand_sum = sum(c['tax_val'] for c in cand_group)
            if abs(my_sum - cand_sum) <= 5.0 and my_sum > 0:
                for idx in df_group_indices:
                    df.at[idx, target_col_name] = df.at[idx, col_tax]
                    df.at[idx, 'Difference'] = 0.0
                    df.at[idx, 'Remarks'] = "Match(Consolidated)"; df.at[idx, '__matched__'] = True
                for c in cand_group: c['used'] = True

    # Cleanup
    for idx, row in df.iterrows():
        if not df.at[idx, '__matched__']:
            df.at[idx, 'Difference'] = robust_safe_float(row[col_tax])
            remark = "Not in Books" if is_portal_sheet else "Not on Portal"
            if is_portal_sheet and reco_month_dt and col_date:
                curr_date = clean_date_robust(row[col_date])
                if pd.notnull(curr_date) and curr_date < reco_month_dt: remark = "Previous Period Inv"
            df.at[idx, 'Remarks'] = remark

        # Section 16(4) time-barred ITC check (portal side only)
        if is_portal_sheet and col_date:
            inv_dt = clean_date_robust(row[col_date])
            if pd.notnull(inv_dt):
                deadline = get_itc_deadline(inv_dt)
                if deadline is not None and pd.Timestamp.now().normalize() > deadline:
                    df.at[idx, 'ITC Time-Barred'] = f"YES (was due {deadline.strftime('%d-%b-%Y')})"

    df.drop(columns=['__matched__'], inplace=True, errors='ignore')
    cess_cols = [c for c in df.columns if 'cess' in c.lower()]
    for c_col in cess_cols:
        try:
            if pd.to_numeric(df[c_col], errors='coerce').fillna(0).sum() == 0: df.drop(columns=[c_col], inplace=True)
        except (ValueError, TypeError):
            pass
    return df

# ==========================================
#  DASHBOARD & REPORTS
# ==========================================

def calculate_smart_offset(liability, credit):
    """Implements GST Section 49 Payment Rules."""
    L = liability.copy() 
    C = credit.copy()
    
    paid = {'i_i':0, 'i_c':0, 'i_s':0, 'c_c':0, 'c_i':0, 's_s':0, 's_i':0}
    
    # 1. IGST Credit Usage
    use = min(L['i'], C['i'])
    paid['i_i'] = use; L['i'] -= use; C['i'] -= use
    
    if C['i'] > 0:
        use = min(L['c'], C['i'])
        paid['i_c'] = use; L['c'] -= use; C['i'] -= use
        
    if C['i'] > 0:
        use = min(L['s'], C['i'])
        paid['i_s'] = use; L['s'] -= use; C['i'] -= use

    # 2. CGST Credit Usage
    if L['c'] > 0 and C['c'] > 0:
        use = min(L['c'], C['c'])
        paid['c_c'] = use; L['c'] -= use; C['c'] -= use
    
    if L['i'] > 0 and C['c'] > 0:
        use = min(L['i'], C['c'])
        paid['c_i'] = use; L['i'] -= use; C['c'] -= use

    # 3. SGST Credit Usage
    if L['s'] > 0 and C['s'] > 0:
        use = min(L['s'], C['s'])
        paid['s_s'] = use; L['s'] -= use; C['s'] -= use
        
    if L['i'] > 0 and C['s'] > 0:
        use = min(L['i'], C['s'])
        paid['s_i'] = use; L['i'] -= use; C['s'] -= use

    return paid, L, C

def generate_master_dashboard(writer, portal_dict, books_dict, manual_inputs):
    """Returns the closing ITC balance (bal_credit: {'i','c','s'}) so a
    caller building a full GSTR-3B working paper (see generate_gstr3b_report
    below) can persist it as next period's opening ITC."""
    # Set Defaults if manual_inputs are missing
    if not manual_inputs:
        manual_inputs = {
            'sales': {'igst':0, 'cgst':0, 'sgst':0},
            'opening': {'igst':0, 'cgst':0, 'sgst':0}
        }

    # --- 1. CALCULATE ITC (GSTR-3B TABLE 4) ---
    sums = {
        'all_other': {'i':0.0, 'c':0.0, 's':0.0},
        'rcm_reg': {'i':0.0, 'c':0.0, 's':0.0},
        'rcm_urd': {'i':0.0, 'c':0.0, 's':0.0}
    }
    
    def get_t(row, df):
        def f(k): return next((c for c in df.columns if any(x in c.lower() for x in k)), None)
        ci, cc, cs = f(['igst', 'integrated']), f(['cgst', 'central']), f(['sgst', 'state', 'ut'])
        return robust_safe_float(row.get(ci)), robust_safe_float(row.get(cc)), robust_safe_float(row.get(cs))

    # Portal Loop
    for name, df in portal_dict.items():
        col_rcm = next((c for c in df.columns if 'reverse' in c.lower()), None)
        is_cn = 'cdnr' in name.lower() or 'credit' in name.lower()
        mult = -1 if is_cn else 1
        for _, r in df.iterrows():
            if is_cn and "Not in Books" in str(r.get('Remarks', '')): continue
            i, c, s = get_t(r, df)
            if str(r.get(col_rcm, '')).lower() in ['y', 'yes']:
                sums['rcm_reg']['i'] += i*mult; sums['rcm_reg']['c'] += c*mult; sums['rcm_reg']['s'] += s*mult
            else:
                sums['all_other']['i'] += i*mult; sums['all_other']['c'] += c*mult; sums['all_other']['s'] += s*mult

    # Books Loop
    for name, data in books_dict.items():
        if any(x in name.lower() for x in ['b2bur', 'unregistered', 'urd']):
            df = data['df']
            mult = -1 if 'credit' in name.lower() else 1
            for _, r in df.iterrows():
                i, c, s = get_t(r, df)
                sums['rcm_urd']['i'] += i*mult; sums['rcm_urd']['c'] += c*mult; sums['rcm_urd']['s'] += s*mult

    # RCM & Net ITC
    tot_rcm = {k: sums['rcm_reg'][k] + sums['rcm_urd'][k] for k in ['i','c','s']}
    net_itc = {k: tot_rcm[k] + sums['all_other'][k] for k in ['i','c','s']}

    # --- 2. CALCULATE PAYMENT (SMART OFFSET) ---
    sales = manual_inputs.get('sales', {'igst':0, 'cgst':0, 'sgst':0})
    op = manual_inputs.get('opening', {'igst':0, 'cgst':0, 'sgst':0})
    
    L_fwd = {'i': sales['igst'], 'c': sales['cgst'], 's': sales['sgst']}
    C_avail = {
        'i': op['igst'] + net_itc['i'],
        'c': op['cgst'] + net_itc['c'],
        's': op['sgst'] + net_itc['s']
    }
    
    paid, cash_fwd, bal_credit = calculate_smart_offset(L_fwd, C_avail)
    
    # --- 3. BUILD VISUAL DATA ---
    data = []
    def r(desc, sub, i, c, s): return [desc, sub, i, c, s, i+c+s]

    # SECTION 1: SALES
    data.append(["OUTPUT TAX LIABILITY (SALES)", "", "", "", "", ""])
    data.append(r("1. Output Liability", "Sales", sales['igst'], sales['cgst'], sales['sgst']))
    data.append(r("2. RCM Liability", "Cash Only", tot_rcm['i'], tot_rcm['c'], tot_rcm['s']))
    data.append(r("3. Total Liability", "1 + 2", 0,0,0)) 
    
    data.append(["", "", "", "", "", ""]) 

    # SECTION 2: PURCHASE (ITC)
    data.append(["ITC SUMMARY (GSTR-3B TABLE 4)", "", "", "", "", ""])
    data.append(r("(A) ITC Available", "Total", "", "", "")) 
    data.append(r("   (3) Inward RCM", "Reg+URD", tot_rcm['i'], tot_rcm['c'], tot_rcm['s']))
    data.append(r("   (5) All Other ITC", "B2B-CDNR", sums['all_other']['i'], sums['all_other']['c'], sums['all_other']['s']))
    data.append(r("(B) ITC Reversed", "Ineligible", 0, 0, 0))
    data.append(r("(C) Net ITC Available", "A - B", 0,0,0)) 

    data.append(["", "", "", "", "", ""]) 

    # SECTION 3: AVAILABLE CREDIT
    data.append(["TOTAL AVAILABLE CREDIT", "", "", "", "", ""])
    data.append(r("4. Opening Balance", "Ledger", op['igst'], op['cgst'], op['sgst']))
    data.append(r("5. Current Month ITC", "From (C)", 0,0,0)) 
    data.append(r("6. Total Credit Available", "4 + 5", 0,0,0)) 

    data.append(["", "", "", "", "", ""]) 

    # SECTION 4: OFFSET
    data.append(["OFFSET SUMMARY (SECTION 49)", "", "", "", "", ""])
    data.append(r("Paid by IGST", "-> I, C, S", paid['i_i'], paid['i_c'], paid['i_s']))
    data.append(r("Paid by CGST", "-> C, I", paid['c_i'], paid['c_c'], 0))
    data.append(r("Paid by SGST", "-> S, I", paid['s_i'], 0, paid['s_s']))

    data.append(["", "", "", "", "", ""]) 

    # SECTION 5: FINAL
    data.append(["FINAL CHALLAN CALCULATION", "", "", "", "", ""])
    data.append(r("NET PAYABLE IN CASH", "Liab - Offset", 0,0,0)) 
    data.append(r("BALANCE CREDIT C/F", "Cred - Offset", 0,0,0)) 

    df = pd.DataFrame(data, columns=["Particulars", "Details", "IGST", "CGST", "SGST", "Total"])
    sheet_name = "Master Dashboard"
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    # --- 4. FORMATTING & FORMULAS ---
    wb = writer.book; ws = writer.sheets[sheet_name]
    
    s_head = wb.add_format({'bold':True, 'bg_color':'#2F4F4F', 'font_color':'white', 'border':1})
    s_sub = wb.add_format({'bold':True, 'bg_color':'#DCDCDC', 'border':1})
    s_num = wb.add_format({'num_format':'#,##0.00', 'border':1})
    s_red = wb.add_format({'bold':True, 'bg_color':'#FFC7CE', 'font_color':'#9C0006', 'num_format':'#,##0.00', 'border':1})
    s_green = wb.add_format({'bold':True, 'bg_color':'#C6EFCE', 'font_color':'#006100', 'num_format':'#,##0.00', 'border':1})
    s_blue = wb.add_format({'bg_color':'#E6E6FA', 'num_format':'#,##0.00', 'border':1}) 
    s_bold_num = wb.add_format({'bold':True, 'num_format':'#,##0.00', 'top':1})
    s_sales = wb.add_format({'bold':True, 'bg_color':'#FFCC99', 'border':1})
    s_purch = wb.add_format({'bold':True, 'bg_color':'#CCECFF', 'border':1})
    s_cred = wb.add_format({'bold':True, 'bg_color':'#E6E6FA', 'border':1})
    s_final = wb.add_format({'bold':True, 'bg_color':'#006400', 'font_color':'white', 'border':1})

    ws.set_column(0, 0, 45); ws.set_column(1, 1, 20); ws.set_column(2, 5, 18)

    for c, val in enumerate(df.columns): ws.write(0, c, val, s_sub)

    for r_idx, row in enumerate(data):
        xl_r = r_idx + 1 
        desc = str(row[0])
        if not desc: continue

        if "OUTPUT TAX" in desc: ws.merge_range(xl_r, 0, xl_r, 5, desc, s_sales); continue
        if "ITC SUMMARY" in desc: ws.merge_range(xl_r, 0, xl_r, 5, desc, s_purch); continue
        if "TOTAL AVAILABLE" in desc: ws.merge_range(xl_r, 0, xl_r, 5, desc, s_cred); continue
        if "OFFSET" in desc: ws.merge_range(xl_r, 0, xl_r, 5, desc, s_sub); continue
        if "FINAL CHALLAN" in desc: ws.merge_range(xl_r, 0, xl_r, 5, desc, s_final); continue

        for col_idx in [2, 3, 4]: 
            if "Total Liability" in desc:
                r_1 = xl_rowcol_to_cell(r_idx - 2 + 1, col_idx)
                r_2 = xl_rowcol_to_cell(r_idx - 1 + 1, col_idx)
                ws.write_formula(xl_r, col_idx, f"={r_1}+{r_2}", s_bold_num); continue
            if "Net ITC" in desc:
                r_a3 = xl_rowcol_to_cell(xl_r - 3, col_idx) 
                r_a5 = xl_rowcol_to_cell(xl_r - 2, col_idx)
                r_b  = xl_rowcol_to_cell(xl_r - 1, col_idx)
                ws.write_formula(xl_r, col_idx, f"={r_a3}+{r_a5}-{r_b}", s_bold_num); continue
            if "Current Month ITC" in desc:
                # Points at "(C) Net ITC Available" (data-list index 10, so
                # xlsxwriter row 10+1=11) -- was hardcoded to 11+1=12, which
                # is the blank spacer row right after it, so this always
                # showed 0 regardless of actual ITC.
                target = xl_rowcol_to_cell(10 + 1, col_idx)
                ws.write_formula(xl_r, col_idx, f"={target}", s_num); continue
            if "Total Credit" in desc:
                r_op = xl_rowcol_to_cell(xl_r - 2, col_idx)
                r_cur = xl_rowcol_to_cell(xl_r - 1, col_idx)
                ws.write_formula(xl_r, col_idx, f"={r_op}+{r_cur}", s_bold_num); continue
            if "NET PAYABLE" in desc:
                # Offset range must span "Paid by IGST" through "Paid by
                # SGST" (data-list indices 18-20, xlsxwriter rows 19-21) --
                # was hardcoded one row too late (20-22), silently dropping
                # the entire "Paid by IGST" line from the cash-payable calc.
                r_liab = xl_rowcol_to_cell(3 + 1, col_idx)
                r_off_start = xl_rowcol_to_cell(18 + 1, col_idx)
                r_off_end = xl_rowcol_to_cell(20 + 1, col_idx)
                ws.write_formula(xl_r, col_idx, f"=MAX(0, {r_liab}-SUM({r_off_start}:{r_off_end}))", s_red); continue
            if "BALANCE CREDIT" in desc:
                # Same offset-range fix as NET PAYABLE above, plus r_cred
                # must point at "6. Total Credit Available" (data-list index
                # 15, xlsxwriter row 16) -- was hardcoded to the blank
                # spacer row right after it (17).
                r_cred = xl_rowcol_to_cell(15 + 1, col_idx)
                r_off_start = xl_rowcol_to_cell(18 + 1, col_idx)
                r_off_end = xl_rowcol_to_cell(20 + 1, col_idx)
                ws.write_formula(xl_r, col_idx, f"=MAX(0, {r_cred}-SUM({r_off_start}:{r_off_end}))", s_green); continue
            ws.write(xl_r, col_idx, row[col_idx], s_blue if "Paid by" in desc else s_num)

        cell_i = xl_rowcol_to_cell(xl_r, 2)
        cell_s = xl_rowcol_to_cell(xl_r, 4)
        style_tot = s_red if "NET PAYABLE" in desc else (s_green if "BALANCE" in desc else s_bold_num)
        ws.write_formula(xl_r, 5, f"=SUM({cell_i}:{cell_s})", style_tot)
        ws.write(xl_r, 0, row[0], s_num)
        ws.write(xl_r, 1, row[1], s_num)

    return {'igst': bal_credit['i'], 'cgst': bal_credit['c'], 'sgst': bal_credit['s']}

def generate_vendor_summary(writer, portal_dict, books_dict):
    stats = {}
    def find_cols_robust(df):
        gstin = next((c for c in df.columns if 'gstin' in c.lower()), None)
        name = next((c for c in df.columns if any(k in c.lower() for k in ['vendor', 'trade', 'party', 'name'])), None)
        tax = next((c for c in df.columns if 'taxable' in c.lower()), None)
        igst = next((c for c in df.columns if any(k in c.lower() for k in ['igst', 'integrated'])), None)
        cgst = next((c for c in df.columns if any(k in c.lower() for k in ['cgst', 'central'])), None)
        sgst = next((c for c in df.columns if any(k in c.lower() for k in ['sgst', 'state'])), None)
        return gstin, name, tax, igst, cgst, sgst

    def process(d_dict, source):
        for name, data in d_dict.items():
            df = data if isinstance(data, pd.DataFrame) else data['df']
            g, n, t, i, c, s = find_cols_robust(df)
            if not g or not t: continue
            mult = -1 if ('cdnr' in name.lower() or 'credit' in name.lower()) else 1
            for _, r in df.iterrows():
                gst = clean_gstin(r[g])
                if not gst: continue
                if gst not in stats:
                    stats[gst] = {k:0.0 for k in ['p_tax','p_i','p_c','p_s','b_tax','b_i','b_c','b_s']}
                    stats[gst]['name'] = str(r.get(n, 'Unknown')).strip()
                if stats[gst]['name'] in ['Unknown', 'nan', ''] and n:
                    stats[gst]['name'] = str(r.get(n, '')).strip()
                pre = 'p_' if source == 'portal' else 'b_'
                stats[gst][pre+'tax'] += robust_safe_float(r.get(t,0))*mult
                stats[gst][pre+'i'] += robust_safe_float(r.get(i,0))*mult
                stats[gst][pre+'c'] += robust_safe_float(r.get(c,0))*mult
                stats[gst][pre+'s'] += robust_safe_float(r.get(s,0))*mult

    process(portal_dict, 'portal')
    process(books_dict, 'books')

    summ = []
    for g, d in stats.items():
        diff = d['b_tax'] - d['p_tax']
        status = "Matched"
        if abs(diff) < 2: status = "✅ Fully Matched"
        elif d['p_tax'] == 0: status = "❓ Not in Portal"
        elif d['b_tax'] == 0: status = "❌ Not in Books"
        elif diff > 0: status = "⚠️ Excess in Books"
        else: status = "💰 Unclaimed in Portal"
        summ.append([g, d['name'], d['p_tax'], d['p_i'], d['p_c'], d['p_s'], d['b_tax'], d['b_i'], d['b_c'], d['b_s'], diff, status])
    
    cols = ['GSTIN', 'Name', 'Portal Taxable', 'P-IGST', 'P-CGST', 'P-SGST', 'Books Taxable', 'B-IGST', 'B-CGST', 'B-SGST', 'Diff', 'Status']
    df_s = pd.DataFrame(summ, columns=cols)
    add_formatting(writer, df_s, "Vendor Summary")

def generate_discrepancy_sheets(writer, portal_dict, books_dict):
    not_in_books = []
    prev_period = []
    mismatches = []

    for sheet_name, df in portal_dict.items():
        if 'Remarks' not in df.columns: continue

        nib_df = df[df['Remarks'].str.contains("Not in Books", case=False, na=False)].copy()
        if not nib_df.empty:
            nib_df.insert(0, 'Source Sheet', sheet_name)
            not_in_books.append(nib_df)

        prev_df = df[df['Remarks'].str.contains("Previous", case=False, na=False)].copy()
        if not prev_df.empty:
            prev_df.insert(0, 'Source Sheet', sheet_name)
            prev_period.append(prev_df)

        # "Mismatch" is a substring of "Mismatch (Rate Diff)" too, so this
        # picks up both flavors -- genuinely the same invoice on both sides,
        # different amount or different tax split.
        mis_df = df[df['Remarks'].str.contains("Mismatch", case=False, na=False)].copy()
        if not mis_df.empty:
            mis_df.insert(0, 'Source Sheet', sheet_name)
            mismatches.append(mis_df)

    not_on_portal = []
    for sheet_name, data in books_dict.items():
        df = data['df']
        if 'Remarks' not in df.columns: continue

        nop_df = df[df['Remarks'].str.contains("Not on Portal", case=False, na=False)].copy()
        if not nop_df.empty:
            nop_df.insert(0, 'Source Sheet', sheet_name)
            not_on_portal.append(nop_df)

    # Mismatches is the highest-priority sheet for a reviewer (a real
    # discrepancy that needs correcting, not just something missing), so
    # it's written first among the discrepancy tabs.
    if mismatches:
        final_mis = pd.concat(mismatches, ignore_index=True)
        add_formatting(writer, final_mis, "Mismatches")

    if not_in_books:
        final_nib = pd.concat(not_in_books, ignore_index=True)
        add_formatting(writer, final_nib, "Not in Books")

    if not_on_portal:
        final_nop = pd.concat(not_on_portal, ignore_index=True)
        add_formatting(writer, final_nop, "Not on Portal")

    if prev_period:
        final_prev = pd.concat(prev_period, ignore_index=True)
        add_formatting(writer, final_prev, "Previous Period Input")

def get_smart_sorted_order(portal_dict, books_dict):
    final = []; used = set()
    bk = list(books_dict.keys())
    def clean(n): return n.lower().replace(" ", "").replace("-", "").replace("_", "").replace("(portal)", "").replace("(books)", "")
    
    for p_name, p_df in portal_dict.items():
        best = None; p_cl = clean(p_name)
        for b in bk:
            if b in used: continue
            b_cl = clean(b)
            if p_cl == b_cl or (p_cl=='b2b' and b_cl=='b2b') or (p_cl in b_cl) or (b_cl in p_cl):
                best = b; break
        final.append((f"{p_name[:20]} (Portal)", p_df))
        if best:
            final.append((f"{best[:20]} (Books)", books_dict[best]['df'])); used.add(best)
    
    for b, data in books_dict.items():
        if b not in used: final.append((f"{b[:20]} (Books)", data['df']))
    return final

# ==========================================
#  MAIN ENTRY POINT (CALLED BY APP.PY)
# ==========================================

def generate_reco_report_zoho(file_portal, file_zoho, manual_inputs=None, month_str=None,
                               owner_user_id=None, client_name=None, save_balance=False):
    """
    Main function called by app.py.
    Returns: BytesIO object (Excel file)

    owner_user_id/client_name/save_balance are optional and only used by the
    full GSTR-3B flow (see generate_gstr3b_zoho_report below): when
    save_balance=True, the closing ITC balance computed by
    generate_master_dashboard is persisted for this client/period so next
    month's opening ITC can auto-fill. The plain GSTR-2B reconciliation
    route never sets these, so its behavior is unchanged.
    """
    output = BytesIO()

    # NOTE: this used to be hardcoded to None, which meant "Previous Period"
    # detection could never fire even though the frontend already sends a
    # reconciliation month -- app.py just wasn't reading it. Now parsed
    # properly, same as the Odoo reco engine.
    reco_dt = None
    if month_str:
        try:
            reco_dt = pd.to_datetime(month_str + "-01")
        except (ValueError, TypeError) as e:
            logging.warning(f"Could not parse reconciliation month '{month_str}': {e}")

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 1. Clean Data
        portal_data, reference_sheets = clean_portal_data(file_portal)
        zoho_data = clean_zoho_data(file_zoho)

        # 2. Generate Maps
        books_maps = generate_lookup_maps(zoho_data)
        portal_maps = generate_lookup_maps(portal_data)

        # 3. Process Portal Data
        processed_portal_dfs = {}
        for sheet, df in portal_data.items():
            df_res = reconcile_dataframe(df, books_maps, 'As per Books', True, reco_dt)
            processed_portal_dfs[sheet] = df_res

        # 4. Process Books Data
        for key, data in zoho_data.items():
            data['df'] = reconcile_dataframe(data['df'], portal_maps, 'As per Portal', False)

        # 5. Generate Summaries
        closing_balance = generate_master_dashboard(writer, processed_portal_dfs, zoho_data, manual_inputs)
        generate_vendor_summary(writer, processed_portal_dfs, zoho_data)
        generate_discrepancy_sheets(writer, processed_portal_dfs, zoho_data)

        # 6. Smart Sorting & Detailed Sheets
        sorted_sheets = get_smart_sorted_order(processed_portal_dfs, zoho_data)
        for sheet_name, df in sorted_sheets:
            add_formatting(writer, df, sheet_name)

        # 7. ITC reference sheets (not reconciled, shown as-is for cross-check)
        for sheet_name, df in reference_sheets.items():
            title = f"{sheet_name} (Reference)"[:31]
            add_formatting(writer, df, title)

    if save_balance and owner_user_id and client_name and month_str:
        save_closing_itc(owner_user_id, client_name, month_str, closing_balance)

    output.seek(0)
    return output


# ==========================================
#  FULL GSTR-3B WORKING PAPER (GSTR-1 + GSTR-2B + auto opening/closing ITC)
# ==========================================

def generate_gstr3b_zoho_report(gstr1_file_paths_dict, file_portal, file_zoho,
                                 owner_user_id, client_name, period, opening_itc_override=None,
                                 manual_sales=None):
    """Wraps generate_reco_report_zoho with the two pieces that used to be
    manual entry: 'sales' figures come from real GSTR-1 Zoho files instead
    of typed-in numbers, and opening ITC auto-carries from last period's
    closing balance (falling back to 0 for a client's first run, or the
    explicit override if given). The Section 49 offset math itself
    (calculate_smart_offset) is untouched -- it's the same logic already
    used by the standalone reconciliation tool.

    manual_sales: when provided (dict with taxable/igst/cgst/sgst, CA-entered
    totals), this skips GSTR-1 file parsing entirely -- for whenever Zoho's
    GSTR-1 export isn't usable and the sales figures are worked out by hand,
    same as the equivalent Odoo GSTR-3B option."""
    if manual_sales is not None:
        sales = {
            'taxable': float(manual_sales.get('taxable') or 0),
            'igst': float(manual_sales.get('igst') or 0),
            'cgst': float(manual_sales.get('cgst') or 0),
            'sgst': float(manual_sales.get('sgst') or 0),
        }
    else:
        from modules.indirect_tax.gstr1_zoho import compute_gstr1_zoho_data

        gstr1_frames, _ = compute_gstr1_zoho_data(gstr1_file_paths_dict)
        sales = {'taxable': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0}
        if gstr1_frames:
            for df in gstr1_frames.values():
                sales['taxable'] += float(pd.to_numeric(df.get('Taxable Amount', 0), errors='coerce').fillna(0).sum())
                sales['igst'] += float(pd.to_numeric(df.get('Integrated Tax', 0), errors='coerce').fillna(0).sum())
                sales['cgst'] += float(pd.to_numeric(df.get('Central Tax', 0), errors='coerce').fillna(0).sum())
                sales['sgst'] += float(pd.to_numeric(df.get('State/UT Tax', 0), errors='coerce').fillna(0).sum())

    opening = get_opening_itc(owner_user_id, client_name, period, opening_itc_override)

    manual_inputs = {'sales': sales, 'opening': opening}

    return generate_reco_report_zoho(
        file_portal, file_zoho, manual_inputs, period,
        owner_user_id=owner_user_id, client_name=client_name, save_balance=True,
    )