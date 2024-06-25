from flask import render_template, request, session, Response
from flask import Flask
import pandas as pd


app2 = Flask(__name__)
app2.config['SECRET_KEY'] = 'your_secret_key_here'


@app2.route('/')
def home():
    return render_template('product-tally.html')

@app2.route('/enter2', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        old_file = request.files['old_file']
        new_file = request.files['new_file']
        
        if old_file and new_file:
            comparison_result = compare_product(old_file, new_file)
            session['comparison_result'] = comparison_result
            return render_template('product-tally-view.html', comparison_result=comparison_result)
    
    return render_template('product-tally.html')

@app2.route('/product-tally', methods=['GET'])
def compare():
    return render_template('product-tally.html')

@app2.route('/download_missing_in_new')
def download_missing_in_new():
    comparison_result = session.get('comparison_result')
    if comparison_result:
        df = pd.DataFrame(comparison_result['missing_in_new'])
        csv_data = df.to_csv(index=False)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=missing_in_shopify.csv"}
        )
    return "Comparison result not found in session"

@app2.route('/download_missing_in_old')
def download_missing_in_old():
    comparison_result = session.get('comparison_result')
    if comparison_result:
        df = pd.DataFrame(comparison_result['missing_in_old'])
        csv_data = df.to_csv(index=False)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=missing_in_bigcommerce.csv"}
        )
    return "Comparison result not found in session"

def compare_product(old_file, new_file):
    old_df = pd.read_csv(old_file, low_memory=False)
    new_df = pd.read_csv(new_file, low_memory=False)
    
    # Convert all columns to string type
    old_df = old_df.astype(str)
    new_df = new_df.astype(str)
    
    # Check if the columns exist in the DataFrames
    if 'Product Code/SKU' not in old_df.columns or 'Product Name' not in old_df.columns:
        print("Required columns do not exist in the Bigcommerce")
        return {}
    if 'Variant SKU' not in new_df.columns or 'Title' not in new_df.columns:
        print("Required columns do not exist in the Shopify")
        return {}
    
    # Rename new file columns to match old file columns
    new_df.rename(columns={
        'Variant SKU': 'Product Code/SKU',
        'Title': 'Product Name',
    }, inplace=True)
    
    # Ensure the key columns have the same data type
    for col in ['Product Code/SKU', 'Product Name']:
        old_df[col] = old_df[col].str.strip()
        new_df[col] = new_df[col].str.strip()
    
    # Set SKU as the index for both dataframes
    old_df.set_index('Product Code/SKU', inplace=True)
    new_df.set_index('Product Code/SKU', inplace=True)
    
    # Merge dataframes based on SKU
    merged_df = pd.merge(old_df, new_df, left_index=True, right_index=True, how='outer', suffixes=('_old', '_new'))
    
    # Find products missing in new file and old file
    missing_in_new = merged_df[merged_df['Product Name_new'].isnull() & merged_df['Product Name_old'].notnull()][['Product Name_old']]
    missing_in_old = merged_df[merged_df['Product Name_old'].isnull() & merged_df['Product Name_new'].notnull()][['Product Name_new']]
    
    result = {
        'missing_in_new': missing_in_new.rename(columns={'Product Name_old': 'Product Name'}).reset_index().to_dict('records'),
        'missing_in_old': missing_in_old.rename(columns={'Product Name_new': 'Product Name'}).reset_index().to_dict('records')
    }
    
    return result

if __name__ == "__main__":
    app2.run(debug=True)
