import boto3
import pandas as pd
from openpyxl import Workbook
import os
from dotenv import load_dotenv

load_dotenv()

def analyze_table_with_textract(pdf_path, output_csv_path, aws_access_key_id, aws_secret_access_key):
    # Initialize AWS Textract client
    textract = boto3.client(
        'textract',
        region_name='us-east-1',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    # Read the file
    with open(pdf_path, 'rb') as file:
        img_bytes = file.read()

    try:
        # Make the API call
        response = textract.analyze_document(
            Document={'Bytes': img_bytes},
            FeatureTypes=['TABLES']
        )

        # Debug: Print total number of blocks
        blocks = response['Blocks']
        print(f"Total blocks found: {len(blocks)}")
        
        # Debug: Print block types
        block_types = {}
        for block in blocks:
            block_type = block['BlockType']
            block_types[block_type] = block_types.get(block_type, 0) + 1
        print("\nBlock types found:")
        for block_type, count in block_types.items():
            print(f"{block_type}: {count}")

        # Create a dictionary to store tables
        tables = {}
        current_table = None
        
        # First, identify tables and their cells
        for block in blocks:
            if block['BlockType'] == 'TABLE':
                current_table = block['Id']
                tables[current_table] = {}
            elif block['BlockType'] == 'CELL' and current_table:
                if 'RowIndex' in block and 'ColumnIndex' in block:
                    row_index = block['RowIndex']
                    col_index = block['ColumnIndex']
                    
                    # Get cell content
                    if 'Relationships' in block:
                        for relationship in block['Relationships']:
                            if relationship['Type'] == 'CHILD':
                                child_ids = relationship['Ids']
                                cell_content = []
                                for child_id in child_ids:
                                    child_block = next((b for b in blocks if b['Id'] == child_id), None)
                                    if child_block and child_block['BlockType'] == 'WORD':
                                        cell_content.append(child_block['Text'])
                                text = ' '.join(cell_content)
                                tables[current_table][(row_index, col_index)] = text
                    else:
                        # Handle cells without relationships
                        text = block.get('Text', '')
                        tables[current_table][(row_index, col_index)] = text

        # Debug: Print table information
        print(f"\nNumber of tables found: {len(tables)}")
        
        if not tables:
            print("No tables were detected in the document!")
            return None

        # Process the first table (or you can process all tables if needed)
        table_dict = next(iter(tables.values()))
        
        # Determine table dimensions
        max_row = max(k[0] for k in table_dict.keys()) if table_dict else 0
        max_col = max(k[1] for k in table_dict.keys()) if table_dict else 0
        
        print(f"\nTable dimensions: {max_row} rows x {max_col} columns")

        # Create the table data
        table_data = []
        for i in range(1, max_row + 1):
            row = []
            for j in range(1, max_col + 1):
                cell_content = table_dict.get((i, j), '')
                row.append(cell_content)
            table_data.append(row)

        # Convert to DataFrame and save
        df = pd.DataFrame(table_data)
        
        # Debug: Print sample of data
        print("\nFirst few rows of extracted data:")
        print(df.head())
        
        # Save to CSV only if we have data
        if not df.empty:
            df.to_csv(output_csv_path, index=False, header=False)
            print(f'\nTable data has been saved to {output_csv_path}')
        else:
            print("No data to save - DataFrame is empty")

        return df

    except Exception as e:
        print(f"Error processing document: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

# Example usage
if __name__ == "__main__":
    
    pdf_path = './raw_data/koran/KC_AMBON/November/3.Rekening Koran_604_THT_112024/1.jpg'
    output_csv_path = 'output_table.csv'
    
    df = analyze_table_with_textract(
        pdf_path, 
        output_csv_path,
        os.getenv('aws_access_key_id'),
        os.getenv('aws_secret_access_key')
    )