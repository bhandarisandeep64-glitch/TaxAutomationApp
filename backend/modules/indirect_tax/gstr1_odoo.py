import pandas as pd
import numpy as np
import re
import os
from openpyxl.utils import get_column_letter

# ==========================================
#  HSN B2B / HSN B2C parser (current Odoo export format)
# ==========================================
#
# Odoo now exports exactly two files -- "HSN B2B" and "HSN B2C" -- from the
# account.move.line ("Journal Item") view. One row per line-item within an
# invoice (an invoice with several HSN codes/products gets one row per
# HSN/SAC code, all sharing the same invoice Number), rather than the old
# per-tax-account ledger export.
#
# Columns actually used: GSTR Section, Partner, GSTIN, Date, HSN/SAC Code,
# Number, Taxes (e.g. "18% GST S" / "18% IGST S" / "5% GST S"), Taxable Amt.
# (an invoice-level total, repeated across that invoice's lines), Credit,
# Debit.
#
# Verified against real exports (both files the firm shared):
#   - Which file is B2B vs B2C has to come from the upload slot, not the
#     data -- the B2C file's own GSTR Section column is always "B2CS", even
#     for its credit notes, so it can't tell CDNR apart on its own.
#   - Credit-note detection instead comes from the Debit column being
#     populated instead of Credit -- this is consistent across both files.
#   - Credit/Debit is the TAXABLE VALUE for that specific line (not the tax
#     amount) -- confirmed against a real multi-line invoice where the line
#     values summed to the invoice's own "Taxable Amt." total, not to 18%
#     of it. Tax is computed here, not read from the file.
#   - "Taxes" gives the rate and type as plain text: "IGST S" -> the whole
#     tax is IGST; "GST S" -> the tax splits evenly into CGST/SGST.
#   - An invoice can mix rates across its lines (e.g. some products at 18%,
#     others at 5%), so tax is computed per LINE using that line's own rate,
#     then summed per invoice -- not one rate applied to the invoice total.
#   - The per-line sum can occasionally fall short of the file's own
#     "Taxable Amt." column (observed on one real invoice, off by ~10k) --
#     likely a line posted to an account outside this export. The per-line
#     sum is used as the authoritative figure (it's what the tax
#     calculation is actually built from); the file's own total is kept
#     alongside as a reference column, and any material mismatch is logged
#     rather than silently dropped.

RATE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')


def _read_file(fp):
    if str(fp).lower().endswith('.csv'):
        return pd.read_csv(fp)
    return pd.read_excel(fp)


def _extract_rate(taxes_str):
    m = RATE_RE.search(str(taxes_str or ''))
    return float(m.group(1)) if m else 0.0


def _is_igst(taxes_str):
    return 'igst' in str(taxes_str or '').lower()


def _parse_hsn_file(fp, base_category):
    """Returns a per-line DataFrame from one HSN B2B/B2C export, tagged with
    Nature (base_category, or base_category + ' CDNR' for credit notes) and
    the tax computed for that line (Line_IGST/Line_CGST/Line_SGST)."""
    df = _read_file(fp)

    for col in ['GSTIN', 'Partner', 'Number', 'Taxes', 'HSN/SAC Code', 'Date']:
        if col not in df.columns:
            df[col] = ''
    for col in ['Taxable Amt.', 'Credit', 'Debit']:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Primary signal: the B2B file's own 'GSTR Section' explicitly tags
    # credit notes ("CDNR Regular") -- more reliable than Debit/Credit alone,
    # confirmed against real data where one credit note had its amount
    # posted to Credit instead of Debit (breaking a Debit-only check) but
    # was still correctly labeled "CDNR Regular". Debit-populated is kept as
    # a fallback for the B2C file, whose 'GSTR Section' is always "B2CS"
    # (never distinguishes CDNR on its own).
    section = df['GSTR Section'].astype(str).str.lower()
    is_cn = section.str.contains('cdnr', na=False) | (df['Debit'] != 0)
    df['Nature'] = np.where(is_cn, f"{base_category} CDNR", base_category)
    # Per-line taxable value -- whichever of Debit/Credit is actually
    # populated for that row (only one ever is), independent of the Nature
    # tag above so a Debit/Credit swap like the one above can't also corrupt
    # the amount.
    df['Line_Taxable'] = np.where(df['Debit'] != 0, df['Debit'], df['Credit'])
    df['Rate'] = df['Taxes'].apply(_extract_rate)
    df['Is_IGST'] = df['Taxes'].apply(_is_igst)

    total_tax = (df['Line_Taxable'] * df['Rate'] / 100).round(2)
    cgst = np.where(df['Is_IGST'], 0.0, (total_tax / 2).round(2))
    df['Line_IGST'] = np.where(df['Is_IGST'], total_tax, 0.0)
    df['Line_CGST'] = cgst
    df['Line_SGST'] = np.where(df['Is_IGST'], 0.0, total_tax - cgst)

    return df


