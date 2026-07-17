import logging
import pandas as pd
from io import BytesIO
import numpy as np
import re
from xlsxwriter.utility import xl_col_to_name

logger = logging.getLogger(__name__)

# ==========================================
#  SECTION 1: SHARED UTILITIES (ADVANCED)
# ==========================================

def add_formatting_and_subtotals(writer, df, sheet_name):
    if df.empty: return 
    
    # Safety: Drop duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Write dataframe
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    (num_rows, num_cols) = df.shape

    # Formats
    header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
    bold_format = workbook.add_format({'bold': True})
    number_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})
    red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'}) 
    green_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'}) 
    
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        worksheet.set_column(col_num, col_num, 15)

    if num_rows > 0:
        worksheet.autofilter(0, 0, num_rows, num_cols - 1)

    total_row = num_rows + 1
    worksheet.write(total_row, 0, 'Filter Total', bold_format)
    
    # Subtotals
    target_cols = [
        'Taxable Value', 'Invoice Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount',
        'IGST', 'CGST', 'SGST', 'Cess', 'Total', 'Taxable Amt.', 'Debit', 'Credit',
        'As per portal', 'As per Books', 'Difference'
    ]
    
    for col_name in target_cols:
        if col_name in df.columns:
            col_idx = df.columns.get_loc(col_name)
            col_letter = xl_col_to_name(col_idx)
            formula = f'=SUBTOTAL(9,{col_letter}2:{col_letter}{total_row})'
            worksheet.write_formula(total_row, col_idx, formula, number_format)
            
    # Conditional Formatting for Remarks
    if 'Remarks' in df.columns:
        rem_idx = df.columns.get_loc('Remarks')
        rem_letter = xl_col_to_name(rem_idx)
        range_str = f"{rem_letter}2:{rem_letter}{total_row}"
        worksheet.conditional_format(range_str, {'type': 'text', 'criteria': 'containing', 'value': 'Not', 'format': red_format})
        worksheet.conditional_format(range_str, {'type': 'text', 'criteria': 'containing', 'value': 'Match', 'format': green_format})

# ==========================================
#  SECTION 2: PORTAL CLEANING LOGIC (FIXED)
# ==========================================

def filter_portal_sheets(xls):
    # NOTE: "ITC Available" / "ITC not available" / "ITC Reversal" / "ITC Rejected"
    # sheets used to be dropped outright, which silently discarded ITC-eligibility
    # data straight off the government portal. They're now kept and flow through
    # the normal cleaning pipeline like every other sheet (see clean_portal_df) so
    # a CA can see them in the output workbook instead of the tool throwing them
    # away. They're still not merged into the reconciliation match logic -- their
    # real column layout hasn't been verified against a live GSTR-2B export, so
    # merging them automatically risked producing a wrong ITC-eligibility tag,
    # which is worse than not having the feature at all.
    sheets_to_delete_always = ["Read me"]
    conditional_delete_map = {
        "B2B": 7, "B2B-CDNR": 7, "ECO": 7, "ISD": 7, "IMPG": 7, "IMPGSEZ": 7,
        "B2B (ITC Reversal)": 7, "B2B-DNR": 7, "B2BA": 8, "B2B-CDNRA": 8
    }
    kept_dataframes = {}
    for sheet in xls.sheet_names:
        sheet_clean = sheet.strip()
        if sheet_clean in sheets_to_delete_always: continue
        try:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
            if sheet_clean in conditional_delete_map:
                target_idx = conditional_delete_map[sheet_clean] - 1
                if len(df) <= target_idx or df.iloc[target_idx].isna().all(): continue
            kept_dataframes[sheet] = df
        except Exception as e:
            logger.warning(f"Skipped portal sheet '{sheet}': {e}")
            continue
    return kept_dataframes

