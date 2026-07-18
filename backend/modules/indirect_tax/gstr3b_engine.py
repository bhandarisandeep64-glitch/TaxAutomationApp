"""
GSTR-3B working paper automation (Odoo clients).

Ties together:
  - GSTR-1 categorized summary (reuses gstr1_odoo.compute_gstr1_data)
  - GSTR-2B reconciliation (reuses gstr2b_reco_engine.compute_reco_data,
    including the "ITC Availability" merge)
  - Section 49 ITC-offset math (fixed 50/50 IGST-remainder-split rule) and
    the resulting journal voucher entries (fixed Odoo account codes)
  - opening ITC carried automatically from last period's closing balance
    (GstrPeriodBalance)

The GSTR2B SUMMARY categorization rules and the entire 3B SUMMARY layout/
formulas below were reverse-engineered against a real, filed 3B working
paper the firm shared and verified line-by-line against its actual numbers
-- see backend/tests/test_gstr3b_engine.py for the exact source data and
expected totals.

The "previous month input" GSTR-2B bucket (invoices dated before the
reconciliation month that matched books this run) is fully automated --
gstr2b_reco_engine tags these rows "Previous Month Input", and this engine
reads that remark directly. The "NOT CLAIMED WORKING" sheet (tracking
invoices still not found in books at all) stays a blank template for manual
entry -- confirmed with the firm that this specific step stays manual.
"""
from io import BytesIO

import pandas as pd

from modules.indirect_tax.gstr1_odoo import compute_gstr1_data
from modules.indirect_tax.gstr2b_reco_engine import (
    compute_reco_data, add_formatting_and_subtotals, get_smart_sorted_order,
)
from modules.indirect_tax.gstr_period_balance import get_opening_itc, save_closing_itc

# Standard Odoo chart-of-accounts codes -- confirmed identical for every
# Odoo client, so these are fixed rather than per-client configuration.
ACCOUNTS = {
    'igst_payable': '112322 IGST Payable',
    'cgst_payable': '112321 CGST Payable',
    'sgst_payable': '112320 SGST Payable',
    'igst_receivable': '100512 IGST Receivable',
    'cgst_receivable': '100511 CGST Receivable',
    'sgst_receivable': '100510 SGST Receivable',
    'rcm_receivable': '100570 Reverse Charge Tax Receivable',
    'rcm_payable': '112319 Gst Payable',
}

GSTR1_CATEGORIES = ['B2B', 'B2B CDNR', 'B2C', 'B2C CDNR']

MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']


# ==========================================
#  GSTR-2B CATEGORIZED SUMMARY
# ==========================================

def _is_claimable_remark(remark):
    """A genuine current-period match -- excludes both "Mismatch" (which
    contains "match" as a substring) and "Previous Month Input" (which
    doesn't, but is called out explicitly for clarity)."""
    r = str(remark or '').lower()
    return 'match' in r and 'mismatch' not in r and 'previous month' not in r

def _is_previous_month_input(remark):
    return 'previous month' in str(remark or '').lower()

def _is_itc_available(value):
    return str(value or '').strip().lower() == 'yes'

def _real_rows(df):
    """Excludes a sheet's own pre-existing 'Filter Total' row (identified by
    a blank Invoice Number) -- present in some already-processed exports and
    otherwise silently double-counted into any aggregate."""
    if df is None or df.empty or 'Invoice Number' not in df.columns:
        return df if df is not None else pd.DataFrame()
    return df[df['Invoice Number'].notna() & (df['Invoice Number'].astype(str).str.strip() != '')]

