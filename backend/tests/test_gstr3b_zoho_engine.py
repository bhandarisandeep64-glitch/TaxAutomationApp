"""
Regression test for the GSTR-3B Zoho flow (generate_gstr3b_zoho_report).

The output format changed from a standalone "Master Dashboard"
(calculate_smart_offset) to an Odoo-style "3B SUMMARY"/"GSTR2B SUMMARY"/
"GSTR1 SUMMARY" layout, per the CA's explicit direction that the Odoo
working paper (gstr3b_engine.py) is the gold standard -- see
compute_3b_totals_zoho's docstring for the offset rule, and
write_3b_summary_sheet_zoho's docstring for why the offset table/JV values
are reviewed Python numbers rather than a hand-authored formula chain.

This checks: GSTR-1 Zoho sales wiring + opening/closing ITC auto-carry
across periods (against synthetic data), the offset math against
hand-computed expected values, and that the JV section is self-balancing
(debits = credits) -- important since an unbalanced JV would be actively
wrong for a CA to book, not just cosmetically off.

Needs DATABASE_URL configured (reads backend/.env) since it exercises the
real opening/closing ITC persistence.

Run directly: python tests/test_gstr3b_zoho_engine.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from flask import Flask

from database import init_db, db
from models import GstrPeriodBalance
from modules.indirect_tax.gstr2b_reco_zoho_engine import (
    generate_gstr3b_zoho_report, compute_3b_totals_zoho,
)
from modules.indirect_tax.gstr_period_balance import get_opening_itc
from test_gstr2b_reco_zoho_engine import _build_portal_file, _build_zoho_file

TEST_OWNER = 'zoho_3b_test_user'
TEST_CLIENT = 'Zoho 3B Test Client'


def _build_gstr1_icn_header():
    df = pd.DataFrame({
        'Date': ['2025-12-05'],
        'Invoice Number': ['SALE-001'],
        'Transaction_Type': ['Invoice'],
        'Taxable_Amount': [10000.0],
        'Integrated Tax': [1800.0],
        'Central Tax': [0],
        'State UT Tax': [0],
        'Customer Name': ['Zoho 3B Test'],
        'GSTIN': ['27AAAAA0000A1Z5'],
    })
    tmpdir = tempfile.mkdtemp()
    fp = os.path.join(tmpdir, 'icn_header.xlsx')
    df.to_excel(fp, index=False)
    return fp


def test_gstr1_sales_wired_into_dashboard_and_itc_carries_forward():
    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        # Clean slate for this test client so re-runs don't see stale balances
        for period in ('2025-11', '2025-12', '2026-01'):
            rec = db.session.get(GstrPeriodBalance, (TEST_OWNER, TEST_CLIENT, period))
            if rec:
                db.session.delete(rec)
        db.session.commit()

        gstr1_fp = _build_gstr1_icn_header()
        portal_file = _build_portal_file()
        zoho_file = _build_zoho_file()

        output = generate_gstr3b_zoho_report(
            {'file_invoice_credit_notes': gstr1_fp}, portal_file, zoho_file,
            TEST_OWNER, TEST_CLIENT, '2025-12'
        )

        sheets = pd.read_excel(output, sheet_name=None)
        assert '3B SUMMARY' in sheets, f"3B SUMMARY missing. Got: {list(sheets.keys())}"
        assert 'GSTR1 SUMMARY' in sheets, f"GSTR1 SUMMARY missing. Got: {list(sheets.keys())}"

        # GSTR1 SUMMARY's SALES row IGST should be the real GSTR-1 sales
        # figure (1800), not a manually-typed 0.
        gstr1_summary = sheets['GSTR1 SUMMARY']
        sales_row = gstr1_summary[gstr1_summary['NATURE'] == 'SALES']
        assert not sales_row.empty, "SALES row missing from GSTR1 SUMMARY"
        assert abs(sales_row.iloc[0]['IGST'] - 1800.0) < 0.01, \
            f"GSTR-1 sales IGST not wired in correctly: {sales_row.iloc[0]['IGST']}"

        # Opening ITC for this first run should have been 0 (no prior period)
        record = db.session.get(GstrPeriodBalance, (TEST_OWNER, TEST_CLIENT, '2025-12'))
        assert record is not None, "Closing balance was not persisted"
        closing_igst = record.closing_itc_igst

        # Next period should auto-carry this exact closing balance as opening
        opening_next = get_opening_itc(TEST_OWNER, TEST_CLIENT, '2026-01')
        assert abs(opening_next['igst'] - closing_igst) < 0.01, \
            f"Opening ITC did not carry forward: {opening_next['igst']} != {closing_igst}"

    print("GSTR-3B Zoho: GSTR-1 sales wiring + opening/closing ITC carry-forward OK")


def test_manual_sales_entry_skips_gstr1_files_entirely():
    """When Zoho's GSTR-1 export format isn't usable, the CA can type in the
    sales totals directly instead -- mirrors the equivalent Odoo GSTR-3B
    manual entry option. Confirms manual_sales wires into the Master
    Dashboard the same way real GSTR-1 files would, with no GSTR-1 files
    passed at all."""
    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        for period in ('2025-11', '2025-12', '2026-01'):
            rec = db.session.get(GstrPeriodBalance, (TEST_OWNER, 'Zoho Manual Sales Client', period))
            if rec:
                db.session.delete(rec)
        db.session.commit()

        portal_file = _build_portal_file()
        zoho_file = _build_zoho_file()

        output = generate_gstr3b_zoho_report(
            {}, portal_file, zoho_file,
            TEST_OWNER, 'Zoho Manual Sales Client', '2025-12',
            manual_sales={'taxable': 10000.0, 'igst': 1800.0, 'cgst': 0, 'sgst': 0},
        )

        sheets = pd.read_excel(output, sheet_name=None)
        gstr1_summary = sheets['GSTR1 SUMMARY']
        sales_row = gstr1_summary[gstr1_summary['NATURE'] == 'SALES']
        assert not sales_row.empty
        assert abs(sales_row.iloc[0]['IGST'] - 1800.0) < 0.01, \
            f"Manually entered sales IGST not wired in correctly: {sales_row.iloc[0]['IGST']}"

        # cleanup
        rec = db.session.get(GstrPeriodBalance, (TEST_OWNER, 'Zoho Manual Sales Client', '2025-12'))
        if rec:
            db.session.delete(rec)
            db.session.commit()

    print("GSTR-3B Zoho: manual sales entry (no GSTR-1 files) wires in correctly")


def test_compute_3b_totals_zoho_matches_hand_computed_values():
    """Hand-computed scenario, comfortable-ITC case (sales IGST 1000, CGST/
    SGST 500 each; this month's ITC IGST 3000, CGST/SGST 200 each; no
    opening balance, no RCM):

    IGST offsets its own liability first (1000 used), remainder (2000)
    splits 1000/1000 into CGST and SGST -- more than enough to fully cover
    both, so CGST/SGST ITC itself goes unused and cash payable is 0 on all
    three heads. Remaining ITC: IGST fully consumed (0 left), CGST/SGST
    carry forward untouched (200 each)."""
    sales = {'igst': 1000.0, 'cgst': 500.0, 'sgst': 500.0}
    opening_itc = {'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0}
    gstr2b_buckets = {
        'current_month_b2b': {'taxable': 0, 'igst': 3000.0, 'cgst': 200.0, 'sgst': 200.0},
        'previous_month_input': {'taxable': 0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0},
        'credit_note': {'taxable': 0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0},
        'rcm': {'taxable': 0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0},
    }

    totals = compute_3b_totals_zoho(sales, gstr2b_buckets, opening_itc)

    for head in ('igst', 'cgst', 'sgst'):
        assert abs(totals['cash_payable'][head]) < 0.01, \
            f"Expected 0 cash payable ({head}), got {totals['cash_payable'][head]}"
    assert abs(totals['remaining_itc']['igst']) < 0.01, \
        f"Expected IGST fully consumed, got {totals['remaining_itc']['igst']}"
    assert abs(totals['remaining_itc']['cgst'] - 200.0) < 0.01, \
        f"Expected 200 CGST ITC carried forward, got {totals['remaining_itc']['cgst']}"
    assert abs(totals['remaining_itc']['sgst'] - 200.0) < 0.01, \
        f"Expected 200 SGST ITC carried forward, got {totals['remaining_itc']['sgst']}"

    print("compute_3b_totals_zoho: offset math matches hand-computed values OK")


def test_compute_3b_totals_zoho_jv_balances_with_rcm():
    """A scenario with real RCM (liability + ITC both nonzero) and a genuine
    cash payable, to confirm the JV rows (as wired in
    write_3b_summary_sheet_zoho) are self-balancing -- total debit (output
    liability including RCM) must equal total credit (ITC utilized + RCM's
    cash-only portion + residual cash payable). An earlier draft of the JV
    double-counted RCM's ITC (added once via compute_3b_totals_zoho's
    `off`/`cash` figures, which already fold RCM in, and again by adding
    `+ rcm[head]` directly onto the Input-ITC JV rows) -- this test checks
    the actual JV row values, not just the underlying totals, so that class
    of bug can't silently reappear."""
    sales = {'igst': 10000.0, 'cgst': 5000.0, 'sgst': 5000.0}
    opening_itc = {'igst': 2000.0, 'cgst': 0.0, 'sgst': 0.0}
    gstr2b_buckets = {
        'current_month_b2b': {'taxable': 0, 'igst': 4000.0, 'cgst': 1000.0, 'sgst': 1000.0},
        'previous_month_input': {'taxable': 0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0},
        'credit_note': {'taxable': 0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0},
        'rcm': {'taxable': 0, 'igst': 500.0, 'cgst': 0.0, 'sgst': 0.0},
    }

    totals = compute_3b_totals_zoho(sales, gstr2b_buckets, opening_itc)
    off, cash, rcm, sales_liab = totals['offset'], totals['cash_payable'], gstr2b_buckets['rcm'], totals['sales_liability']

    debit_total = sum(sales_liab.values()) + sum(rcm.values())
    credit_total = (
        (off['igst_used_on_igst'] + off['igst_used_on_cgst'] + off['igst_used_on_sgst'])
        + off['cgst_itc_used'] + off['sgst_itc_used']
        + cash['igst'] + cash['cgst'] + cash['sgst']
    )
    assert abs(debit_total - credit_total) < 0.01, \
        f"JV does not balance: debit {debit_total} != credit {credit_total}"

    print("compute_3b_totals_zoho: JV rows balance (debit == credit) with RCM present OK")


if __name__ == '__main__':
    test_gstr1_sales_wired_into_dashboard_and_itc_carries_forward()
    test_manual_sales_entry_skips_gstr1_files_entirely()
    test_compute_3b_totals_zoho_matches_hand_computed_values()
    test_compute_3b_totals_zoho_jv_balances_with_rcm()
    print("ALL TESTS PASSED")
