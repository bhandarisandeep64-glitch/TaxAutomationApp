"""
Regression test for gstr2b_reco_engine.py.

No real GSTR-2B/Odoo sample files exist in this repo, so this builds fake
ones in-memory that match the column shapes the engine's cleaning functions
expect, and checks the specific matching bugs that were fixed:
  A) invoice-number spacing/punctuation no longer breaks an exact match
  B) a small rounding difference + differently-formatted invoice number is
     still caught by the fuzzy match (previously required a paisa-perfect
     amount match before fuzzy matching even ran)
  C) previous-period marking (when a reconciliation month is supplied)
  D) Section 16(4) time-barred ITC flag
  E) ITC-eligibility sheets are preserved (not dropped) but not
     double-counted into the main reconciliation / vendor summary

Run directly: python tests/test_gstr2b_reco_engine.py
(also pytest-discoverable once pytest is added to the project)
"""
import os
import sys
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd

from modules.indirect_tax.gstr2b_reco_engine import generate_reco_report


def _build_portal_file():
    b2b_cols = ['GSTIN of supplier', 'Trade/Legal name', 'Invoice number', 'Invoice Date',
                'Invoice Value (₹)', 'Place of supply', 'Supply Attract Reverse Charge', 'Rate (%)',
                'Taxable Value (₹)', 'Integrated Tax (₹)', 'Central Tax (₹)', 'State/UT Tax (₹)', 'Cess Amount (₹)']

    rows = [
        # A: spacing/punctuation difference, identical amount -> should Match via exact (normalized)
        ['27AAAAA0000A1Z5', 'Test Vendor A', 'INV-2025/001', '05-12-2025', 17700, 'Maharashtra', 'No', 18, 15000.00, 2700.00, 0, 0, 0],
        # B: differently-formatted invoice number + 40 paisa rounding diff -> should Match (Fuzzy)
        ['27BBBBB0000B1Z5', 'Test Vendor B', '0002-25', '10-12-2025', 23600, 'Maharashtra', 'No', 18, 20000.00, 3600.00, 0, 0, 0],
        # C1: previous-period, no books match at all -> "Previous Period Inv"
        ['27CCCCC0000C1Z5', 'Test Vendor C', 'OLD-001', '15-10-2025', 11800, 'Maharashtra', 'No', 18, 10000.00, 1800.00, 0, 0, 0],
        # C2: previous-period, WITH a books match -> "Match (Old Inv)"
        ['27DDDDD0000D1Z5', 'Test Vendor D', 'OLD-002', '20-10-2025', 5900, 'Maharashtra', 'No', 18, 5000.00, 900.00, 0, 0, 0],
        # D: time-barred (FY 2022-23 invoice, Section 16(4) deadline was 30-Nov-2023)
        ['27EEEEE0000E1Z5', 'Test Vendor E', 'TB-001', '10-05-2022', 5900, 'Maharashtra', 'No', 18, 5000.00, 900.00, 0, 0, 0],
        # filler rows so the sheet clears the "B2B" conditional row-count check (needs >6 rows)
        ['27FFFFF0000F1Z5', 'Filler Vendor 1', 'FILL-001', '02-12-2025', 1180, 'Maharashtra', 'No', 18, 1000.00, 180.00, 0, 0, 0],
        ['27FFFFF0000F1Z5', 'Filler Vendor 1', 'FILL-002', '03-12-2025', 1180, 'Maharashtra', 'No', 18, 1000.00, 180.00, 0, 0, 0],
        ['27FFFFF0000F1Z5', 'Filler Vendor 1', 'FILL-003', '04-12-2025', 1180, 'Maharashtra', 'No', 18, 1000.00, 180.00, 0, 0, 0],
    ]
    b2b_df = pd.DataFrame(rows, columns=b2b_cols)

    # ITC reference sheet -- same shape, should survive but not be reconciled
    itc_rows = [
        ['27AAAAA0000A1Z5', 'Test Vendor A', 'INV-2025/001', '05-12-2025', 17700, 'Maharashtra', 'No', 18, 15000.00, 2700.00, 0, 0, 0],
        ['27ZZZZZ0000Z1Z5', 'Blocked Vendor Z', 'BLK-001', '06-12-2025', 1180, 'Maharashtra', 'No', 18, 1000.00, 180.00, 0, 0, 0],
    ]
    itc_df = pd.DataFrame(itc_rows, columns=b2b_cols)

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        b2b_df.to_excel(writer, sheet_name='B2B', header=True, index=False)
        itc_df.to_excel(writer, sheet_name='ITC Available', header=True, index=False)
    buf.seek(0)
    return buf


