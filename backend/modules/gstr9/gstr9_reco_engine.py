"""
GSTR-9 three-way ITC reconciliation (Books vs 2B/8A vs 3B).

The annual analogue of the monthly GSTR-2B reco: instead of comparing the
portal against books for one period, this matches every purchase invoice /
credit note / debit note across THREE year-long sources by GSTIN +
Document No. and classifies each one by where it appears and whether the
tax (ITC) figures agree -- surfacing exactly the differences a CA has to
explain (or reverse) in GSTR-9 Table 8.

All three input sheets share the layout the firm already prepares (same as
their "As Per 3B" working):
    Nature | GSTIN | Vendor Name | Document No. | Document type |
    Invoice date | Invoice Value | Place of Supply | Reverse Charge |
    Taxable Value | Integrated Tax | Central Tax | State/UT Tax |
    ITC Availability
Credit notes carry NEGATIVE amounts (so a plain sum nets them out). A
grand-total row (blank Nature/GSTIN, only amount columns filled) sits at
the bottom of each sheet and is auto-detected and dropped.

Reconciliation figure: total tax (IGST+CGST+SGST) = the ITC, compared with
a small rounding tolerance. Taxable / IGST / CGST / SGST are all shown.

Amendments (2B/8A sheet only): a row whose Nature contains "amend" carries
the supplier's REVISED absolute value for a bill whose original number it
references with a suffix (e.g. original "200", amendment "200-a"). The
amendment REPLACES the original bill's 2B value (the vendor amended it to
0, or to 50 -- that new figure is the correct one), matched back to the
base bill by GSTIN + base document number. This is the one piece built from
the firm's description rather than a real 2B sample, so it's isolated in
_resolve_amendments() for easy validation/tuning against a real file.
"""
import re
from io import BytesIO

import pandas as pd
from xlsxwriter.utility import xl_col_to_name

# Match decision uses total tax; anything within this many rupees is "equal"
# (absorbs paise-level rounding across the year).
TAX_TOLERANCE = 2.0

# ==========================================
#  SMALL UTILITIES (self-contained -- no coupling to the other engines)
# ==========================================

def _clean_gstin(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).upper().strip().replace(" ", "").replace("-", "")
    return s[:15]