def clean_portal_df(df_raw, sheet_name):
    # 1. Header Logic
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
            if len(new_cols) == df_data.shape[1]: df_data.columns = new_cols
        else: 
            if len(row1) == df_data.shape[1]: df_data.columns = row1
    else: 
        if len(row1) == df_data.shape[1]: df_data.columns = row1

    # 2. Rename & Clean
    rename_map = {
        'Invoice number': 'Invoice Number', 'Note number': 'Invoice Number', 'Bill of entry number': 'Invoice Number',
        'Invoice Value (₹)': 'Invoice Value', 'Taxable Value (₹)': 'Taxable Value',
        'Integrated Tax (₹)': 'IGST Tax Amount', 'Central Tax (₹)': 'CGST Tax Amount', 'State/UT Tax (₹)': 'SGST Tax Amount',
        'Cess Amount (₹)': 'Cess Amount', 'Trade/Legal name': 'Vendor Name', 'GSTIN of supplier': 'GSTIN',
        'Invoice Date': 'Invoice date', 'Place of supply': 'Place Of Supply',
        'Supply Attract Reverse Charge': 'Reverse Charge', 'Rate (%)': 'Rate'
    }
    final_cols = []
    for col in df_data.columns:
        mapped = col
        for k, v in rename_map.items():
            if k.lower() == str(col).lower().strip(): mapped = v; break
        final_cols.append(mapped)
    
    # === CORRECTION: Rename FIRST, then drop duplicates ===
    df_data.columns = final_cols
    df_data = df_data.loc[:, ~df_data.columns.duplicated()]
    # ====================================================

    numeric_cols = ['Taxable Value', 'Invoice Value', 'IGST Tax Amount', 'CGST Tax Amount', 'SGST Tax Amount', 'Cess Amount', 'Rate']
    for col in numeric_cols:
        if col in df_data.columns: df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)

    unwanted = ['period', 'filing date', 'applicable %', 'source', 'irn']
    cols_to_drop = [c for c in df_data.columns if any(kw in str(c).lower() for kw in unwanted)]
    if cols_to_drop: df_data.drop(columns=cols_to_drop, inplace=True, errors='ignore')

    df_data = df_data.replace(r'^\s*$', np.nan, regex=True).dropna(axis=1, how='all')
    for col in numeric_cols:
        if col in df_data.columns and df_data[col].abs().max() == 0: df_data.drop(columns=[col], inplace=True)
        
    return df_data

# Sheets that carry ITC-eligibility information rather than a distinct set of
# transactions. Kept and shown in the output workbook for reference, but
# deliberately NOT merged into the match/reconciliation logic below -- their
# rows likely overlap with invoices already listed in B2B/ECO/etc, and
# reconciling them too would double-count those invoices.
ITC_REFERENCE_SHEETS = {"ITC Available", "ITC not available", "ITC Reversal", "ITC Rejected"}

# ==========================================
#  SECTION 3: ODOO CLEANING LOGIC (PRESERVED)
# ==========================================

