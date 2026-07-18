"""
Regression test for the GSTR-3B Zoho flow (generate_gstr3b_zoho_report).

Unlike test_gstr3b_engine.py, there's no real filed Zoho 3B working paper
to validate against -- this checks the two things that were actually built
(GSTR-1 Zoho sales wiring into the existing Master Dashboard, and opening/
closing ITC auto-carry across periods) against synthetic data. The
Section 49 offset math itself (calculate_smart_offset) and the reconciliation
engine it builds on already have their own tests.

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
from modules.indirect_tax.gstr2b_reco_zoho_engine import generate_gstr3b_zoho_report
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
        assert 'Master Dashboard' in sheets, f"Master Dashboard missing. Got: {list(sheets.keys())}"

        dashboard = sheets['Master Dashboard']
        # Row 2 (0-indexed) = "1. Output Liability" -- IGST column should be
        # the real GSTR-1 sales figure (1800), not a manually-typed 0.
        output_liability_row = dashboard[dashboard['Particulars'] == '1. Output Liability']
        assert not output_liability_row.empty, "Output Liability row missing from dashboard"
        assert abs(output_liability_row.iloc[0]['IGST'] - 1800.0) < 0.01, \
            f"GSTR-1 sales IGST not wired in correctly: {output_liability_row.iloc[0]['IGST']}"

        # Opening ITC for this first run should have been 0 (no prior period)
        record = db.session.get(GstrPeriodBalance, (TEST_OWNER, TEST_CLIENT, '2025-12'))
        assert record is not None, "Closing balance was not persisted"
        closing_igst = record.closing_itc_igst

        # Next period should auto-carry this exact closing balance as opening
        opening_next = get_opening_itc(TEST_OWNER, TEST_CLIENT, '2026-01')
        assert abs(opening_next['igst'] - closing_igst) < 0.01, \
            f"Opening ITC did not carry forward: {opening_next['igst']} != {closing_igst}"

    print("GSTR-3B Zoho: GSTR-1 sales wiring + opening/closing ITC carry-forward OK")


if __name__ == '__main__':
    test_gstr1_sales_wired_into_dashboard_and_itc_carries_forward()
    print("ALL TESTS PASSED")
