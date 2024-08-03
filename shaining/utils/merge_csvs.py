import argparse
import os
import pandas as pd
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from io_helpers import sort_files

"""
Run using:
python merge_csv.py path_to_your_csv_directory output.csv

"""

def merge_csvs(input_dir, output_csv):
    parent_dir, name_prefix = os.path.split(input_dir)
    filename_list = os.listdir(str(parent_dir))
    filename_list = [filename for filename in filename_list if filename.startswith(name_prefix) and filename.endswith(".csv")]


    result = pd.DataFrame(columns=['log'])
    for filename in filename_list:
        df = pd.read_csv(os.path.join(parent_dir, filename))
        result = result.merge(df, on='log', how='outer') 
        print(df.shape)
    result.to_csv(output_csv, index=False)
    print(f"Saved dataframe with {result.shape} in {output_csv}")

# Example usage
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert JSON files in a directory to a CSV file.')
    parser.add_argument('csv_dir', type=str, help='The directory containing JSON files')
    parser.add_argument('output_csv', type=str, help='The output CSV file path')
    args = parser.parse_args()

    merge_csvs(args.csv_dir, args.output_csv)