def _find_col(df, *candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def _sum4(df):
    df = _real_rows(df)
    if df is None or df.empty:
        return {'taxable': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0}
    tax_col = _find_col(df, 'Taxable Value', 'Taxable Amt.')
    igst_col = _find_col(df, 'IGST Tax Amount', 'IGST', 'Integrated Tax(₹)', 'Integrated Tax (₹)')
    cgst_col = _find_col(df, 'CGST Tax Amount', 'CGST', 'Central Tax(₹)', 'Central Tax (₹)')
    sgst_col = _find_col(df, 'SGST Tax Amount', 'SGST', 'State/UT Tax(₹)', 'State/UT Tax (₹)')

    def s(col):
        return float(pd.to_numeric(df[col], errors='coerce').fillna(0).sum()) if col else 0.0

    return {'taxable': s(tax_col), 'igst': s(igst_col), 'cgst': s(cgst_col), 'sgst': s(sgst_col)}

def _find_sheet(sheets, name):
    target = name.strip().lower()
    for k, df in sheets.items():
        if k.strip().lower() == target:
            return df
    return None

def compute_gstr2b_buckets(processed_portal, processed_books):
    """Returns the 4 GSTR2B SUMMARY category rows (current month B2B claimed,
    previous month input, credit note claimed, RCM), plus the underlying
    filtered rows for the supporting detail block.

    "Previous month input" is invoices dated before the reconciliation month
    that matched books this run -- gstr2b_reco_engine tags these
    "Previous Month Input" (see apply_reco_logic), so this bucket reads
    directly off that remark rather than needing separate tracking."""
    b2b_portal = _find_sheet(processed_portal, 'B2B')
    cdnr_portal = _find_sheet(processed_portal, 'B2B-CDNR')
    rcm_regular = processed_books.get('RCM as per Books')
    rcm_cn = processed_books.get('V CN RCM as per Books')

    def filter_rows(df, remark_predicate):
        if df is None or df.empty or 'Remarks' not in df.columns or 'ITC Availability' not in df.columns:
            return pd.DataFrame()
        mask = df['Remarks'].apply(remark_predicate) & df['ITC Availability'].apply(_is_itc_available)
        return df[mask]

    bucket_a_rows = filter_rows(b2b_portal, _is_claimable_remark)
    bucket_b_rows = filter_rows(b2b_portal, _is_previous_month_input)
    bucket_c_rows = filter_rows(cdnr_portal, _is_claimable_remark)

    rcm_frames = [df for df in [rcm_regular, rcm_cn] if df is not None and not df.empty]
    bucket_d_rows = pd.concat(rcm_frames, ignore_index=True) if rcm_frames else pd.DataFrame()

    return {
        'current_month_b2b': _sum4(bucket_a_rows),
        'previous_month_input': _sum4(bucket_b_rows),
        'credit_note': _sum4(bucket_c_rows),
        'rcm': _sum4(bucket_d_rows),
        'detail_rows': {
            'current_month_b2b': bucket_a_rows,
            'previous_month_input': bucket_b_rows,
            'credit_note': bucket_c_rows,
            'rcm': bucket_d_rows,
        },
    }


# ==========================================
#  GSTR-1 CATEGORIZED SUMMARY
# ==========================================

def compute_gstr1_buckets(gstr1_summary_df):
    """Maps the free-form Nature groupby from compute_gstr1_data onto the
    fixed 4-category layout the 3B SUMMARY sheet expects, defaulting any
    category with no transactions this month to zero (so the sheet's row
    positions -- and the formulas that reference them by fixed cell -- never
    shift around from month to month)."""
    values = {}
    if gstr1_summary_df is not None:
        for _, row in gstr1_summary_df.iterrows():
            values[str(row.get('Category', '')).strip()] = row

    result = {}
    for cat in GSTR1_CATEGORIES:
        row = values.get(cat)
        result[cat] = {
            'taxable': float(row['Taxable']) if row is not None else 0.0,
            'igst': float(row['IGST']) if row is not None else 0.0,
            'cgst': float(row['CGST']) if row is not None else 0.0,
            'sgst': float(row['SGST']) if row is not None else 0.0,
        }
    return result


def build_manual_gstr1_buckets(manual):
    """Same output shape as compute_gstr1_buckets, but from CA-entered
    totals instead of parsed ledger files -- used when Odoo's GSTR-1 export
    format isn't usable and the firm is preparing that summary by hand."""
    manual = manual or {}
    result = {}
    for cat in GSTR1_CATEGORIES:
        vals = manual.get(cat) or {}
        result[cat] = {
            'taxable': float(vals.get('taxable') or 0),
            'igst': float(vals.get('igst') or 0),
            'cgst': float(vals.get('cgst') or 0),
            'sgst': float(vals.get('sgst') or 0),
        }
    return result


def compute_3b_totals(gstr1_buckets, gstr2b_buckets, opening_itc):
    """The Section 49 offset math, standalone and testable. Used to persist
    a closing ITC balance for next month's opening-ITC auto-fill -- the
    authoritative, reviewable numbers live in the actual Excel formulas
    written by write_3b_summary_sheet (an exact replica of the firm's
    existing formulas, quirks included). This function uses a capped
    utilization rule (never use more ITC than the liability actually left
    after the IGST offset) rather than replicating a same-cell-reference
    inconsistency in the source formulas that opening-ITC-is-always-zero
    in the one real sample available made impossible to fully disambiguate
    -- capping only matters when ITC would otherwise exceed liability, and
    produces identical figures to the literal formulas on the verified
    real-data case (see tests/test_gstr3b_engine.py)."""
    current_month_itc = {
        head: (gstr2b_buckets['current_month_b2b'][head] + gstr2b_buckets['previous_month_input'][head]
               - gstr2b_buckets['credit_note'][head] + gstr2b_buckets['rcm'][head])
        for head in ('igst', 'cgst', 'sgst')
    }
    total_available = {head: opening_itc[head] + current_month_itc[head] for head in ('igst', 'cgst', 'sgst')}

    sales_igst = gstr1_buckets['B2B']['igst'] - gstr1_buckets['B2B CDNR']['igst'] + gstr1_buckets['B2C']['igst'] - gstr1_buckets['B2C CDNR']['igst']
    sales_cgst = gstr1_buckets['B2B']['cgst'] - gstr1_buckets['B2B CDNR']['cgst'] + gstr1_buckets['B2C']['cgst'] - gstr1_buckets['B2C CDNR']['cgst']
    sales_sgst = gstr1_buckets['B2B']['sgst'] - gstr1_buckets['B2B CDNR']['sgst'] + gstr1_buckets['B2C']['sgst'] - gstr1_buckets['B2C CDNR']['sgst']
    rcm = gstr2b_buckets['rcm']

    # IGST ITC offsets IGST liability first (uncapped, matching the firm's
    # own formula), then the *remainder* splits 50/50 into CGST/SGST usage.
    igst_used_on_igst = sales_igst
    igst_remainder = total_available['igst'] - igst_used_on_igst
    igst_used_on_cgst = igst_remainder / 2
    igst_used_on_sgst = igst_remainder / 2

    cgst_liability_after_igst = sales_cgst - igst_used_on_cgst
    sgst_liability_after_igst = sales_sgst - igst_used_on_sgst
    cgst_itc_used = min(total_available['cgst'], max(cgst_liability_after_igst, 0))
    sgst_itc_used = min(total_available['sgst'], max(sgst_liability_after_igst, 0))

    cash_payable = {
        'igst': max(sales_igst - igst_used_on_igst + rcm['igst'], 0),
        'cgst': max(cgst_liability_after_igst - cgst_itc_used + rcm['cgst'], 0),
        'sgst': max(sgst_liability_after_igst - sgst_itc_used + rcm['sgst'], 0),
    }
    remaining_itc = {
        'igst': total_available['igst'] - (igst_used_on_igst + igst_used_on_cgst + igst_used_on_sgst),
        'cgst': total_available['cgst'] - cgst_itc_used,
        'sgst': total_available['sgst'] - sgst_itc_used,
    }

    return {
        'total_available_itc': total_available,
        'sales_liability': {'igst': sales_igst, 'cgst': sales_cgst, 'sgst': sales_sgst},
        'cash_payable': cash_payable,
        'net_payable_cash': sum(cash_payable.values()) - (rcm['igst'] + rcm['cgst'] + rcm['sgst']),
        'remaining_itc': remaining_itc,
    }



# ==========================================
#  3B SUMMARY SHEET (exact layout/formulas from the real working paper)
# ==========================================

def write_3b_summary_sheet(writer, opening_itc, period_label):
    """Writes the '3B SUMMARY' sheet with LIVE FORMULAS (not pre-computed
    static values) referencing 'GSTR1 SUMMARY' and 'GSTR2B SUMMARY', exactly
    matching the real working paper's structure -- so if a reviewer edits the
    GSTR2B SUMMARY category rows (e.g. after manually filling in "previous
    month input"), everything downstream recalculates automatically in
    Excel, the same way the firm's existing working paper already works."""
    wb = writer.book
    ws = wb.add_worksheet("3B SUMMARY")
    writer.sheets["3B SUMMARY"] = ws

    bold = wb.add_format({'bold': True})
    header = wb.add_format({'bold': True, 'bg_color': '#2F4F4F', 'font_color': 'white'})
    num = wb.add_format({'num_format': '#,##0.00'})
    num_bold = wb.add_format({'bold': True, 'num_format': '#,##0.00'})
    green = wb.add_format({'bold': True, 'bg_color': '#C6EFCE', 'font_color': '#006100', 'num_format': '#,##0.00'})
    red = wb.add_format({'bold': True, 'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'num_format': '#,##0.00'})

    ws.set_column(1, 15, 16)
    ws.set_column(3, 3, 30)
    ws.set_column(6, 6, 32)

    R = lambda excel_row: excel_row - 1  # 1-indexed Excel row -> 0-indexed xlsxwriter row
    C = lambda excel_col_letter: ord(excel_col_letter) - ord('A')

    # --- ITC BEFORE FILING (G2:J6) ---
    ws.write(R(2), C('G'), 'ITC BEFORE FILING', header)
    ws.write_row(R(3), C('G'), ['PARTICULARS', 'IGST', 'CGST', 'SGST'], bold)
    ws.write(R(4), C('G'), 'OPENING ITC')
    ws.write(R(4), C('H'), opening_itc['igst'], num)
    ws.write(R(4), C('I'), opening_itc['cgst'], num)
    ws.write(R(4), C('J'), opening_itc['sgst'], num)
    ws.write(R(5), C('G'), 'CURRENT MONTH ITC')
    ws.write_formula(R(5), C('H'), "=M11", num)
    ws.write_formula(R(5), C('I'), "=N11", num)
    ws.write_formula(R(5), C('J'), "=O11", num)
    ws.write(R(6), C('G'), 'TOTAL', bold)
    ws.write_formula(R(6), C('H'), "=SUM(H4:H5)", num_bold)
    ws.write_formula(R(6), C('I'), "=SUM(I4:I5)", num_bold)
    ws.write_formula(R(6), C('J'), "=SUM(J4:J5)", num_bold)

    # --- GSTR1 SUMMARY (B7:F11) / GST2B SUMMARY (K7:P11) ---
    ws.write(R(7), C('B'), 'GSTR1 SUMMARY', header)
    ws.write(R(7), C('K'), 'GST2B SUMMARY', header)
    ws.write_row(R(8), C('B'), ['PARTICULARS', 'TAXABLE VALUE', 'IGST', 'CGST', 'SGST'], bold)
    ws.write_row(R(8), C('K'), ['PARTICULARS', 'TAXABLE VALUE', 'IGST', 'CGST', 'SGST', 'TOTAL'], bold)

    ws.write(R(9), C('B'), 'SALES')
    ws.write_formula(R(9), C('C'), "='GSTR1 SUMMARY'!B6", num)
    ws.write_formula(R(9), C('D'), "='GSTR1 SUMMARY'!C6", num)
    ws.write_formula(R(9), C('E'), "='GSTR1 SUMMARY'!D6", num)
    ws.write_formula(R(9), C('F'), "='GSTR1 SUMMARY'!E6", num)
    ws.write(R(9), C('K'), 'ITC OTHER THAN RCM')
    ws.write_formula(R(9), C('L'), "='GSTR2B SUMMARY'!B2+'GSTR2B SUMMARY'!B3-'GSTR2B SUMMARY'!B4", num)
    ws.write_formula(R(9), C('M'), "='GSTR2B SUMMARY'!C2+'GSTR2B SUMMARY'!C3-'GSTR2B SUMMARY'!C4", num)
    ws.write_formula(R(9), C('N'), "='GSTR2B SUMMARY'!D2+'GSTR2B SUMMARY'!D3-'GSTR2B SUMMARY'!D4", num)
    ws.write_formula(R(9), C('O'), "='GSTR2B SUMMARY'!E2+'GSTR2B SUMMARY'!E3-'GSTR2B SUMMARY'!E4", num)
    ws.write_formula(R(9), C('P'), "=M9+N9+O9", num)

    ws.write(R(10), C('B'), 'RCM')
    ws.write_formula(R(10), C('C'), "='GSTR2B SUMMARY'!B5", num)
    ws.write_formula(R(10), C('D'), "='GSTR2B SUMMARY'!C5", num)
    ws.write_formula(R(10), C('E'), "='GSTR2B SUMMARY'!D5", num)
    ws.write_formula(R(10), C('F'), "='GSTR2B SUMMARY'!E5", num)
    ws.write(R(10), C('K'), 'RCM')
    ws.write_formula(R(10), C('L'), "=C10", num)
    ws.write_formula(R(10), C('M'), "=D10", num)
    ws.write_formula(R(10), C('N'), "=E10", num)
    ws.write_formula(R(10), C('O'), "=F10", num)
    ws.write_formula(R(10), C('P'), "=M10+N10+O10", num)

    ws.write(R(11), C('B'), 'TOTAL', bold)
    ws.write_formula(R(11), C('C'), "=C9+C10", num_bold)
    ws.write_formula(R(11), C('D'), "=D9+D10", num_bold)
    ws.write_formula(R(11), C('E'), "=E9+E10", num_bold)
    ws.write_formula(R(11), C('F'), "=F9+F10", num_bold)
    ws.write(R(11), C('K'), 'TOTAL', bold)
    ws.write_formula(R(11), C('L'), "=L9+L10", num_bold)
    ws.write_formula(R(11), C('M'), "=M9+M10", num_bold)
    ws.write_formula(R(11), C('N'), "=N9+N10", num_bold)
    ws.write_formula(R(11), C('O'), "=O9+O10", num_bold)
    ws.write_formula(R(11), C('P'), "=P9+P10", num_bold)

    # --- Section 49 offset: IGST clears IGST liability first, remainder splits 50/50 CGST/SGST ---
    ws.write_formula(R(13), C('G'), "=H6-H18", num)
    ws.write_formula(R(13), C('H'), "=G13/2", num)

    ws.write(R(15), C('D'), 'GST3B SUMMARY', header)
    ws.write_row(R(16), C('H'), ['PAID THROUGH ITC'], bold)
    ws.write(R(16), C('K'), 'PAYABLE IN CASH', bold)
    ws.write_row(R(17), C('E'), ['SALES', 'RCM'], bold)
    ws.write_row(R(17), C('H'), ['IGST', 'CGST', 'SGST'], bold)

    ws.write(R(18), C('D'), 'IGST')
    ws.write_formula(R(18), C('E'), "=D9", num)
    ws.write_formula(R(18), C('F'), "=D10", num)
    ws.write_formula(R(18), C('H'), "=E18", num)
    ws.write_formula(R(18), C('K'), "=E18-H18-I18-J18+F18", num)

    ws.write(R(19), C('D'), 'CGST')
    ws.write_formula(R(19), C('E'), "=E9", num)
    ws.write_formula(R(19), C('F'), "=E10", num)
    ws.write_formula(R(19), C('H'), "=G13/2", num)
    ws.write_formula(R(19), C('I'), "=I6", num)
    ws.write_formula(R(19), C('K'), "=E19-H19-I19-J19+F19", num)

    ws.write(R(20), C('D'), 'SGST')
    ws.write_formula(R(20), C('E'), "=F9", num)
    ws.write_formula(R(20), C('F'), "=F10", num)
    ws.write_formula(R(20), C('H'), "=G13/2", num)
    ws.write_formula(R(20), C('J'), "=J5", num)
    ws.write_formula(R(20), C('K'), "=E20-H20-I20-J20+F20", num)

    ws.write_formula(R(21), C('E'), "=E20+E19+E18", num_bold)
    ws.write_formula(R(21), C('F'), "=F20+F19+F18", num_bold)
    ws.write_formula(R(21), C('H'), "=SUM(H18:H20)", num_bold)
    ws.write_formula(R(21), C('I'), "=SUM(I18:I20)", num_bold)
    ws.write_formula(R(21), C('J'), "=SUM(J18:J20)", num_bold)
    ws.write_formula(R(21), C('K'), "=SUM(K18:K20)", num_bold)

    ws.write_formula(R(22), C('E'), "=E21+F21", num_bold)
    ws.write_formula(R(22), C('G'), "=H21+I21+J21", num_bold)
    ws.write_formula(R(22), C('K'), "=K21-F21", red)

    # --- ITC AFTER FILING ---
    ws.write(R(24), C('G'), 'ITC AFTER FILING', header)
    ws.write_row(R(25), C('G'), ['PARTICULARS', 'IGST', 'CGST', 'SGST'], bold)
    ws.write(R(26), C('G'), 'AVAILABLE ITC INCLUDING CURRENT MONTH')
    ws.write_formula(R(26), C('H'), "=H5", num)
    ws.write_formula(R(26), C('I'), "=I5", num)
    ws.write_formula(R(26), C('J'), "=J5", num)
    ws.write(R(27), C('G'), 'UTILISED IN CURRENT MONTH')
    ws.write_formula(R(27), C('H'), "=H18+H19+H20", num)
    ws.write_formula(R(27), C('I'), "=I19", num)
    ws.write_formula(R(27), C('J'), "=J20", num)
    ws.write(R(28), C('G'), 'REMAINING ITC', bold)
    ws.write_formula(R(28), C('H'), "=H26-H27", green)
    ws.write_formula(R(28), C('I'), "=I26-I27", green)
    ws.write_formula(R(28), C('J'), "=J26-J27", green)

    # --- 3B JV ---
    ws.write(R(30), C('D'), f'3B JV FOR THE MONTH OF {period_label.upper()}', header)
    ws.write_row(R(31), C('D'), ['PARTICULARS'], bold)
    ws.write_row(R(31), C('I'), ['DEBIT', 'CREDIT'], bold)

    jv_rows = [
        (32, ACCOUNTS['igst_payable'], 'I', '=D9', None),
        (33, ACCOUNTS['cgst_payable'], 'I', '=E9', None),
        (34, ACCOUNTS['sgst_payable'], 'I', '=F9', None),
        (35, ACCOUNTS['igst_receivable'], 'J', '=H18', None),
        (36, ACCOUNTS['igst_receivable'], 'J', '=H19', None),
        (37, ACCOUNTS['igst_receivable'], 'J', '=H20', None),
        (38, ACCOUNTS['cgst_receivable'], 'J', '=I19', None),
        (39, ACCOUNTS['sgst_receivable'], 'J', '=J20', None),
        (40, ACCOUNTS['igst_payable'], 'I', '=F18', None),
        (41, ACCOUNTS['cgst_payable'], 'I', '=F19', None),
        (42, ACCOUNTS['sgst_payable'], 'I', '=F20', None),
        (43, ACCOUNTS['rcm_payable'], 'J', '=M10+N10+O10', None),
        (44, ACCOUNTS['igst_receivable'], 'I', '=M10', None),
        (45, ACCOUNTS['cgst_receivable'], 'I', '=N10', None),
        (46, ACCOUNTS['sgst_receivable'], 'I', '=O10', None),
        (47, ACCOUNTS['rcm_receivable'], 'J', '=P10', None),
        (48, ACCOUNTS['rcm_payable'], 'J', '=K22', None),
    ]
    for excel_row, account, col, formula, _ in jv_rows:
        ws.write(R(excel_row), C('D'), account)
        ws.write_formula(R(excel_row), C(col), formula, num)

    ws.write_formula(R(49), C('I'), "=SUM(I32:I48)", num_bold)
    ws.write_formula(R(49), C('J'), "=SUM(J32:J48)", num_bold)
    ws.write_formula(R(50), C('J'), "=J49-I49", bold)


# ==========================================
#  GSTR2B SUMMARY / GSTR1 SUMMARY sheets
# ==========================================

def write_gstr2b_summary_sheet(writer, buckets):
    wb = writer.book
    ws = wb.add_worksheet("GSTR2B SUMMARY")
    writer.sheets["GSTR2B SUMMARY"] = ws
    bold = wb.add_format({'bold': True})
    num = wb.add_format({'num_format': '#,##0.00'})
    num_bold = wb.add_format({'bold': True, 'num_format': '#,##0.00'})

    ws.set_column(0, 0, 55)
    ws.set_column(1, 4, 16)

    ws.write_row(0, 0, ['PARTICULARS', 'TAXABLE VALUE', 'IGST', 'CGST', 'SGST'], bold)

    rows = [
        ('CURRENT MONTH B2B PURCHASE CLAIMED', buckets['current_month_b2b']),
        ('PREVIOUS MONTH B2B PURCHASE REFLECTING IN THIS MONTH CLAIMED', buckets['previous_month_input']),
        ('CURRENT MONTH B2B CREDIT NOTE CLAIMED', buckets['credit_note']),
        ('CURRENT MONTH RCM BOOKS+PORTAL', buckets['rcm']),
    ]
    for i, (label, vals) in enumerate(rows):
        r = i + 1
        ws.write(r, 0, label)
        ws.write(r, 1, vals['taxable'], num)
        ws.write(r, 2, vals['igst'], num)
        ws.write(r, 3, vals['cgst'], num)
        ws.write(r, 4, vals['sgst'], num)

    ws.write(5, 0, 'FINAL ITC', bold)
    ws.write_formula(5, 1, "=B2+B3-B4+B5", num_bold)
    ws.write_formula(5, 2, "=C2+C3-C4+C5", num_bold)
    ws.write_formula(5, 3, "=D2+D3-D4+D5", num_bold)
    ws.write_formula(5, 4, "=E2+E3-E4+E5", num_bold)

    # Supporting detail beneath the summary (row positions here are free-form
    # -- nothing references them by fixed cell address).
    start = 9
    for label, key in [('CURRENT MONTH B2B PURCHASE CLAIMED', 'current_month_b2b'),
                        ('PREVIOUS MONTH B2B PURCHASE REFLECTING IN THIS MONTH CLAIMED', 'previous_month_input'),
                        ('CURRENT MONTH B2B CREDIT NOTE CLAIMED', 'credit_note'),
                        ('CURRENT MONTH RCM (BOOKS)', 'rcm')]:
        df = buckets['detail_rows'][key]
        if df is None or df.empty:
            continue
        ws.write(start, 0, label, bold)
        df.to_excel(writer, sheet_name="GSTR2B SUMMARY", index=False, startrow=start + 1)
        start = start + 1 + len(df) + 3

def write_gstr1_summary_sheet(writer, gstr1_buckets, gstr1_detail_df):
    wb = writer.book
    ws = wb.add_worksheet("GSTR1 SUMMARY")
    writer.sheets["GSTR1 SUMMARY"] = ws
    bold = wb.add_format({'bold': True})
    num = wb.add_format({'num_format': '#,##0.00'})
    num_bold = wb.add_format({'bold': True, 'num_format': '#,##0.00'})

    ws.set_column(0, 0, 16)
    ws.set_column(1, 4, 16)

    ws.write_row(0, 0, ['NATURE', 'TAXABLE VALUE', 'IGST', 'CGST', 'SGST'], bold)
    for i, cat in enumerate(GSTR1_CATEGORIES):
        r = i + 1
        vals = gstr1_buckets[cat]
        ws.write(r, 0, cat)
        ws.write(r, 1, vals['taxable'], num)
        ws.write(r, 2, vals['igst'], num)
        ws.write(r, 3, vals['cgst'], num)
        ws.write(r, 4, vals['sgst'], num)

    # TOTAL = B2B - B2B CDNR + B2C - B2C CDNR (credit notes reduce sales)
    ws.write(5, 0, 'TOTAL', bold)
    ws.write_formula(5, 1, "=B2-B3+B4-B5", num_bold)
    ws.write_formula(5, 2, "=C2-C3+C4-C5", num_bold)
    ws.write_formula(5, 3, "=D2-D3+D4-D5", num_bold)
    ws.write_formula(5, 4, "=E2-E3+E4-E5", num_bold)

    if gstr1_detail_df is not None and not gstr1_detail_df.empty:
        ws.write(8, 0, 'DETAIL', bold)
        gstr1_detail_df.to_excel(writer, sheet_name="GSTR1 SUMMARY", index=False, startrow=9)

def write_not_claimed_working_sheet(writer, period_label):
    """Blank template matching the firm's existing manually-maintained
    layout -- deliberately not auto-populated (see module docstring)."""
    wb = writer.book
    ws = wb.add_worksheet("NOT CLAIMED WORKING")
    writer.sheets["NOT CLAIMED WORKING"] = ws
    bold = wb.add_format({'bold': True})

    ws.write(0, 0, f'AS ON {period_label} (fill in manually)', bold)
    ws.write_row(1, 0, ['Date', 'Number', 'Vendor Name', 'Invoice Total', 'Taxable Value', 'IGST', 'CGST', 'SGST'], bold)
    ws.set_column(0, 7, 16)


# ==========================================
#  MAIN ENTRY POINT
# ==========================================

def generate_gstr3b_report(gstr1_file_paths, file_portal, odoo_files_dict,
                            owner_user_id, client_name, period, opening_itc_override=None,
                            manual_gstr1_buckets=None):
    """period: 'YYYY-MM'. Returns a BytesIO xlsx and updates this client's
    closing ITC balance for next period's opening ITC.

    manual_gstr1_buckets: when provided (dict keyed by GSTR1_CATEGORIES,
    each a {taxable, igst, cgst, sgst} dict of CA-entered totals), this
    skips ledger-file parsing entirely -- used while Odoo's GSTR-1 export
    format is unusable and that summary is prepared by hand."""
    output = BytesIO()

    if manual_gstr1_buckets is not None:
        gstr1_detail_df = None
        gstr1_buckets = build_manual_gstr1_buckets(manual_gstr1_buckets)
    else:
        gstr1_detail_df, gstr1_summary_df = compute_gstr1_data(gstr1_file_paths)
        gstr1_buckets = compute_gstr1_buckets(gstr1_summary_df)

    processed_portal, processed_books, reference_sheets = compute_reco_data(file_portal, odoo_files_dict, period)
    gstr2b_buckets = compute_gstr2b_buckets(processed_portal, processed_books)

    opening_itc = get_opening_itc(owner_user_id, client_name, period, opening_itc_override)

    year, month = (int(x) for x in period.split('-'))
    period_label = f"{MONTH_NAMES[month - 1]} {year}"

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        write_3b_summary_sheet(writer, opening_itc, period_label)
        write_gstr2b_summary_sheet(writer, gstr2b_buckets)
        write_gstr1_summary_sheet(writer, gstr1_buckets, gstr1_detail_df)
        write_not_claimed_working_sheet(writer, period_label)

        sorted_sheets = get_smart_sorted_order(processed_portal, processed_books)
        for sheet_title, df_final in sorted_sheets:
            add_formatting_and_subtotals(writer, df_final, sheet_title)

        for sheet_name, df in reference_sheets.items():
            title = f"{sheet_name} (Reference)"[:31]
            add_formatting_and_subtotals(writer, df, title)

    # Persist closing ITC so next period's opening ITC auto-fills instead of
    # needing manual re-entry.
    totals = compute_3b_totals(gstr1_buckets, gstr2b_buckets, opening_itc)
    save_closing_itc(owner_user_id, client_name, period, totals['remaining_itc'])

    output.seek(0)
    return output
