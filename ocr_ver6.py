import boto3
import pandas as pd
from openpyxl import Workbook
import os
from dotenv import load_dotenv
import csv

# Load environment variables
load_dotenv()

def analyze_financial_statement(image_path, aws_access_key_id, aws_secret_access_key):
    """Analyze a financial statement image with AWS Textract with enhanced table detection"""
    textract = boto3.client(
        'textract',
        region_name='us-east-1',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    with open(image_path, 'rb') as file:
        img_bytes = file.read()

    try:
        response = textract.analyze_document(
            Document={'Bytes': img_bytes},
            FeatureTypes=['TABLES', 'FORMS']
        )

        blocks = response['Blocks']
        print(f"\nProcessing image: {image_path}")
        print(f"Total blocks detected: {len(blocks)}")

        transactions = []
        current_row = {}
        
        columns = ['Tanggal Transaksi', 'Uraian Transaksi', 'Teller', 'Debet', 'Kredit', 'Saldo']

        for block in blocks:
            if block['BlockType'] == 'CELL':
                if 'RowIndex' in block and 'ColumnIndex' in block:
                    row_index = block['RowIndex']
                    col_index = block['ColumnIndex']
                    
                    cell_text = ''
                    if 'Relationships' in block:
                        for relationship in block['Relationships']:
                            if relationship['Type'] == 'CHILD':
                                for child_id in relationship['Ids']:
                                    child_block = next((b for b in blocks if b['Id'] == child_id), None)
                                    if child_block and child_block['BlockType'] == 'WORD':
                                        cell_text += child_block['Text'] + ' '
                                cell_text = cell_text.strip()
                    else:
                        cell_text = block.get('Text', '').strip()

                    if row_index > 1:
                        col_name = columns[col_index - 1] if col_index <= len(columns) else f'Column{col_index}'
                        
                        if col_index == 1:
                            if current_row:
                                transactions.append(current_row)
                            current_row = {col: '' for col in columns}
                        
                        current_row[col_name] = cell_text

        if current_row:
            transactions.append(current_row)

        df = pd.DataFrame(transactions)
        
        if not df.empty:
            for col in ['Debet', 'Kredit', 'Saldo']:
                if col in df.columns:
                    df[col] = df[col].replace('', '0')
                    df[col] = df[col].str.replace(',', '').str.replace('.00', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    except Exception as e:
        print(f"Error processing document: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

# Main execution
if __name__ == "__main__":
    main_path = './raw_data/koran/KC_BANDA_ACEH/Desember'
    
    for dir in os.listdir(main_path):
        dir_path = os.path.join(main_path, dir)
        
        if os.path.isdir(dir_path):
            combined_output_path = os.path.join(dir_path, 'combined_transactions.csv')

            # Cek jika file output gabungan sudah ada
            if os.path.exists(combined_output_path):
                print(f"📂 Folder '{dir}' sudah diproses sebelumnya. Melewati folder ini.")
                continue
            
            dir_images = [f for f in os.listdir(dir_path) if f.endswith('.jpg')]
            sorted_images = sorted(dir_images, key=lambda x: int(x.split('.')[0]))
            
            all_transactions = []
            
            for i, img in enumerate(sorted_images):
                image_path = os.path.join(dir_path, img)
                output_csv_path = os.path.join(dir_path, f'output_table{i}.csv')
                
                print(f"\nProcessing {img} ({i+1}/{len(sorted_images)})")
                
                df = analyze_financial_statement(
                    image_path,
                    os.getenv('aws_access_key_id'),
                    os.getenv('aws_secret_access_key')
                )
                
                if df is not None and not df.empty:
                    all_transactions.append(df)
                    
                    df.to_csv(output_csv_path, index=False, quoting=csv.QUOTE_ALL, encoding='utf-8')
                    print(f"✅ Data tersimpan di {output_csv_path}")
            
            if all_transactions:
                combined_df = pd.concat(all_transactions, ignore_index=True)
                combined_df.to_csv(combined_output_path,  index=False, quoting=csv.QUOTE_ALL, encoding='utf-8')
                print(f"\n📦 Hasil gabungan untuk '{dir}' disimpan di {combined_output_path}")