def _clean_docno(val):
    """Lowercase, strip everything but alphanumerics -- so '25-26/5872' and
    '25 26 5872' collapse to the same key. Same normalization the monthly
    reco uses, so behavior is consistent."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return re.sub(r'[^a-z0-9]', '', str(val).lower())

def _safe_float(val):
    if val is None or val == '' or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    try:
        return float(str(val).replace(',', '').strip())
    except (ValueError, TypeError):
        return 0.0

def _find_col(columns, *keywords):
    for c in columns:
        cl = str(c).lower()
        if all(k in cl for k in keywords):
            return c
    return None


# ==========================================
#  LOADING & NORMALIZATION
# ==========================================

def _load_sheet(file_obj):
    """Reads one prepared sheet into a list of normalized row dicts, dropping
    the trailing grand-total row (blank Nature/GSTIN with only amount
    columns populated)."""
    xls = pd.ExcelFile(file_obj)
    # Prefer a sheet named like B2B, else the first non-empty sheet.
    sheet_name = next((s for s in xls.sheet_names if s.strip().lower() == 'b2b'), xls.sheet_names[0])
    df = pd.read_excel(xls, sheet_name=sheet_name, header=0)
    df = df.dropna(how='all')

    cols = list(df.columns)
    col_nature = _find_col(cols, 'nature')
    col_gstin = _find_col(cols, 'gstin')
    col_vendor = _find_col(cols, 'vendor') or _find_col(cols, 'name')
    col_doc = _find_col(cols, 'document', 'no') or _find_col(cols, 'doc') or _find_col(cols, 'invoice', 'number')
    col_doctype = _find_col(cols, 'document', 'type') or _find_col(cols, 'type')
    col_date = _find_col(cols, 'invoice', 'date') or _find_col(cols, 'date')
    col_rcm = _find_col(cols, 'reverse')
    col_taxable = _find_col(cols, 'taxable')
    col_igst = _find_col(cols, 'integrated') or _find_col(cols, 'igst')
    col_cgst = _find_col(cols, 'central') or _find_col(cols, 'cgst')
    col_sgst = _find_col(cols, 'state') or _find_col(cols, 'sgst')
    col_itc = _find_col(cols, 'itc')

    rows = []
    for _, r in df.iterrows():
        gstin = _clean_gstin(r.get(col_gstin)) if col_gstin else ""
        docno_raw = r.get(col_doc) if col_doc else None
        docno_clean = _clean_docno(docno_raw)

        # Grand-total / blank rows: no GSTIN and no document number, but the
        # amount columns are filled. Skip -- they'd otherwise double count.
        if not gstin and not docno_clean:
            continue

        nature = str(r.get(col_nature) or '').strip() if col_nature else ''
        rows.append({
            'gstin': gstin,
            'vendor': str(r.get(col_vendor) or '').strip() if col_vendor else '',
            'docno_raw': str(docno_raw).strip() if docno_raw is not None else '',
            'docno_clean': docno_clean,
            'nature': nature,
            'is_amendment': 'amend' in nature.lower(),
            'doctype': str(r.get(col_doctype) or '').strip() if col_doctype else '',
            'date': r.get(col_date) if col_date else None,
            'rcm': str(r.get(col_rcm) or '').strip() if col_rcm else '',
            'itc': str(r.get(col_itc) or '').strip() if col_itc else '',
            'taxable': _safe_float(r.get(col_taxable)) if col_taxable else 0.0,
            'igst': _safe_float(r.get(col_igst)) if col_igst else 0.0,
            'cgst': _safe_float(r.get(col_cgst)) if col_cgst else 0.0,
            'sgst': _safe_float(r.get(col_sgst)) if col_sgst else 0.0,
        })
    return rows


def _blank_bucket():
    return {'taxable': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0,
            'vendor': '', 'docno_raw': '', 'nature': '', 'rcm': '', 'present': False}


def _aggregate(rows):
    """Sum signed amounts per (gstin, docno_clean) key. Multiple lines of the
    same bill net together; credit notes (already negative) net against
    their invoices when they share a number."""
    agg = {}
    for r in rows:
        key = (r['gstin'], r['docno_clean'])
        b = agg.get(key)
        if b is None:
            b = _blank_bucket()
            b['vendor'] = r['vendor']
            b['docno_raw'] = r['docno_raw']
            b['nature'] = r['nature']
            b['rcm'] = r['rcm']
            agg[key] = b
        b['present'] = True
        b['taxable'] += r['taxable']
        b['igst'] += r['igst']
        b['cgst'] += r['cgst']
        b['sgst'] += r['sgst']
        if not b['vendor'] and r['vendor']:
            b['vendor'] = r['vendor']
    return agg


# ==========================================
#  AMENDMENT RESOLUTION (2B/8A only) -- see module docstring
# ==========================================

def _resolve_amendments(portal_rows):
    """Returns the 2B aggregate with amendments applied. Normal rows are
    aggregated first; then each amendment row REPLACES its base bill's value
    (the amended figure is the supplier's revised absolute value). The base
    bill is found within the same GSTIN by longest-prefix match of the
    cleaned document number (so '200a' -> '200'); if no base is present in
    the 2B sheet, the amendment stands on its own under its stripped base
    key so it still lines up with the same bill in Books/3B."""
    normal = [r for r in portal_rows if not r['is_amendment']]
    amendments = [r for r in portal_rows if r['is_amendment']]

    agg = _aggregate(normal)

    # Index existing base doc numbers per GSTIN for prefix matching.
    keys_by_gstin = {}
    for (gstin, docno) in agg.keys():
        keys_by_gstin.setdefault(gstin, []).append(docno)

    def _strip_suffix(docno_clean):
        # '200a' -> '200', '200amd' -> '200'. Strip a short trailing alpha
        # tail only when it follows a digit, so purely-alpha numbers are left
        # alone.
        m = re.match(r'^(.*\d)[a-z]{1,3}$', docno_clean)
        return m.group(1) if m else docno_clean

    for amd in amendments:
        gstin = amd['gstin']
        amd_clean = amd['docno_clean']
        candidates = keys_by_gstin.get(gstin, [])

        # Longest existing base key that is a prefix of the amendment number.
        base = None
        best_len = -1
        for cand in candidates:
            if cand and amd_clean.startswith(cand) and len(cand) > best_len:
                base = cand
                best_len = len(cand)
        if base is None:
            base = _strip_suffix(amd_clean)

        key = (gstin, base)
        b = agg.get(key)
        if b is None:
            b = _blank_bucket()
            keys_by_gstin.setdefault(gstin, []).append(base)
            agg[key] = b
        # REPLACE (not add): the amendment carries the new absolute value.
        b['present'] = True
        b['taxable'] = amd['taxable']
        b['igst'] = amd['igst']
        b['cgst'] = amd['cgst']
        b['sgst'] = amd['sgst']
        b['vendor'] = amd['vendor'] or b['vendor']
        b['docno_raw'] = amd['docno_raw'] or b['docno_raw']
        b['nature'] = amd['nature']
        b['rcm'] = amd['rcm'] or b['rcm']
    return agg


# ==========================================
#  CLASSIFICATION (the smart core)
# ==========================================

def _tax_total(bucket):
    return bucket['igst'] + bucket['cgst'] + bucket['sgst']

def _eq(a, b):
    return abs(a - b) <= TAX_TOLERANCE

# (status label, risk level). Risk drives sheet ordering and colour.
def _classify(b, p, t):
    bp, pp, tp = b['present'], p['present'], t['present']
    bt, pt, tt = _tax_total(b), _tax_total(p), _tax_total(t)

    if bp and pp and tp:
        if _eq(bt, pt) and _eq(bt, tt):
            return ('Reconciled (all three agree)', 'OK')
        if _eq(bt, tt) and not _eq(bt, pt):
            return ('Books & 3B agree, 2B differs', 'Medium')
        if _eq(bt, pt) and not _eq(bt, tt):
            return ('Books & 2B agree, 3B differs (over/under-claimed)', 'Medium')
        if _eq(pt, tt) and not _eq(bt, pt):
            return ('2B & 3B agree, Books differs (booking error)', 'Medium')
        return ('All three differ', 'Medium')

    if bp and pp and not tp:
        return ('Eligible but not claimed in 3B', 'Low')
    if bp and not pp and tp:
        return ('Claimed & booked, NOT in 2B', 'High')
    if not bp and pp and tp:
        return ('Claimed & in 2B, not in books', 'Medium')
    if bp and not pp and not tp:
        return ('In books only (vendor not filed / not claimed)', 'Low')
    if not bp and pp and not tp:
        return ('In 2B only (not booked, not claimed)', 'Low')
    if not bp and not pp and tp:
        return ('Claimed only — no 2B, no books', 'High')
    return ('Unclassified', 'Medium')


# ==========================================
#  WORKBOOK OUTPUT
# ==========================================

RISK_ORDER = {'High': 0, 'Medium': 1, 'Low': 2, 'OK': 3}

def _build_reco_dataframe(books, portal, filed):
    all_keys = set(books) | set(portal) | set(filed)
    records = []
    for key in all_keys:
        gstin, docno = key
        b = books.get(key, _blank_bucket())
        p = portal.get(key, _blank_bucket())
        t = filed.get(key, _blank_bucket())
        status, risk = _classify(b, p, t)

        vendor = b['vendor'] or p['vendor'] or t['vendor']
        docraw = b['docno_raw'] or p['docno_raw'] or t['docno_raw']

        b_tax, p_tax, t_tax = _tax_total(b), _tax_total(p), _tax_total(t)
        records.append({
            'GSTIN': gstin,
            'Vendor Name': vendor,
            'Document No.': docraw,
            'In Books': 'Yes' if b['present'] else '',
            'In 2B/8A': 'Yes' if p['present'] else '',
            'In 3B': 'Yes' if t['present'] else '',
            'Books Taxable': round(b['taxable'], 2),
            'Books ITC': round(b_tax, 2),
            '2B Taxable': round(p['taxable'], 2),
            '2B ITC': round(p_tax, 2),
            '3B Taxable': round(t['taxable'], 2),
            '3B ITC': round(t_tax, 2),
            'ITC Diff (Books-2B)': round(b_tax - p_tax, 2),
            'ITC Diff (Books-3B)': round(b_tax - t_tax, 2),
            'ITC Diff (2B-3B)': round(p_tax - t_tax, 2),
            'Status': status,
            'Risk': risk,
            '_risk_rank': RISK_ORDER.get(risk, 1),
        })
    df = pd.DataFrame(records)
    if df.empty:
        return df
    return df.sort_values(['_risk_rank', 'GSTIN', 'Document No.']).drop(columns=['_risk_rank']).reset_index(drop=True)


def _totals(agg):
    return {
        'taxable': round(sum(b['taxable'] for b in agg.values()), 2),
        'igst': round(sum(b['igst'] for b in agg.values()), 2),
        'cgst': round(sum(b['cgst'] for b in agg.values()), 2),
        'sgst': round(sum(b['sgst'] for b in agg.values()), 2),
    }


def _write_formatted(writer, df, sheet_name, wb, fmts):
    """Writes a DataFrame with a styled header, autofilter, frozen header,
    and a bottom SUBTOTAL row on the numeric columns."""
    safe_name = sheet_name[:31]
    if df.empty:
        ws = wb.add_worksheet(safe_name)
        writer.sheets[safe_name] = ws
        ws.write(0, 0, 'No records in this category.', fmts['bold'])
        return
    df.to_excel(writer, sheet_name=safe_name, index=False)
    ws = writer.sheets[safe_name]
    n_rows, n_cols = df.shape

    for c, col in enumerate(df.columns):
        ws.write(0, c, col, fmts['header'])
        width = max(12, min(40, int(df[col].astype(str).str.len().max() if n_rows else 12) + 2))
        ws.set_column(c, c, width)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, n_rows, n_cols - 1)

    total_row = n_rows + 1
    ws.write(total_row, 0, 'TOTAL', fmts['bold'])
    for c, col in enumerate(df.columns):
        if any(k in col for k in ('Taxable', 'ITC', 'Diff')):
            letter = xl_col_to_name(c)
            ws.write_formula(total_row, c, f'=SUBTOTAL(9,{letter}2:{letter}{total_row})', fmts['num_bold'])

    # Colour the Status column by risk where present.
    if 'Risk' in df.columns:
        risk_idx = df.columns.get_loc('Risk')
        status_idx = df.columns.get_loc('Status')
        for i in range(n_rows):
            risk = df.iloc[i]['Risk']
            fmt = {'High': fmts['red'], 'Medium': fmts['amber'], 'Low': fmts['grey'], 'OK': fmts['green']}.get(risk)
            if fmt:
                ws.write(i + 1, status_idx, df.iloc[i]['Status'], fmt)
                ws.write(i + 1, risk_idx, risk, fmt)


def _write_summary(writer, wb, fmts, computed, controls, reco_df):
    ws = wb.add_worksheet('Summary')
    writer.sheets['Summary'] = ws
    ws.set_column(0, 0, 42)
    ws.set_column(1, 8, 16)

    ws.write(0, 0, 'GSTR-9 THREE-WAY RECONCILIATION', fmts['title'])

    # --- Control-total tie-out ---
    r = 2
    ws.write(r, 0, 'CONTROL TOTAL TIE-OUT (ITC)', fmts['header'])
    ws.write_row(r + 1, 0, ['Source', 'Your Total', 'Computed Total', 'Difference', 'Status'], fmts['bold'])
    labels = [('Books', 'books'), ('2B / 8A', 'portal'), ('3B', 'filed')]
    row = r + 2
    for label, key in labels:
        comp = computed[key]['igst'] + computed[key]['cgst'] + computed[key]['sgst']
        ctrl_dict = controls.get(key) if controls else None
        ctrl = None
        if ctrl_dict is not None:
            ctrl = float(ctrl_dict.get('igst') or 0) + float(ctrl_dict.get('cgst') or 0) + float(ctrl_dict.get('sgst') or 0)
        ws.write(row, 0, label)
        if ctrl is None:
            ws.write(row, 1, '—')
            ws.write(row, 2, round(comp, 2), fmts['num'])
            ws.write(row, 3, '—')
            ws.write(row, 4, 'Not provided', fmts['grey'])
        else:
            diff = round(ctrl - comp, 2)
            ws.write(row, 1, round(ctrl, 2), fmts['num'])
            ws.write(row, 2, round(comp, 2), fmts['num'])
            ws.write(row, 3, diff, fmts['num'])
            ok = abs(diff) <= TAX_TOLERANCE
            ws.write(row, 4, 'Tied out ✓' if ok else 'MISMATCH — check file', fmts['green'] if ok else fmts['red'])
        row += 1

    # --- Headline three-way differences ---
    row += 1
    ws.write(row, 0, 'HEADLINE DIFFERENCES (ITC)', fmts['header'])
    row += 1
    b = computed['books']['igst'] + computed['books']['cgst'] + computed['books']['sgst']
    p = computed['portal']['igst'] + computed['portal']['cgst'] + computed['portal']['sgst']
    t = computed['filed']['igst'] + computed['filed']['cgst'] + computed['filed']['sgst']
    for label, val in [('Books − 2B/8A', b - p), ('Books − 3B', b - t), ('2B/8A − 3B', p - t)]:
        ws.write(row, 0, label)
        ws.write(row, 1, round(val, 2), fmts['num'])
        row += 1

    # --- Category breakdown ---
    row += 1
    ws.write(row, 0, 'BREAKDOWN BY CATEGORY', fmts['header'])
    ws.write_row(row + 1, 0, ['Status', 'Risk', 'Count', 'Net ITC Impact'], fmts['bold'])
    row += 2
    if not reco_df.empty:
        grp = reco_df.groupby(['Status', 'Risk']).agg(
            Count=('GSTIN', 'count'),
            Impact=('ITC Diff (Books-3B)', 'sum'),
        ).reset_index()
        grp['_rank'] = grp['Risk'].map(RISK_ORDER).fillna(1)
        grp = grp.sort_values('_rank')
        for _, g in grp.iterrows():
            risk = g['Risk']
            fmt = {'High': fmts['red'], 'Medium': fmts['amber'], 'Low': fmts['grey'], 'OK': fmts['green']}.get(risk, fmts['num'])
            ws.write(row, 0, g['Status'])
            ws.write(row, 1, risk, fmt)
            ws.write(row, 2, int(g['Count']))
            ws.write(row, 3, round(float(g['Impact']), 2), fmts['num'])
            row += 1


def _make_formats(wb):
    return {
        'title': wb.add_format({'bold': True, 'font_size': 14, 'font_color': '#1F3864'}),
        'header': wb.add_format({'bold': True, 'bg_color': '#2F4F4F', 'font_color': 'white', 'border': 1}),
        'bold': wb.add_format({'bold': True}),
        'num': wb.add_format({'num_format': '#,##0.00'}),
        'num_bold': wb.add_format({'bold': True, 'num_format': '#,##0.00', 'top': 1}),
        'red': wb.add_format({'bold': True, 'bg_color': '#FFC7CE', 'font_color': '#9C0006'}),
        'amber': wb.add_format({'bold': True, 'bg_color': '#FFEB9C', 'font_color': '#9C6500'}),
        'green': wb.add_format({'bold': True, 'bg_color': '#C6EFCE', 'font_color': '#006100'}),
        'grey': wb.add_format({'font_color': '#808080'}),
    }


# ==========================================
#  MAIN ENTRY POINT
# ==========================================

def process_gstr9_reco(books_file, portal_file, filed_file, control_totals=None):
    """books_file / portal_file / filed_file: file objects or paths for the
    As-Per-Books, As-Per-2B/8A, and As-Per-3B sheets.

    control_totals (optional): {'books': {'igst','cgst','sgst'}, 'portal':
    {...}, 'filed': {...}} of the ITC totals the CA expects, for the tie-out
    check. Any source omitted just shows 'Not provided'.

    Returns a BytesIO xlsx workbook.
    """
    books_rows = _load_sheet(books_file)
    portal_rows = _load_sheet(portal_file)
    filed_rows = _load_sheet(filed_file)

    books = _aggregate(books_rows)
    portal = _resolve_amendments(portal_rows)   # amendments applied here
    filed = _aggregate(filed_rows)

    computed = {'books': _totals(books), 'portal': _totals(portal), 'filed': _totals(filed)}
    reco_df = _build_reco_dataframe(books, portal, filed)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        wb = writer.book
        fmts = _make_formats(wb)

        _write_summary(writer, wb, fmts, computed, control_totals, reco_df)
        _write_formatted(writer, reco_df, 'Full Reconciliation', wb, fmts)

        # One sheet per non-reconciled category, highest risk first.
        if not reco_df.empty:
            issues = reco_df[reco_df['Risk'] != 'OK']
            seen = []
            for status in issues.sort_values('Status').groupby('Status').groups:
                subset = issues[issues['Status'] == status]
                rank = RISK_ORDER.get(subset.iloc[0]['Risk'], 1)
                seen.append((rank, status, subset))
            for _, status, subset in sorted(seen, key=lambda x: x[0]):
                # Short, filesystem-safe tab name derived from the status.
                short = re.sub(r'[^A-Za-z0-9 ]', '', status)[:28]
                _write_formatted(writer, subset.drop(columns=['Risk']), short, wb, fmts)

    output.seek(0)
    return output
