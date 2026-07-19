"""
Regression test for the GSTR-9 three-way reconciliation engine.

Builds synthetic Books / 2B-8A / 3B sheets in the firm's prepared layout,
covering every classification bucket in the matrix plus both amendment
flavours (full negation and partial revision) and the control-total
tie-out. No real client files needed.

Run directly: python tests/test_gstr9_reco_engine.py
"""
import os
import sys
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd

from modules.gstr9.gstr9_reco_engine import process_gstr9_reco, _load_sheet, _resolve_amendments, _tax_total

COLUMNS = ['Nature', 'GSTIN', 'Vendor Name', 'Document No.', 'Document type', 'Invoice date',
           'Invoice Value(₹)', 'Place Of Supply', 'Reverse Charge', 'Taxable Value',
           'Integrated Tax(₹)', 'Central Tax(₹)', 'State/UT Tax(₹)', 'ITC Availability']


def _row(nature, gstin, vendor, docno, taxable, igst, cgst, sgst, dtype='Regular'):
    return [nature, gstin, vendor, docno, dtype, '15/06/2025', taxable + igst + cgst + sgst,
            'Maharashtra', 'No', taxable, igst, cgst, sgst, 'Yes']


def _make_sheet(rows, add_total=True):
    data = [COLUMNS] + rows
    if add_total:
        # Grand-total row: blank Nature/GSTIN, only amount columns filled.
        tot_taxable = sum(r[9] for r in rows)
        tot_i = sum(r[10] for r in rows)
        tot_c = sum(r[11] for r in rows)
        tot_s = sum(r[12] for r in rows)
        data.append([None, None, None, None, None, None, None, None, None,
                     tot_taxable, tot_i, tot_c, tot_s, None])
    buf = BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        df.to_excel(w, sheet_name='B2B', header=False, index=False)
    buf.seek(0)
    return buf


# GSTINs for distinct scenarios
G = {
    'reconciled': '27AAAAA1111A1Z5',
    'amt_3b':     '27BBBBB2222B1Z5',
    'not_claimed':'27CCCCC3333C1Z5',
    'not_in_2b':  '27DDDDD4444D1Z5',
    'not_books':  '27EEEEE5555E1Z5',
    'books_only': '27FFFFF6666F1Z5',
    '2b_only':    '27GGGGG7777G1Z5',
    'claimed_only':'27HHHHH8888H1Z5',
    'amend_neg':  '27IIIII9999I1Z5',
    'amend_part': '27JJJJJ0000J1Z5',
}


def _build_files():
    # Each scenario: (books row?, 2b row?, 3b row?)
    books, portal, filed = [], [], []

    # 1. Reconciled -- present & equal in all three
    books.append(_row('B2B INVOICES', G['reconciled'], 'Recon Co', 'INV-1', 1000, 180, 0, 0))
    portal.append(_row('B2B INVOICES', G['reconciled'], 'Recon Co', 'INV-1', 1000, 180, 0, 0))
    filed.append(_row('B2B INVOICES', G['reconciled'], 'Recon Co', 'INV-1', 1000, 180, 0, 0))

    # 2. Books & 2B agree, 3B differs (over-claimed in 3B)
    books.append(_row('B2B INVOICES', G['amt_3b'], 'Amt Co', 'INV-2', 1000, 100, 0, 0))
    portal.append(_row('B2B INVOICES', G['amt_3b'], 'Amt Co', 'INV-2', 1000, 100, 0, 0))
    filed.append(_row('B2B INVOICES', G['amt_3b'], 'Amt Co', 'INV-2', 1000, 150, 0, 0))

    # 3. Eligible but not claimed in 3B (books + 2b, no 3b)
    books.append(_row('B2B INVOICES', G['not_claimed'], 'NotClaim Co', 'INV-3', 1000, 90, 0, 0))
    portal.append(_row('B2B INVOICES', G['not_claimed'], 'NotClaim Co', 'INV-3', 1000, 90, 0, 0))

    # 4. Claimed & booked, NOT in 2B (books + 3b, no 2b) -- HIGH risk
    books.append(_row('B2B INVOICES', G['not_in_2b'], 'No2B Co', 'INV-4', 1000, 200, 0, 0))
    filed.append(_row('B2B INVOICES', G['not_in_2b'], 'No2B Co', 'INV-4', 1000, 200, 0, 0))

    # 5. Claimed & in 2B, not in books (2b + 3b, no books)
    portal.append(_row('B2B INVOICES', G['not_books'], 'NoBooks Co', 'INV-5', 1000, 120, 0, 0))
    filed.append(_row('B2B INVOICES', G['not_books'], 'NoBooks Co', 'INV-5', 1000, 120, 0, 0))

    # 6. In books only
    books.append(_row('B2B INVOICES', G['books_only'], 'BooksOnly Co', 'INV-6', 1000, 50, 0, 0))

    # 7. In 2B only
    portal.append(_row('B2B INVOICES', G['2b_only'], '2BOnly Co', 'INV-7', 1000, 60, 0, 0))

    # 8. Claimed only -- no 2b, no books -- HIGH risk
    filed.append(_row('B2B INVOICES', G['claimed_only'], 'ClaimedOnly Co', 'INV-8', 1000, 70, 0, 0))

    # 9. Amendment (full negation): original in 2B 100, amended to 0.
    #    Books & 3B still show the original 100 -> after amendment, 2B=0,
    #    so this becomes "Books & 3B agree, 2B differs".
    books.append(_row('B2B INVOICES', G['amend_neg'], 'AmendNeg Co', '200', 1000, 100, 0, 0))
    portal.append(_row('B2B INVOICES', G['amend_neg'], 'AmendNeg Co', '200', 1000, 100, 0, 0))
    portal.append(_row('Amendment', G['amend_neg'], 'AmendNeg Co', '200-a', 0, 0, 0, 0))
    filed.append(_row('B2B INVOICES', G['amend_neg'], 'AmendNeg Co', '200', 1000, 100, 0, 0))

    # 10. Amendment (partial): original in 2B 100, amended to 50.
    #     Books & 3B show 100 -> after amendment 2B=50 -> "Books & 3B agree,
    #     2B differs".
    books.append(_row('B2B INVOICES', G['amend_part'], 'AmendPart Co', '300', 1000, 100, 0, 0))
    portal.append(_row('B2B INVOICES', G['amend_part'], 'AmendPart Co', '300', 1000, 100, 0, 0))
    portal.append(_row('Amendment', G['amend_part'], 'AmendPart Co', '300-a', 500, 50, 0, 0))
    filed.append(_row('B2B INVOICES', G['amend_part'], 'AmendPart Co', '300', 1000, 100, 0, 0))

    return _make_sheet(books), _make_sheet(portal), _make_sheet(filed)


