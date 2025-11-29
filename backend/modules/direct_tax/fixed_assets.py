import pandas as pd
from io import BytesIO
from xlsxwriter.utility import xl_col_to_name

def add_formatting(writer, df, sheet_name):
    if df.empty: return
    df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    (max_row, max_col) = df.shape

    # Formats
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
    num_fmt = workbook.add_format({'num_format': '#,##0.00'})
    bold_fmt = workbook.add_format({'bold': True})
    
    # Write Headers
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_fmt)
        worksheet.set_column(col_num, col_num, 18)

    # Add Totals Row
    total_row = max_row + 1
    worksheet.write(total_row, 0, 'Grand Total', bold_fmt)
    
    # Sum numeric columns
    numeric_cols = ['Opening WDV', 'Additions > 180', 'Additions < 180', 'Sale Amount', 
                    'Dep (Full Rate)', 'Dep (Half Rate)', 'Total Dep.', 'Closing WDV']
    
    for col_name in numeric_cols:
        if col_name in df.columns:
            col_idx = df.columns.get_loc(col_name)
            col_letter = xl_col_to_name(col_idx)
            formula = f'=SUBTOTAL(9,{col_letter}2:{col_letter}{total_row})'
            worksheet.write_formula(total_row, col_idx, formula, num_fmt)

def calculate_depreciation_engine(file_content):
    """
    Core Logic: Reads Excel, calculates Income Tax Depreciation (180 days rule).
    """
    try:
        xls = pd.ExcelFile(file_content)
        df = pd.read_excel(xls, sheet_name=0)
    except:
        file_content.seek(0)
        df = pd.read_csv(file_content)

    # 1. Clean Headers
    df.columns = df.columns.str.strip()
    
    # 2. Ensure Numeric Columns
    num_cols = ['Block Rate', 'Opening WDV', 'Addition Amount', 'Sale Amount']
    for col in num_cols:
        if col not in df.columns: df[col] = 0.0
        else: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. Date Handling (180 Days Rule)
    if 'Addition Date' in df.columns:
        df['Addition Date'] = pd.to_datetime(df['Addition Date'], errors='coerce')
    else:
        df['Addition Date'] = pd.NaT

    def get_addition_split(row):
        add_amt = row['Addition Amount']
        date = row['Addition Date']
        
        if add_amt <= 0 or pd.isna(date):
            # Conservative: Assume > 180 if no date, or 0 if no amount
            return pd.Series([add_amt, 0.0])
        
        # Cut-off: Oct 4th (Month 10, Day 4)
        if date.month > 10 or (date.month == 10 and date.day >= 4):
            return pd.Series([0.0, add_amt]) # < 180 days
        else:
            return pd.Series([add_amt, 0.0]) # > 180 days

    df[['Additions > 180', 'Additions < 180']] = df.apply(get_addition_split, axis=1)

    # 4. Calculate Depreciation Logic
    def calc_row_dep(row):
        rate = row['Block Rate'] / 100.0
        opening = row['Opening WDV']
        sales = row['Sale Amount']
        add_more = row['Additions > 180']
        add_less = row['Additions < 180']
        
        # Net Balance available for Full Rate = (Opening + Adds>180) - Sales
        full_rate_base = opening + add_more - sales
        
        dep_full = 0.0
        dep_half = 0.0
        
        if full_rate_base >= 0:
            dep_full = full_rate_base * rate
            dep_half = add_less * (rate / 2)
        else:
            # Sales ate into the Full Rate base, now eating into Half Rate base
            remaining_sales_impact = abs(full_rate_base) 
            half_rate_base = max(0, add_less - remaining_sales_impact)
            
            dep_full = 0.0
            dep_half = half_rate_base * (rate / 2)
            
        total_dep = dep_full + dep_half
        closing = (opening + add_more + add_less - sales) - total_dep
        
        return pd.Series([dep_full, dep_half, total_dep, closing])

    df[['Dep (Full Rate)', 'Dep (Half Rate)', 'Total Dep.', 'Closing WDV']] = df.apply(calc_row_dep, axis=1)
    
    # Date formatting for output
    df['Addition Date'] = df['Addition Date'].dt.strftime('%d-%m-%Y')

    # 5. Generate Output
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        final_cols = [
            'Asset Name', 'Block Rate', 'Opening WDV', 
            'Addition Date', 'Addition Amount', 
            'Additions > 180', 'Additions < 180',
            'Sale Amount', 
            'Dep (Full Rate)', 'Dep (Half Rate)', 'Total Dep.', 
            'Closing WDV'
        ]
        
        for c in final_cols:
            if c not in df.columns: df[c] = ''
            
        add_formatting(writer, df[final_cols], "Fixed Asset Register")
        
    output.seek(0)
    return output