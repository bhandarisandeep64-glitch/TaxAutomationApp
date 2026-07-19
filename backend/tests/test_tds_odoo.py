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

from modules.direct_tax.tds_odoo import process_tds_odoo, _parse_label, _parse_account_new_section


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


def test_label_parsing_current_and_legacy_formats():
    """Odoo's real export format changed to "New {section} {rate}%" (e.g.
    real file: "New 194H 2%") -- the original parser assumed the reverse
    ("{rate}% {section}") and silently produced 'N/A' for every row on
    real data, since that format has no space after the trailing %."""
    assert _parse_label('New 194H 2%') == ('194H', 2.0)
    assert _parse_label('new 194c 1.5%') == ('194c', 1.5)  # case-insensitive
    # Legacy format still supported for older periods
    assert _parse_label('1% 194C') == ('194C', 1.0)
    # Unparseable label doesn't crash, just comes back unresolved
    assert _parse_label('garbage text')[0] == 'N/A'
    assert _parse_label(None)[0] == 'N/A'
    print("Label parsing (current + legacy formats): OK")


def test_account_new_section_takes_priority_over_table():
    """Odoo's own Account name (e.g. "112456 TDS 393(1)1(ii) - TDS ON
    COMMISSION/BROKERAGE - 1006") is the primary source for New
    Section/Code -- self-updating as the client's chart of accounts
    evolves -- and only falls back to the hardcoded table when the account
    name doesn't match this pattern."""
    new_sec, code = _parse_account_new_section(
        '112456 TDS 393(1)1(ii) - TDS ON COMMISSION/BROKERAGE - 1006'
    )
    assert new_sec == '393(1), Sl. 1(ii)', new_sec
    assert code == '1006'

    # Doesn't match the expected pattern -- caller should fall back to the table
    assert _parse_account_new_section('112456 Some Other Account') == (None, None)
    assert _parse_account_new_section(None) == (None, None)
    assert _parse_account_new_section('') == (None, None)
    print("Account-based New Section/Code extraction: OK")


def test_end_to_end_real_odoo_label_format_with_account_fallback():
    """Mirrors the real file's exact shape: current-format Label ("New 194H
    2%"), and a mix of one row whose Account carries the new code directly
    and one row whose Account doesn't (falls back to the shared table)."""
    tmpdir = tempfile.mkdtemp()
    out_dir = tempfile.mkdtemp()

    f = _write_odoo_file(tmpdir, 'odoo_new_format.xlsx', [
        # Account carries the new section/code directly -- primary source
        {'Partner': 'Rajiv Prakash Krishnani', 'PAN No.': 'AAACV4141L', 'Number': '26-27/06/116',
         'Journal': 'Vendor Bills', 'Label': 'New 194H 2%',
         'Account': '112456 TDS 393(1)1(ii) - TDS ON COMMISSION/BROKERAGE - 1006',
         'Taxable Amt.': 80127.56, 'Credit': 1602.56, 'Date': '2026-06-17'},
        # Account doesn't follow the pattern -- must fall back to the table
        # (194Q is a fixed mapping regardless of rate)
        {'Partner': 'Some Vendor Pvt Ltd', 'PAN No.': 'ABCPS1234C', 'Number': '26-27/06/200',
         'Journal': 'Vendor Bills', 'Label': 'New 194Q 0.1%',
         'Account': '112999 Some Unrelated Account Name',
         'Taxable Amt.': 500000, 'Credit': 500, 'Date': '2026-06-18'},
    ])

    result = process_tds_odoo([f], out_dir, 'Real Format Test')
    assert result['success'], result.get('error')

    out_path = os.path.join(out_dir, result['filename'])
    detail_df = pd.read_excel(out_path, sheet_name='TDS Working', header=0)

    row1 = detail_df[detail_df['Transaction#'] == '26-27/06/116'].iloc[0]
    assert row1['Old Section'] == '194H'
    assert row1['New Section'] == '393(1), Sl. 1(ii)'
    assert int(float(row1['Section Code'])) == 1006

    row2 = detail_df[detail_df['Transaction#'] == '26-27/06/200'].iloc[0]
    assert row2['Old Section'] == '194Q'
    assert row2['New Section'] == '393(1), Sl. 8(ii)'  # from the shared table, not Account
    assert int(float(row2['Section Code'])) == 1031

    print("End-to-end real Odoo label format + Account fallback: OK")


if __name__ == '__main__':
    test_end_to_end_report_structure()
    test_label_parsing_current_and_legacy_formats()
    test_account_new_section_takes_priority_over_table()
    test_end_to_end_real_odoo_label_format_with_account_fallback()
    print("ALL TESTS PASSED")