def test_amendment_resolution():
    """Amendments REPLACE the base bill's 2B value and net under the base
    document number so they line up with Books/3B."""
    _, portal_file, _ = _build_files()
    portal_rows = _load_sheet(portal_file)
    resolved = _resolve_amendments(portal_rows)

    # Full negation: base '200' should now be 0 ITC, not 100.
    neg = resolved.get((G['amend_neg'], '200'))
    assert neg is not None, "Amended base bill 200 missing"
    assert abs(_tax_total(neg)) < 0.01, f"Full-negation amendment not applied: {_tax_total(neg)}"

    # Partial: base '300' should now be 50 ITC (replaced 100).
    part = resolved.get((G['amend_part'], '300'))
    assert part is not None, "Amended base bill 300 missing"
    assert abs(_tax_total(part) - 50.0) < 0.01, f"Partial amendment not applied: {_tax_total(part)}"

    # No stray '200a'/'300a' keys left dangling.
    assert (G['amend_neg'], '200a') not in resolved, "Stray amendment key 200a survived"
    assert (G['amend_part'], '300a') not in resolved, "Stray amendment key 300a survived"

    print("Amendment resolution (full negation + partial): OK")


def test_grand_total_row_excluded():
    books_file, _, _ = _build_files()
    rows = _load_sheet(books_file)
    # No row should have a blank GSTIN and blank docno (the total row).
    assert all(r['gstin'] or r['docno_clean'] for r in rows), "Grand-total row was not excluded"
    print("Grand-total row excluded: OK")


def test_all_categories_present():
    books_file, portal_file, filed_file = _build_files()
    output = process_gstr9_reco(books_file, portal_file, filed_file)
    sheets = pd.read_excel(output, sheet_name=None)

    assert 'Summary' in sheets
    assert 'Full Reconciliation' in sheets

    full = sheets['Full Reconciliation']
    # drop the TOTAL row (blank GSTIN)
    full = full[full['GSTIN'].notna() & (full['GSTIN'].astype(str).str.strip() != '')]

    def status_for(gstin):
        m = full[full['GSTIN'] == gstin]
        assert len(m) == 1, f"Expected 1 row for {gstin}, got {len(m)}"
        return m.iloc[0]['Status']

    assert 'Reconciled' in status_for(G['reconciled'])
    assert '3B differs' in status_for(G['amt_3b'])
    assert 'not claimed in 3B' in status_for(G['not_claimed'])
    assert 'NOT in 2B' in status_for(G['not_in_2b'])
    assert 'not in books' in status_for(G['not_books'])
    assert 'books only' in status_for(G['books_only'])
    assert '2B only' in status_for(G['2b_only'])
    assert 'Claimed only' in status_for(G['claimed_only'])
    # both amendment scenarios collapse to "Books & 3B agree, 2B differs"
    assert '2B differs' in status_for(G['amend_neg'])
    assert '2B differs' in status_for(G['amend_part'])

    print("All eight categories + amendment outcomes classified correctly: OK")


def test_control_total_tie_out():
    books_file, portal_file, filed_file = _build_files()
    # Books ITC total: 180+100+90+200+50+100+100 = 820
    controls = {
        'books':  {'igst': 820.0, 'cgst': 0, 'sgst': 0},
        'portal': {'igst': 999.0, 'cgst': 0, 'sgst': 0},   # deliberately wrong
        'filed':  {'igst': 0, 'cgst': 0, 'sgst': 0},        # provided but 0
    }
    output = process_gstr9_reco(books_file, portal_file, filed_file, control_totals=controls)
    summary = pd.read_excel(output, sheet_name='Summary', header=None)
    text = summary.astype(str).values.flatten()
    joined = ' '.join(text)
    assert 'Tied out' in joined, "Correct control total did not tie out"
    assert 'MISMATCH' in joined, "Wrong control total was not flagged"
    print("Control-total tie-out (correct ties, wrong flagged): OK")


if __name__ == '__main__':
    test_grand_total_row_excluded()
    test_amendment_resolution()
    test_all_categories_present()
    test_control_total_tie_out()
    print("ALL TESTS PASSED")
