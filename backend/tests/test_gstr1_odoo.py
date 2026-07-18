"""
Tests for the rewritten gstr1_odoo.py (Odoo's current "HSN B2B" / "HSN B2C"
Journal Item export format, replacing the old per-tax-account ledger
export).

Two kinds of coverage:
  1. Synthetic fixtures exercising the specific behaviors confirmed against
     real data during development: credit notes detected via Debit (not via
     GSTR Section, since the real B2C file never tags CDNR that way),
     mixed-rate invoices (an invoice with both an 18% and a 5% line),
     IGST vs CGST/SGST routing, and the HSN-wise netting of credit notes.
  2. A real-data check against the two files the firm actually shared
     (skipped if either is missing or locked open in Excel -- this file
     lives on the CA's Desktop and gets opened for review often).

Run directly: python tests/test_gstr1_odoo.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd

from modules.indirect_tax.gstr1_odoo import compute_gstr1_data

B2B_SAMPLE_PATH = r"C:\Users\ASUS\OneDrive\Desktop\Journal Item (account.move.line) (15).xlsx"
B2C_SAMPLE_PATH = r"C:\Users\ASUS\OneDrive\Desktop\hsn b2c file.xlsx"


def _approx(a, b, tol=0.02):
    return abs(a - b) <= tol


def _write(df, tmpdir, name):
    fp = os.path.join(tmpdir, name)
    df.to_excel(fp, index=False)
    return fp


def test_b2b_regular_and_cdnr_with_mixed_rates():
    """One invoice with two lines at different rates (18% and 5%) -- tax
    must be computed per line and summed, not one rate applied to the
    invoice total. One CDNR row (Debit populated) in the same file."""
    tmpdir = tempfile.mkdtemp()
    df = pd.DataFrame([
        {'GSTR Section': 'B2B Regular', 'Partner': 'Arch Decor', 'GSTIN': '27AACPS9617D1ZK',
         'Date': '2026-06-30', 'HSN/SAC Code': 44123190, 'Number': 'INV-001',
         'Taxes': '18% GST S', 'Taxable Amt.': 15000.0, 'Credit': 10000.0, 'Debit': 0.0},
        {'GSTR Section': 'B2B Regular', 'Partner': 'Arch Decor', 'GSTIN': '27AACPS9617D1ZK',
         'Date': '2026-06-30', 'HSN/SAC Code': 39219029, 'Number': 'INV-001',
         'Taxes': '5% GST S', 'Taxable Amt.': 15000.0, 'Credit': 5000.0, 'Debit': 0.0},
        {'GSTR Section': 'CDNR Regular', 'Partner': 'Unnati Traders', 'GSTIN': '27BEKPR4715N1ZU',
         'Date': '2026-06-30', 'HSN/SAC Code': 48239019, 'Number': 'CN-001',
         'Taxes': '18% GST S', 'Taxable Amt.': 2000.0, 'Credit': 0.0, 'Debit': 2000.0},
    ])
    fp = _write(df, tmpdir, 'b2b.xlsx')

    final_df, summary, hsn_summary_df = compute_gstr1_data({'file_b2b': fp})

    inv = final_df[final_df['Number'] == 'INV-001'].iloc[0]
    assert _approx(inv['Taxable Amt.'], 15000.0)
    # 18% on 10000 = 1800 (900 CGST + 900 SGST); 5% on 5000 = 250 (125 + 125)
    assert _approx(inv['CGST'], 1025.0), inv['CGST']
    assert _approx(inv['SGST'], 1025.0), inv['SGST']
    assert _approx(inv['IGST'], 0.0)
    assert inv['Nature'] == 'B2B'

    cn = final_df[final_df['Number'] == 'CN-001'].iloc[0]
    assert cn['Nature'] == 'B2B CDNR'
    assert _approx(cn['Taxable Amt.'], 2000.0)
    assert _approx(cn['CGST'], 180.0) and _approx(cn['SGST'], 180.0)

    cat = summary.set_index('Category')
    assert _approx(cat.loc['B2B', 'Taxable'], 15000.0)
    assert _approx(cat.loc['B2B CDNR', 'Taxable'], 2000.0)  # positive magnitude, not negative

    print("B2B regular + mixed-rate invoice + CDNR: OK")


def test_b2c_credit_note_detected_without_gstr_section_tag():
    """Real B2C exports tag every row (including credit notes) as 'B2CS' --
    credit-note detection has to come from Debit being populated instead."""
    tmpdir = tempfile.mkdtemp()
    df = pd.DataFrame([
        {'GSTR Section': 'B2CS', 'Partner': 'Walk-in Customer', 'GSTIN': None,
         'Date': '2026-06-30', 'HSN/SAC Code': 48239019, 'Number': 'B2C-001',
         'Taxes': '18% GST S', 'Taxable Amt.': 1000.0, 'Credit': 1000.0, 'Debit': 0.0},
        {'GSTR Section': 'B2CS', 'Partner': 'Walk-in Customer', 'GSTIN': None,
         'Date': '2026-06-29', 'HSN/SAC Code': 48239019, 'Number': 'B2C-CN-001',
         'Taxes': '18% GST S', 'Taxable Amt.': 200.0, 'Credit': 0.0, 'Debit': 200.0},
    ])
    fp = _write(df, tmpdir, 'b2c.xlsx')

    final_df, summary, _ = compute_gstr1_data({'file_b2c': fp})

    regular = final_df[final_df['Number'] == 'B2C-001'].iloc[0]
    cn = final_df[final_df['Number'] == 'B2C-CN-001'].iloc[0]
    assert regular['Nature'] == 'B2C'
    assert cn['Nature'] == 'B2C CDNR'
    assert _approx(cn['Taxable Amt.'], 200.0)

    print("B2C credit-note detection via Debit column (no GSTR Section tag): OK")


def test_igst_vs_intrastate_split():
    tmpdir = tempfile.mkdtemp()
    df = pd.DataFrame([
        {'GSTR Section': 'B2B Regular', 'Partner': 'V-Can Furnitech', 'GSTIN': '24AADCV0508Q1Z6',
         'Date': '2026-06-30', 'HSN/SAC Code': 48239019, 'Number': 'INV-IGST-001',
         'Taxes': '18% IGST S', 'Taxable Amt.': 4365.0, 'Credit': 4365.0, 'Debit': 0.0},
    ])
    fp = _write(df, tmpdir, 'b2b_igst.xlsx')
    final_df, _, _ = compute_gstr1_data({'file_b2b': fp})
    row = final_df.iloc[0]
    assert _approx(row['IGST'], 785.7), row['IGST']  # 4365 * 18%
    assert _approx(row['CGST'], 0.0) and _approx(row['SGST'], 0.0)
    print("IGST routing: OK")


def test_hsn_summary_nets_credit_notes():
    tmpdir = tempfile.mkdtemp()
    df = pd.DataFrame([
        {'GSTR Section': 'B2B Regular', 'Partner': 'A', 'GSTIN': '27AAAAA0000A1Z5',
         'Date': '2026-06-30', 'HSN/SAC Code': 48239019, 'Number': 'INV-001',
         'Taxes': '18% GST S', 'Taxable Amt.': 1000.0, 'Credit': 1000.0, 'Debit': 0.0},
        {'GSTR Section': 'CDNR Regular', 'Partner': 'A', 'GSTIN': '27AAAAA0000A1Z5',
         'Date': '2026-06-30', 'HSN/SAC Code': 48239019, 'Number': 'CN-001',
         'Taxes': '18% GST S', 'Taxable Amt.': 400.0, 'Credit': 0.0, 'Debit': 400.0},
    ])
    fp = _write(df, tmpdir, 'b2b_hsn.xlsx')
    _, _, hsn_summary_df = compute_gstr1_data({'file_b2b': fp})
    row = hsn_summary_df[hsn_summary_df['HSN/SAC Code'] == 48239019].iloc[0]
    assert _approx(row['Taxable Value'], 600.0), row['Taxable Value']  # 1000 - 400, netted
    print("HSN summary nets credit notes: OK")


def test_real_hsn_b2b_b2c_files():
    """Real-data check against the actual files the firm shared. Skipped if
    either file is missing, or locked (a common state for a file living on
    the CA's own Desktop that gets opened for review)."""
    for path in (B2B_SAMPLE_PATH, B2C_SAMPLE_PATH):
        if not os.path.exists(path):
            print(f"SKIPPED (sample file not present at {path})")
            return

    try:
        final_df, summary, hsn_summary_df = compute_gstr1_data({
            'file_b2b': B2B_SAMPLE_PATH, 'file_b2c': B2C_SAMPLE_PATH,
        })
    except PermissionError:
        print("SKIPPED (sample file is currently open/locked elsewhere)")
        return

    # Arch Decor invoice 26-27/04760: Taxable Amt 104261.88, rate 18% GST S
    row = final_df[final_df['Number'] == '26-27/04760']
    assert not row.empty, "Arch Decor invoice not found in real B2B file"
    row = row.iloc[0]
    assert _approx(row['Taxable Amt.'], 104261.88, tol=1.0), row['Taxable Amt.']
    expected_total_tax = round(104261.88 * 0.18, 2)
    assert _approx(row['CGST'] + row['SGST'], expected_total_tax, tol=1.0), (row['CGST'], row['SGST'])
    assert _approx(row['IGST'], 0.0)

    # V-Can Furnitech invoice 26-27/04729: GSTIN prefix 24 (interstate), IGST
    row = final_df[final_df['Number'] == '26-27/04729']
    assert not row.empty, "V-Can Furnitech invoice not found in real B2B file"
    row = row.iloc[0]
    assert row['IGST'] > 0 and _approx(row['CGST'], 0.0) and _approx(row['SGST'], 0.0)

    cat = summary.set_index('Category')
    for c in ['B2B', 'B2B CDNR', 'B2C', 'B2C CDNR']:
        assert c in cat.index

    assert not hsn_summary_df.empty

    print("Real HSN B2B/B2C files: Arch Decor + V-Can Furnitech invoices match expected tax computation")


if __name__ == '__main__':
    test_b2b_regular_and_cdnr_with_mixed_rates()
    test_b2c_credit_note_detected_without_gstr_section_tag()
    test_igst_vs_intrastate_split()
    test_hsn_summary_nets_credit_notes()
    test_real_hsn_b2b_b2c_files()
    print("ALL TESTS PASSED")
