import pandas as pd
import io
import re

# Helper function to double the CGST rate
def format_cgst_rate(val):
    if pd.isna(val): return val
    val_str = str(val)
    match = re.search(r'([0-9.]+)', val_str)
    if match:
        num = float(match.group(1))
        doubled = num * 2
        return f"{doubled:g}% GST S"
    return val_str

def process_cgst_file(file):
    df = pd.read_excel(file)
    df['CGST'] = df['Credit'].fillna(0) - df['Debit'].fillna(0)
    is_credit_note = df['Debit'].fillna(0) > 0
    df.loc[is_credit_note, 'Taxable Amount'] = -df.loc[is_credit_note, 'Taxable Amount'].abs()
    df.loc[~is_credit_note, 'Taxable Amount'] = df.loc[~is_credit_note, 'Taxable Amount'].abs()
    df = df.rename(columns={'Partner': 'Customer Name', 'Number': 'Invoice Number', 'Label': 'Tax Rate'})
    df['Account'] = 'GST Payable'
    df['Tax Rate'] = df['Tax Rate'].apply(format_cgst_rate)
    df['SGST'] = df['CGST']
    df['IGST'] = 0
    return df

def process_igst_file(file):
    df = pd.read_excel(file)
    df['IGST'] = df['Credit'].fillna(0) - df['Debit'].fillna(0)
    is_credit_note = df['Debit'].fillna(0) > 0
    df.loc[is_credit_note, 'Taxable Amount'] = -df.loc[is_credit_note, 'Taxable Amount'].abs()
    df.loc[~is_credit_note, 'Taxable Amount'] = df.loc[~is_credit_note, 'Taxable Amount'].abs()
    df = df.rename(columns={'Partner': 'Customer Name', 'Number': 'Invoice Number', 'Label': 'Tax Rate'})
    df['Account'] = 'IGST Payable'
    df['CGST'] = 0
    df['SGST'] = 0
    return df

def process_cgst_cn_file(file):
    df = pd.read_excel(file)
    df['CGST'] = -df['Debit'].fillna(0).abs()
    df['Taxable Amount'] = -df['Taxable Amount'].abs()
    df = df.rename(columns={'Partner': 'Customer Name', 'Number': 'Invoice Number', 'Label': 'Tax Rate'})
    df['Account'] = 'GST Payable'
    df['Tax Rate'] = df['Tax Rate'].apply(format_cgst_rate)
    df['SGST'] = df['CGST']
    df['IGST'] = 0
    return df

def process_igst_cn_file(file):
    df = pd.read_excel(file)
    df['IGST'] = -df['Debit'].fillna(0).abs()
    df['Taxable Amount'] = -df['Taxable Amount'].abs()
    df = df.rename(columns={'Partner': 'Customer Name', 'Number': 'Invoice Number', 'Label': 'Tax Rate'})
    df['Account'] = 'IGST Payable'
    df['CGST'] = 0
    df['SGST'] = 0
    return df

# --- THE MAIN ENGINE ROUTE ---
def generate_mario_sales_report(files_dict):
    dataframes = []
    file_mapping = {
        'file_b2b_cgst': process_cgst_file,
        'file_b2b_igst': process_igst_file,
        'file_b2c_cgst': process_cgst_file,
        'file_b2c_igst': process_igst_file,
        'file_b2b_cn_cgst': process_cgst_cn_file,
        'file_b2b_cn_igst': process_igst_cn_file
    }
    
    for key, process_function in file_mapping.items():
        if key in files_dict and files_dict[key].filename != '':
            dataframes.append(process_function(files_dict[key]))
            
    if not dataframes:
        raise ValueError("Please upload at least one valid file.")
        
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    if 'GSTIN' not in combined_df.columns:
        combined_df['GSTIN'] = None
        
    combined_df[['IGST', 'CGST', 'SGST', 'Taxable Amount']] = combined_df[['IGST', 'CGST', 'SGST', 'Taxable Amount']].fillna(0)
    combined_df['Total'] = combined_df['Taxable Amount'] + combined_df['IGST'] + combined_df['CGST'] + combined_df['SGST']
    
    final_columns = ['Customer Name', 'GSTIN', 'Date', 'Reference', 'Invoice Number', 'Account', 'Tax Rate', 'Total', 'Taxable Amount', 'IGST', 'CGST', 'SGST']
    final_df = combined_df[final_columns]
    
    totals = {
        'Customer Name': 'GRAND TOTAL',
        'Total': final_df['Total'].sum(),
        'Taxable Amount': final_df['Taxable Amount'].sum(),
        'IGST': final_df['IGST'].sum(),
        'CGST': final_df['CGST'].sum(),
        'SGST': final_df['SGST'].sum()
    }
    
    summary_row = pd.DataFrame([totals])
    final_df = pd.concat([final_df, summary_row], ignore_index=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False)
    output.seek(0)
    
    return output