def clean_odoo_data(df, is_rcm=False):
    required_cols = ['Account', 'Label', 'Date']
    for col in required_cols:
        if col not in df.columns: df[col] = ''

    if 'Debit' not in df.columns: df['Debit'] = 0.0
    if 'Credit' not in df.columns: df['Credit'] = 0.0
    
    df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
    df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)

    # Tax Calculation
    account_series = df['Account'].astype(str)
    is_igst = account_series.str.contains('igst', case=False, na=False)
    is_cgst = account_series.str.contains('cgst', case=False, na=False)
    is_sgst = account_series.str.contains('sgst', case=False, na=False)
    
    if is_rcm:
        condition = df['Debit'] != 0
        df['Tax_Amount'] = np.where(condition, df['Debit'], df['Credit'])
    else:
        condition = df['Credit'] != 0
        df['Tax_Amount'] = np.where(condition, df['Credit'], df['Debit'])

    df['IGST'] = np.where(is_igst, df['Tax_Amount'], 0.0)
    df['CGST'] = np.where(is_cgst, df['Tax_Amount'], 0.0)
    df['SGST'] = np.where(is_sgst, df['Tax_Amount'], 0.0)

    mask_missing_sgst = (df['CGST'] != 0) & (df['SGST'] == 0)
    df.loc[mask_missing_sgst, 'SGST'] = df.loc[mask_missing_sgst, 'CGST']

    if 'Label' in df.columns:
        df['Rate'] = df['Label'].astype(str).str.extract(r'(\d+\.?\d*)%').astype(float)
        df['Rate_Str'] = df['Rate'].map('{:.2f}%'.format, na_action='ignore')
    else:
        df['Rate'] = 0.0; df['Rate_Str'] = '0.00%'
    
    if 'Taxable Amt.' not in df.columns: df['Taxable Amt.'] = 0.0
    df['Taxable Amt.'] = pd.to_numeric(df['Taxable Amt.'], errors='coerce').fillna(0)
    df['Total'] = df['Taxable Amt.'] + df['IGST'] + df['CGST'] + df['SGST']
    
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%d-%m-%Y')

    # Mapping Reference/Number to Invoice Number
    if 'Reference' in df.columns:
        df['Invoice Number'] = df['Reference'].fillna(df['Number'] if 'Number' in df.columns else '')
    elif 'Number' in df.columns:
        df['Invoice Number'] = df['Number']

    # --- BRIDGE: Make Compatible with Advanced Engine ---
    # The Engine looks for 'Taxable Value' and 'Invoice date'
    if 'Taxable Amt.' in df.columns: df['Taxable Value'] = df['Taxable Amt.']
    if 'Date' in df.columns: df['Invoice date'] = df['Date']
    # --------------------------------------------------

    final_columns = [
        'Partner', 'GSTIN', 'Date', 'Invoice date', 'Invoice Number', 'Number', 'Reference', 'Account', 
        'Label', 'Rate_Str', 'Total', 'Taxable Amt.', 'Taxable Value', 'IGST', 'CGST', 'SGST',
        'As per Portal', 'Difference', 'Remarks'
    ]
    for col in final_columns:
        if col not in df.columns: df[col] = '' 
    return df[final_columns]

def process_odoo_logic_4files(file_dict):
    """
    Processes the 4 distinct Odoo files:
    - reg_cgst, reg_igst (Combines to B2B + V CN)
    - rcm_cgst, rcm_igst (Combines to RCM + V CN RCM)
    """
    processed_results = {}

    def load_df(key):
        file = file_dict.get(key)
        if not file: return None
        try:
            return pd.read_excel(file)
        except Exception:
            try:
                file.seek(0)
                return pd.read_csv(file)
            except Exception as e:
                logger.warning(f"Could not read Odoo file for '{key}': {e}")
                return None

    # --- 1. REGULAR (B2B) ---
    reg_cgst = load_df('odoo_reg_cgst')
    reg_igst = load_df('odoo_reg_igst')
    regular_dfs = [d for d in [reg_cgst, reg_igst] if d is not None]

    if regular_dfs:
        reg_df = pd.concat(regular_dfs, ignore_index=True)
        if 'Credit' in reg_df.columns:
            v_cn_mask = reg_df['Credit'] != 0
            processed_results['B2B as per Books'] = clean_odoo_data(reg_df[~v_cn_mask].copy(), is_rcm=False)
            processed_results['V CN as per Books'] = clean_odoo_data(reg_df[v_cn_mask].copy(), is_rcm=False)
        else:
            processed_results['B2B as per Books'] = clean_odoo_data(reg_df, is_rcm=False)

    # --- 2. RCM ---
    rcm_cgst = load_df('odoo_rcm_cgst')
    rcm_igst = load_df('odoo_rcm_igst')
    rcm_dfs = [d for d in [rcm_cgst, rcm_igst] if d is not None]

    if rcm_dfs:
        rcm_df = pd.concat(rcm_dfs, ignore_index=True)
        if 'Debit' in rcm_df.columns:
            # For RCM, Credit Notes usually have Debit values
            rcm_cn_mask = rcm_df['Debit'] != 0
            
            rcm_cn_data = rcm_df[rcm_cn_mask].copy()
            # Flip Taxable for RCM CN
            if 'Taxable Amt.' in rcm_cn_data.columns: 
                rcm_cn_data['Taxable Amt.'] = rcm_cn_data['Taxable Amt.'] * -1
            
            processed_results['RCM as per Books'] = clean_odoo_data(rcm_df[~rcm_cn_mask].copy(), is_rcm=True)
            processed_results['V CN RCM as per Books'] = clean_odoo_data(rcm_cn_data, is_rcm=True)
        else:
            processed_results['RCM as per Books'] = clean_odoo_data(rcm_df, is_rcm=True)

    return processed_results