def _build_odoo_reg_igst():
    cols = ['Account', 'Label', 'Date', 'Reference', 'Debit', 'Credit', 'Taxable Amt.']
    rows = [
        # A: matches portal's "INV-2025/001" but formatted with spaces instead of -/
        ['Input IGST 18%', 'Purchase - Test Vendor A', '05-12-2025', 'INV 2025 001', 2700.00, 0, 15000.00],
        # B: matches portal's "0002-25" but formatted as "Bill 0002/25", amount 40 paisa lower
        ['Input IGST 18%', 'Purchase - Test Vendor B', '10-12-2025', 'Bill 0002/25', 3599.93, 0, 19999.60],
        # C2: matches portal's OLD-002 exactly
        ['Input IGST 18%', 'Purchase - Test Vendor D', '20-10-2025', 'OLD-002', 900.00, 0, 5000.00],
        # filler matches (so these don't show up as false "Not on Portal")
        ['Input IGST 18%', 'Purchase - Filler 1', '02-12-2025', 'FILL-001', 180.00, 0, 1000.00],
        ['Input IGST 18%', 'Purchase - Filler 2', '03-12-2025', 'FILL-002', 180.00, 0, 1000.00],
        ['Input IGST 18%', 'Purchase - Filler 3', '04-12-2025', 'FILL-003', 180.00, 0, 1000.00],
    ]
    df = pd.DataFrame(rows, columns=cols)
    buf = BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return buf


def _get_row(df, inv):
    match = df[df['Invoice Number'] == inv]
    assert len(match) == 1, f"Expected exactly 1 row for invoice {inv!r}, found {len(match)}"
    return match.iloc[0]


def test_gstr2b_reco_engine():
    portal_file = _build_portal_file()
    odoo_files = {
        'odoo_reg_cgst': None,
        'odoo_reg_igst': _build_odoo_reg_igst(),
        'odoo_rcm_cgst': None,
        'odoo_rcm_igst': None,
    }

    output = generate_reco_report(portal_file, odoo_files, month_str="2025-12")
    all_sheets = pd.read_excel(output, sheet_name=None)

    b2b_portal = next((df for name, df in all_sheets.items() if name.startswith('B2B') and '(Portal)' in name), None)
    assert b2b_portal is not None, "Could not find the B2B (Portal) sheet in output"

    # A: spacing/punctuation difference should match via normalized exact match, not fuzzy
    a = _get_row(b2b_portal, 'INV-2025/001')
    assert a['Remarks'] == 'Match', f"Test A failed: got {a['Remarks']!r}"

    # B: reformatted invoice number + 40 paisa rounding difference should still fuzzy-match
    b = _get_row(b2b_portal, '0002-25')
    assert b['Remarks'] == 'Match (Fuzzy)', f"Test B failed: got {b['Remarks']!r}"

    # C1: previous-period invoice with no books match
    c1 = _get_row(b2b_portal, 'OLD-001')
    assert c1['Remarks'] == 'Previous Period Inv', f"Test C1 failed: got {c1['Remarks']!r}"

    # C2: previous-period invoice WITH a books match
    c2 = _get_row(b2b_portal, 'OLD-002')
    assert c2['Remarks'] == 'Match (Old Inv)', f"Test C2 failed: got {c2['Remarks']!r}"

    # D: Section 16(4) time-barred flag
    d = _get_row(b2b_portal, 'TB-001')
    assert str(d['ITC Time-Barred']).startswith('YES'), f"Test D failed: got {d['ITC Time-Barred']!r}"

    # E: ITC reference sheet preserved but not double-counted into reconciliation/summary
    ref_sheets = [n for n in all_sheets if 'ITC Available' in n]
    assert len(ref_sheets) == 1 and '(Reference)' in ref_sheets[0], f"Test E failed: {ref_sheets}"
    vendor_summary = all_sheets.get('Vendor Summary')
    assert vendor_summary is not None, "Vendor Summary sheet missing"
    blocked_vendor_rows = vendor_summary[vendor_summary['Vendor Name'] == 'Blocked Vendor Z']
    assert len(blocked_vendor_rows) == 0, "Test E failed: reference sheet data leaked into vendor summary"

    print("ALL TESTS PASSED")


if __name__ == '__main__':
    test_gstr2b_reco_engine()