def _invoice_level(per_line_df):
    """Collapses the per-line rows down to one row per invoice Number,
    summing the per-line taxable/tax figures (correct even when an invoice
    mixes tax rates across its lines) -- the file's own invoice-level
    'Taxable Amt.' is kept alongside as a reference/reconciliation column,
    not used for the calculation itself."""
    grouped = per_line_df.groupby('Number', as_index=False).agg(
        Nature=('Nature', 'first'), Partner=('Partner', 'first'),
        GSTIN=('GSTIN', 'first'), Date=('Date', 'first'),
        **{'HSN/SAC Code': ('HSN/SAC Code', 'first')},
        **{'Taxable Amt. (Odoo Reference)': ('Taxable Amt.', 'first')},
        **{'Taxable Amt.': ('Line_Taxable', 'sum')},
        IGST=('Line_IGST', 'sum'), CGST=('Line_CGST', 'sum'), SGST=('Line_SGST', 'sum'),
    )
    return grouped


def compute_gstr1_data(file_paths):
    """file_paths: dict with optional 'file_b2b'/'file_b2c' keys pointing at
    Odoo's HSN B2B / HSN B2C Journal Item exports. At least one is required.

    Returns (final_df, summary, hsn_summary_df):
      - final_df: one row per invoice, with IGST/CGST/SGST computed line by
        line and summed (so mixed-rate invoices come out correct).
      - summary: groupby('Nature') totals in the {Category, Taxable, IGST,
        CGST, SGST} shape gstr3b_engine.py's compute_gstr1_buckets expects,
        plus a GRAND TOTAL row. This is the authoritative source for
        GSTR-1/3B totals.
      - hsn_summary_df: HSN-wise net taxable/tax totals (Table 12 style),
        netting credit notes against regular invoices per HSN code -- a
        useful new breakdown this format makes possible, but a best-effort
        one (see module docstring on the occasional per-line shortfall).
    """
    per_line_frames = []
    for key, base_category in (('file_b2b', 'B2B'), ('file_b2c', 'B2C')):
        fp = file_paths.get(key) if file_paths else None
        if fp:
            per_line_frames.append(_parse_hsn_file(fp, base_category))

    if not per_line_frames:
        return None, None, None

    per_line_df = pd.concat(per_line_frames, ignore_index=True)

    invoice_df = _invoice_level(per_line_df)
    for col in ['Taxable Amt.', 'IGST', 'CGST', 'SGST', 'Taxable Amt. (Odoo Reference)']:
        invoice_df[col] = invoice_df[col].round(2)
    invoice_df['Invoice Total'] = (
        invoice_df['Taxable Amt.'] + invoice_df['IGST'] + invoice_df['CGST'] + invoice_df['SGST']
    ).round(2)

    mismatch = (invoice_df['Taxable Amt.'] - invoice_df['Taxable Amt. (Odoo Reference)']).abs()
    flagged = invoice_df[mismatch > 1.0]
    if not flagged.empty:
        print(
            f"GSTR-1 note: {len(flagged)} invoice(s) where the computed taxable value "
            f"(summed from line items) differs from Odoo's own invoice total by more than "
            f"Rs 1 -- likely a line posted outside this export. Invoice numbers: "
            f"{list(flagged['Number'])}"
        )

    final_cols = ['Nature', 'Partner', 'GSTIN', 'Date', 'Number', 'HSN/SAC Code',
                  'Invoice Total', 'Taxable Amt.', 'IGST', 'CGST', 'SGST',
                  'Taxable Amt. (Odoo Reference)']
    final_df = invoice_df[[c for c in final_cols if c in invoice_df.columns]].copy()

    summary = invoice_df.groupby('Nature').agg(
        Taxable=('Taxable Amt.', 'sum'), IGST=('IGST', 'sum'),
        CGST=('CGST', 'sum'), SGST=('SGST', 'sum'),
    ).reset_index().rename(columns={'Nature': 'Category'})
    total_row = pd.DataFrame([{
        'Category': 'GRAND TOTAL',
        'Taxable': summary['Taxable'].sum(), 'IGST': summary['IGST'].sum(),
        'CGST': summary['CGST'].sum(), 'SGST': summary['SGST'].sum(),
    }])
    summary = pd.concat([summary, total_row], ignore_index=True)
    for col in ['Taxable', 'IGST', 'CGST', 'SGST']:
        summary[col] = summary[col].round(2)

    is_cdnr = per_line_df['Nature'].str.contains('CDNR')
    sign = np.where(is_cdnr, -1, 1)
    hsn_summary_df = per_line_df.assign(
        Signed_Taxable=per_line_df['Line_Taxable'] * sign,
        Signed_IGST=per_line_df['Line_IGST'] * sign,
        Signed_CGST=per_line_df['Line_CGST'] * sign,
        Signed_SGST=per_line_df['Line_SGST'] * sign,
    ).groupby('HSN/SAC Code', as_index=False).agg(
        **{'Taxable Value': ('Signed_Taxable', 'sum')},
        IGST=('Signed_IGST', 'sum'), CGST=('Signed_CGST', 'sum'), SGST=('Signed_SGST', 'sum'),
    )
    hsn_summary_df['Total Tax'] = hsn_summary_df['IGST'] + hsn_summary_df['CGST'] + hsn_summary_df['SGST']
    for col in ['Taxable Value', 'IGST', 'CGST', 'SGST', 'Total Tax']:
        hsn_summary_df[col] = hsn_summary_df[col].round(2)
    hsn_summary_df = hsn_summary_df.sort_values('HSN/SAC Code').reset_index(drop=True)

    return final_df, summary, hsn_summary_df