# ==========================================
#  SECTION 4: RECO ENGINE (ADVANCED FUZZY & DATE)
# ==========================================

def clean_inv_str(s):
    if pd.isna(s): return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(s).lower())

def get_itc_deadline(invoice_date):
    """Section 16(4): ITC on an invoice must be claimed by 30th November
    following the end of the financial year (Apr-Mar) it belongs to. Returns
    None if invoice_date isn't a usable date. This is the statutory ceiling,
    not the earlier "date of filing the annual return" cutoff (we don't have
    that filing date available here), so it's a conservative/latest bound."""
    if pd.isna(invoice_date): return None
    year, month = invoice_date.year, invoice_date.month
    fy_end_year = year + 1 if month >= 4 else year
    return pd.Timestamp(year=fy_end_year, month=11, day=30)

def generate_lookup_map(data_source):
    exact_map = {}
    amount_map = {}

    for key, val in data_source.items():
        if isinstance(val, pd.DataFrame): df = val
        else: df = val['df']

        # Support both Taxable Value and Taxable Amt.
        col_inv = 'Invoice Number'
        col_tax = 'Taxable Value' if 'Taxable Value' in df.columns else 'Taxable Amt.'

        if col_inv in df.columns and col_tax in df.columns:
            for _, row in df.iterrows():
                inv_raw = str(row[col_inv]).strip()
                inv_clean = clean_inv_str(inv_raw)
                if not inv_clean:
                    continue

                try:
                    raw_tax = float(row[col_tax])
                    tax_val = raw_tax if pd.notnull(raw_tax) else 0.0
                except (TypeError, ValueError):
                    tax_val = 0.0

                # Exact-match key is normalized the same way as the fuzzy key
                # (lowercased, punctuation/whitespace stripped) so "INV-001",
                # "inv 001" and "INV001" are all treated as the same invoice
                # instead of only matching on identical formatting.
                if inv_clean not in exact_map:
                    exact_map[inv_clean] = tax_val

                # Bucketed to the nearest rupee rather than the exact paisa
                # value, so a small rounding difference between the portal
                # and the books doesn't stop the fuzzy invoice-number check
                # below from ever getting a chance to run.
                amt_key = round(tax_val)
                amount_map.setdefault(amt_key, []).append({
                    'clean_inv': inv_clean,
                    'tax_val': tax_val
                })

    return exact_map, amount_map

