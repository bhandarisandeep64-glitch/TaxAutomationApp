"""
Tests for tds_zoho.py's Income Tax Act 2025 section mapping and the
restructured TDS Working output (Old Section/New Section/Section Code,
no blank Challan columns, new Vendor Summary sheet).

Run directly: python tests/test_tds_zoho.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd

from modules.direct_tax.tds_zoho import process_tds_zoho, _lookup_new_section


def _approx(a, b, tol=0.5):
    return abs(a - b) <= tol


def _write_section_file(tmpdir, section_name, rows):
    """rows: list of dicts with Transaction#, Date, Vendor, PAN, Transaction
    Type, Total, Tax Deducted at Source, Rate at which deducted."""
    df = pd.DataFrame(rows)
    fp = os.path.join(tmpdir, f"{section_name}.xlsx")
    df.to_excel(fp, index=False)
    return fp


def test_section_lookup_mapping():
    # Rate-disambiguated sections
    assert _lookup_new_section('194C', 1.0) == ('393(1), Sl. 6(i).D(a)', '1023')
    assert _lookup_new_section('194C', 2.0) == ('393(1), Sl. 6(i).D(b)', '1024')
    assert _lookup_new_section('194J', 2.0) == ('393(1), Sl. 6(iii).D(a)', '1026')
    # 194J at 10% always codes to Professional Services (1027), never 1028
    assert _lookup_new_section('194J', 10.0) == ('393(1), Sl. 6(iii).D(b)', '1027')

    # Fixed-mapping sections, regardless of rate
    assert _lookup_new_section('194Q', 0.1) == ('393(1), Sl. 8(ii)', '1031')
    assert _lookup_new_section('194P', 5.0) == ('393(1), Sl. 8(iii)', '1032')
    assert _lookup_new_section('194', 10.0) == ('393(1), Sl. 7', '1029')
    assert _lookup_new_section('194H', 5.0) == ('393(1), Sl. 1(ii)', '1006')
    assert _lookup_new_section('194T', 10.0) == ('393(3), Sl. 7', '1067')

    # Out-of-scope sections (194R, 194S) are deliberately unmapped
    assert _lookup_new_section('194R', 10.0) == ('', '')
    assert _lookup_new_section('194S', 1.0) == ('', '')

    # Case-insensitivity on the section label
    assert _lookup_new_section('194c', 1.0) == ('393(1), Sl. 6(i).D(a)', '1023')

    print("Section lookup mapping: OK")


def test_end_to_end_report_structure():
    tmpdir = tempfile.mkdtemp()
    out_dir = tempfile.mkdtemp()

    f_194c = _write_section_file(tmpdir, '194C', [
        {'Transaction#': 'T1', 'Date': '2026-06-05', 'Vendor': 'Alpha Contractors',
         'PAN': 'ABCPA1234P', 'Transaction Type': 'Bill', 'Total': 100000,
         'Tax Deducted at Source': 1000, 'Rate at which deducted': 1},   # Individual/HUF -> 1023
        {'Transaction#': 'T2', 'Date': '2026-06-06', 'Vendor': 'Beta Builders Pvt Ltd',
         'PAN': 'ABCPB5678C', 'Transaction Type': 'Bill', 'Total': 200000,
         'Tax Deducted at Source': 4000, 'Rate at which deducted': 2},   # Others -> 1024
    ])
    f_194j = _write_section_file(tmpdir, '194J', [
        {'Transaction#': 'T3', 'Date': '2026-06-10', 'Vendor': 'Alpha Contractors',
         'PAN': 'ABCPA1234P', 'Transaction Type': 'Professional Fees', 'Total': 50000,
         'Tax Deducted at Source': 5000, 'Rate at which deducted': 10},  # -> 1027
    ])
    f_194r = _write_section_file(tmpdir, '194R', [
        {'Transaction#': 'T4', 'Date': '2026-06-12', 'Vendor': 'Gamma Traders',
         'PAN': 'ABCPG9012C', 'Transaction Type': 'Perquisite', 'Total': 10000,
         'Tax Deducted at Source': 1000, 'Rate at which deducted': 10},  # unmapped -> blank
    ])

    result = process_tds_zoho([f_194c, f_194j, f_194r], out_dir, 'Test Client')
    assert result['success'], result.get('error')

    out_path = os.path.join(out_dir, result['filename'])
    detail_df = pd.read_excel(out_path, sheet_name='TDS Working', header=0)

    # No blank Challan columns anywhere in the detail sheet
    for col in ['Challan No.', 'Challan Date', 'BSR Code', 'Challan Amount', 'Paid Interest', 'Challan Total Amount']:
        assert col not in detail_df.columns, f"{col} should have been removed"

    # Old Section / New Section / Section Code present and correctly mapped
    # (numeric-looking codes round-trip through Excel as floats, hence the
    # int() coercion -- the underlying report value is correct either way)
    row_194c_1 = detail_df[detail_df['Transaction#'] == 'T1'].iloc[0]
    assert row_194c_1['Old Section'] == '194C'
    assert row_194c_1['New Section'] == '393(1), Sl. 6(i).D(a)'
    assert int(float(row_194c_1['Section Code'])) == 1023

    row_194c_2 = detail_df[detail_df['Transaction#'] == 'T2'].iloc[0]
    assert int(float(row_194c_2['Section Code'])) == 1024

    row_194j = detail_df[detail_df['Transaction#'] == 'T3'].iloc[0]
    assert int(float(row_194j['Section Code'])) == 1027

    row_194r = detail_df[detail_df['Transaction#'] == 'T4'].iloc[0]
    assert row_194r['Old Section'] == '194R'
    assert pd.isna(row_194r['New Section']) or row_194r['New Section'] == ''
    assert pd.isna(row_194r['Section Code']) or row_194r['Section Code'] == ''

    # Vendor Summary sheet: Alpha Contractors appears in both 194C and 194J,
    # so its totals must be combined across sections.
    vendor_df = pd.read_excel(out_path, sheet_name='Vendor Summary', header=0)
    assert list(vendor_df.columns) == ['Vendor Name', 'Total Taxable Value', 'Total TDS']
    alpha = vendor_df[vendor_df['Vendor Name'] == 'Alpha Contractors'].iloc[0]
    assert _approx(alpha['Total Taxable Value'], 150000.0), alpha['Total Taxable Value']  # 100000 + 50000
    assert _approx(alpha['Total TDS'], 6000.0), alpha['Total TDS']  # 1000 + 5000

    beta = vendor_df[vendor_df['Vendor Name'] == 'Beta Builders Pvt Ltd'].iloc[0]
    assert _approx(beta['Total Taxable Value'], 200000.0)
    assert _approx(beta['Total TDS'], 4000.0)

    print("End-to-end TDS Zoho report structure: OK")


if __name__ == '__main__':
    test_section_lookup_mapping()
    test_end_to_end_report_structure()
    print("ALL TESTS PASSED")