def process_gstr1_odoo(file_paths, output_folder, custom_filename=None):
    """
    Main Wrapper:
    1. Reads the HSN B2B / HSN B2C files.
    2. Computes per-invoice GSTR-1 data and category/HSN summaries.
    3. Generates a formatted Excel with Subtotals, AutoFilter, and an HSN
       Summary sheet.
    """
    try:
        final_df, summary, hsn_summary_df = compute_gstr1_data(file_paths)
        if final_df is None:
            return {"success": False, "error": "Could not process any valid data. Upload at least one of the HSN B2B / HSN B2C files."}

        if custom_filename and str(custom_filename).strip():
            clean_name = re.sub(r'[\\/*?:"<>|]', '-', str(custom_filename).strip())
            output_filename = f"{clean_name} GSTR1.xlsx"
        else:
            output_filename = "GSTR1_Report.xlsx"

        output_full_path = os.path.join(output_folder, output_filename)

        with pd.ExcelWriter(output_full_path, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name='GSTR1 Data', index=False)

            worksheet = writer.sheets['GSTR1 Data']
            last_row = len(final_df) + 2

            summary_start_row = last_row + 4
            summary.to_excel(writer, sheet_name='GSTR1 Data', index=False, startrow=summary_start_row)

            hsn_summary_df.to_excel(writer, sheet_name='HSN Summary', index=False)

        # --- POST-PROCESSING (Formatting) ---
        import openpyxl
        wb = openpyxl.load_workbook(output_full_path)
        ws = wb['GSTR1 Data']

        ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{len(final_df) + 1}"

        ws.cell(row=last_row, column=1).value = "GRAND TOTAL"
        ws.cell(row=last_row, column=1).font = openpyxl.styles.Font(bold=True)

        for col_name in ['Taxable Amt.', 'IGST', 'CGST', 'SGST']:
            if col_name in final_df.columns:
                col_idx = final_df.columns.get_loc(col_name) + 1
                col_letter = get_column_letter(col_idx)
                ws.cell(row=last_row, column=col_idx).value = f"=SUBTOTAL(9, {col_letter}2:{col_letter}{len(final_df)+1})"
                ws.cell(row=last_row, column=col_idx).font = openpyxl.styles.Font(bold=True)

        hsn_ws = wb['HSN Summary']
        if len(hsn_summary_df) > 0:
            hsn_ws.auto_filter.ref = f"A1:{get_column_letter(hsn_ws.max_column)}{len(hsn_summary_df) + 1}"

        wb.save(output_full_path)

        # Cleanup
        for fp in file_paths.values():
            if fp and os.path.exists(fp): os.remove(fp)

        return {
            "success": True,
            "message": "GSTR-1 Report Generated.",
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename,
            "summary_data": summary.to_dict(orient='records')
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