def apply_reco_logic(df, lookup_maps, target_col_name, is_portal_sheet, reco_month_dt=None):
    exact_map, amount_map = lookup_maps

    df[target_col_name] = 0.0; df['Difference'] = 0.0; df['Remarks'] = ''
    if is_portal_sheet:
        df['ITC Time-Barred'] = ''
    col_inv = 'Invoice Number'
    col_tax = 'Taxable Value' if 'Taxable Value' in df.columns else 'Taxable Amt.'
    col_date = 'Invoice date'

    if col_inv not in df.columns: return df

    if col_date in df.columns:
        # Try day-first first (standard Indian format); anything still
        # unparsed gets a second attempt the other way round instead of
        # being silently given up on.
        raw_dates = df[col_date]
        parsed = pd.to_datetime(raw_dates, dayfirst=True, errors='coerce')
        still_unparsed = parsed.isna() & raw_dates.notna()
        if still_unparsed.any():
            parsed.loc[still_unparsed] = pd.to_datetime(raw_dates[still_unparsed], dayfirst=False, errors='coerce')
        df[col_date] = parsed

    today = pd.Timestamp.now().normalize()

    def row_logic(row):
        inv_raw = str(row.get(col_inv, '')).strip()
        inv_clean = clean_inv_str(inv_raw)

        my_tax = float(row.get(col_tax, 0)) if pd.notnull(row.get(col_tax, 0)) else 0.0

        remark = ""
        other_val = 0.0
        diff = 0.0
        match_found = False

        # 1. Exact match (case/whitespace/punctuation-insensitive)
        if inv_clean and inv_clean in exact_map:
            other_val = exact_map[inv_clean]
            match_found = True
            remark = "Match" if abs(my_tax - other_val) < 2 else "Mismatch"

        # 2. Fuzzy match: same invoice-number substring logic as before, but
        # checked across neighboring rupee buckets (not just the exact paisa
        # bucket) so small rounding differences don't block it.
        if not match_found and inv_clean:
            rounded = round(my_tax)
            for amt_key in (rounded, rounded - 1, rounded + 1):
                candidates = amount_map.get(amt_key)
                if not candidates:
                    continue
                for cand in candidates:
                    cand_clean = cand['clean_inv']
                    if cand_clean and ((inv_clean in cand_clean) or (cand_clean in inv_clean)):
                        other_val = cand['tax_val']
                        match_found = True
                        remark = "Match (Fuzzy)"
                        break
                if match_found:
                    break

        if match_found:
            diff = my_tax - other_val
            if abs(diff) > 2: remark = "Mismatch"
        else:
            remark = "Not in Books" if is_portal_sheet else "Not on Portal"
            diff = my_tax

        itc_barred = ''
        inv_dt = row.get(col_date) if col_date in row else None
        has_date = isinstance(inv_dt, pd.Timestamp) and pd.notnull(inv_dt)

        # 3. Previous-period check (portal side only, requires a reco month)
        if is_portal_sheet and reco_month_dt is not None and has_date and inv_dt < reco_month_dt:
            remark = (remark + " (Old Inv)") if "Match" in remark else "Previous Period Inv"

        # 4. Section 16(4) time-barred ITC check (portal side only)
        if is_portal_sheet and has_date:
            deadline = get_itc_deadline(inv_dt)
            if deadline is not None and today > deadline:
                itc_barred = f"YES (was due {deadline.strftime('%d-%b-%Y')})"

        return pd.Series([other_val, diff, remark, itc_barred])

    results = df.apply(row_logic, axis=1)
    if not results.empty:
        df[target_col_name] = results[0]
        df['Difference'] = results[1]
        df['Remarks'] = results[2]
        if is_portal_sheet:
            df['ITC Time-Barred'] = results[3]
    return df

# ==========================================
#  SECTION 5: SMART SORTING
# ==========================================

def get_smart_sorted_order(portal_dict, books_dict):
    portal_invs = {}
    for k, df in portal_dict.items():
        if 'Invoice Number' in df.columns:
            unique_invs = set(df['Invoice Number'].astype(str).str.lower().str.strip())
            portal_invs[k] = unique_invs
            
    books_invs = {}
    for k, df in books_dict.items():
        if 'Invoice Number' in df.columns:
            unique_invs = set(df['Invoice Number'].astype(str).str.lower().str.strip())
            books_invs[k] = unique_invs
    
    final_order = []
    used_books = set()

    for p_name, p_df in portal_dict.items():
        best_match_name = None
        highest_intersect = 0
        p_set = portal_invs.get(p_name, set())

        if p_set:
            for b_name, b_set in books_invs.items():
                if b_name in used_books: continue
                common_count = len(p_set.intersection(b_set))
                if common_count > highest_intersect:
                    highest_intersect = common_count
                    best_match_name = b_name

        base_name = p_name[:20].strip() 
        p_sheet_title = f"{base_name} (Portal)"
        final_order.append((p_sheet_title, p_df))

        if best_match_name and highest_intersect > 0:
            b_df = books_dict[best_match_name]
            b_sheet_title = f"{base_name} (Books)"
            final_order.append((b_sheet_title, b_df))
            used_books.add(best_match_name)

    for b_name, b_df in books_dict.items():
        if b_name not in used_books:
            title = f"{b_name} (Books)"[:31]
            final_order.append((title, b_df))
            
    return final_order

# ==========================================
#  SECTION 6: VENDOR SUMMARY
# ==========================================

