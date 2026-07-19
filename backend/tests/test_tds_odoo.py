"""
Tests for tds_odoo.py's Income Tax Act 2025 section mapping and the
restructured TDS Working output (Old Section/New Section/Section Code,
no blank Challan columns, new Vendor Summary sheet).

Unlike Zoho (one file = one section, from the filename), Odoo's ledger
export carries both the rate and the old section as text inside a single
"Label" column per row (e.g. "2% 194C") -- so these fixtures build that
shape directly rather than relying on filenames.

Run directly: python tests/test_tds_odoo.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd

from modules.direct_tax.tds_odoo import process_tds_odoo


def _approx(a, b, tol=0.5):
    return abs(a - b) <= tol


def _write_odoo_file(tmpdir, name, rows):
    """rows: list of dicts with Partner, PAN No., Number, Journal, Label,
    Taxable Amt., Credit, Date."""
    df = pd.DataFrame(rows)
    fp = os.path.join(tmpdir, name)
    df.to_excel(fp, index=False)
    return fp


def test_end_to_end_report_structure():
    tmpdir = tempfile.mkdtemp()
    out_dir = tempfile.mkdtemp()

    f = _write_odoo_file(tmpdir, 'odoo_tds.xlsx', [
        # 194C, Individual/HUF (1%) -> 1023
        {'Partner': 'Alpha Contractors', 'PAN No.': 'ABCPA1234P', 'Number': 'INV1',
         'Journal': 'Vendor Bills', 'Label': '1% 194C', 'Taxable Amt.': 100000,
         'Credit': 1000, 'Date': '2026-06-05'},
        # 194C, Others (2%) -> 1024
        {'Partner': 'Beta Builders Pvt Ltd', 'PAN No.': 'ABCPB5678C', 'Number': 'INV2',
         'Journal': 'Vendor Bills', 'Label': '2% 194C', 'Taxable Amt.': 200000,
         'Credit': 4000, 'Date': '2026-06-06'},
        # 194J professional services (10%) -> 1027, same vendor as INV1
        {'Partner': 'Alpha Contractors', 'PAN No.': 'ABCPA1234P', 'Number': 'INV3',
         'Journal': 'Vendor Bills', 'Label': '10% 194J', 'Taxable Amt.': 50000,
         'Credit': 5000, 'Date': '2026-06-10'},
        # 194R -- deliberately unmapped
        {'Partner': 'Gamma Traders', 'PAN No.': 'ABCPG9012C', 'Number': 'INV4',
         'Journal': 'Vendor Bills', 'Label': '10% 194R', 'Taxable Amt.': 10000,
         'Credit': 1000, 'Date': '2026-06-12'},
    ])

    result = process_tds_odoo([f], out_dir, 'Test Odoo Client')
    assert result['success'], result.get('error')

    out_path = os.path.join(out_dir, result['filename'])
    detail_df = pd.read_excel(out_path, sheet_name='TDS Working', header=0)

    # No blank Challan columns anywhere in the detail sheet
    for col in ['Challan No.', 'Challan Date', 'BSR Code', 'Challan Amount', 'Paid Interest', 'Challan Total Amount']:
        assert col not in detail_df.columns, f"{col} should have been removed"

    row1 = detail_df[detail_df['Transaction#'] == 'INV1'].iloc[0]
    assert row1['Old Section'] == '194C'
    assert row1['New Section'] == '393(1), Sl. 6(i).D(a)'
    assert int(float(row1['Section Code'])) == 1023

    row2 = detail_df[detail_df['Transaction#'] == 'INV2'].iloc[0]
    assert int(float(row2['Section Code'])) == 1024

    row3 = detail_df[detail_df['Transaction#'] == 'INV3'].iloc[0]
    assert int(float(row3['Section Code'])) == 1027

    row4 = detail_df[detail_df['Transaction#'] == 'INV4'].iloc[0]
    assert row4['Old Section'] == '194R'
    assert pd.isna(row4['New Section']) or row4['New Section'] == ''
    assert pd.isna(row4['Section Code']) or row4['Section Code'] == ''

    # Vendor Summary: Alpha Contractors appears in both 194C and 194J rows
    vendor_df = pd.read_excel(out_path, sheet_name='Vendor Summary', header=0)
    assert list(vendor_df.columns) == ['Vendor Name', 'Total Taxable Value', 'Total TDS']
    alpha = vendor_df[vendor_df['Vendor Name'] == 'Alpha Contractors'].iloc[0]
    assert _approx(alpha['Total Taxable Value'], 150000.0), alpha['Total Taxable Value']  # 100000 + 50000
    assert _approx(alpha['Total TDS'], 6000.0), alpha['Total TDS']  # 1000 + 5000

    beta = vendor_df[vendor_df['Vendor Name'] == 'Beta Builders Pvt Ltd'].iloc[0]
    assert _approx(beta['Total Taxable Value'], 200000.0)
    assert _approx(beta['Total TDS'], 4000.0)

    print("End-to-end TDS Odoo report structure: OK")


if __name__ == '__main__':
    test_end_to_end_report_structure()
    print("ALL TESTS PASSED")