def generate_vendor_summary(processed_portal):
    """Rolls up the portal-side reconciliation results by vendor, so a CA can
    see which suppliers have the most mismatches/missing invoices without
    reading through every row of every sheet."""
    frames = [df for df in processed_portal.values() if 'Remarks' in df.columns and 'Vendor Name' in df.columns]
    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined['Vendor Name'] = combined['Vendor Name'].replace('', np.nan).fillna('Unknown')

    group_cols = ['Vendor Name'] + (['GSTIN'] if 'GSTIN' in combined.columns else [])
    grouped = combined.groupby(group_cols).agg(
        Total_Invoices=('Remarks', 'count'),
        Matched=('Remarks', lambda s: s.str.startswith('Match').sum()),
        Mismatched=('Remarks', lambda s: (s == 'Mismatch').sum()),
        Not_In_Books=('Remarks', lambda s: (s == 'Not in Books').sum()),
        Total_Difference=('Difference', 'sum'),
    ).reset_index()
    count_cols = ['Total_Invoices', 'Matched', 'Mismatched', 'Not_In_Books']
    grouped[count_cols] = grouped[count_cols].astype(int)

    return grouped.reindex(grouped['Total_Difference'].abs().sort_values(ascending=False).index)

# ==========================================
#  SECTION 7: MAIN ENTRY POINT
# ==========================================

def generate_reco_report(file_portal, odoo_files_dict, month_str=None):
    output = BytesIO()
    reco_dt = None

    if month_str:
        try:
            reco_dt = pd.to_datetime(month_str + "-01")
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse reconciliation month '{month_str}': {e}")

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

        # 1. Portal Processing -- split into sheets to reconcile vs. ITC
        # reference-only sheets (see ITC_REFERENCE_SHEETS above)
        xls_p = pd.ExcelFile(file_portal)
        raw_portal = filter_portal_sheets(xls_p)
        clean_portal_dict = {}
        reference_sheets = {}
        rcm_frames = []
        for sheet, df_raw in raw_portal.items():
            df = clean_portal_df(df_raw, sheet)
            if df.empty: continue
            if sheet.strip() in ITC_REFERENCE_SHEETS:
                reference_sheets[sheet] = df
                continue
            if 'Reverse Charge' in df.columns:
                is_rcm = df['Reverse Charge'].astype(str).str.strip().str.lower().isin(['yes', 'y'])
                if is_rcm.any():
                    rcm_data = df[is_rcm].copy(); rcm_data['Source'] = sheet
                    rcm_frames.append(rcm_data); df = df[~is_rcm]
            clean_portal_dict[sheet] = df
        if rcm_frames: clean_portal_dict['RCM Combined'] = pd.concat(rcm_frames, ignore_index=True)

        # 2. Odoo Processing
        clean_odoo_dict = process_odoo_logic_4files(odoo_files_dict)

        # 3. Indexing
        books_maps_tuple = generate_lookup_map(clean_odoo_dict)
        portal_maps_tuple = generate_lookup_map(clean_portal_dict)

        # 4. Apply Logic (Portal Sheets)
        processed_portal = {}
        for sheet_name, df in clean_portal_dict.items():
            df_final = apply_reco_logic(df, books_maps_tuple, 'As per Books', True, reco_dt)
            processed_portal[sheet_name] = df_final

        # 5. Apply Logic (Books Sheets)
        processed_books = {}
        for sheet_name, df in clean_odoo_dict.items():
            df_final = apply_reco_logic(df, portal_maps_tuple, 'As per Portal', False, None)
            processed_books[sheet_name] = df_final

        # 6. Vendor Summary (written first so it's the first tab a reviewer sees)
        vendor_summary = generate_vendor_summary(processed_portal)
        if not vendor_summary.empty:
            add_formatting_and_subtotals(writer, vendor_summary, "Vendor Summary")

        # 7. Smart Sorting & Writing (main reconciliation sheets)
        sorted_sheets = get_smart_sorted_order(processed_portal, processed_books)
        for sheet_title, df_final in sorted_sheets:
            add_formatting_and_subtotals(writer, df_final, sheet_title)

        # 8. ITC reference sheets (not reconciled, shown as-is for cross-check)
        for sheet_name, df in reference_sheets.items():
            title = f"{sheet_name} (Reference)"[:31]
            add_formatting_and_subtotals(writer, df, title)

    output.seek(0)
    return output