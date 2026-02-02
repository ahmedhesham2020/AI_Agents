
import pandas as pd
import argparse
import sys

# This script is a template for the excel-data-extractor sub-agent.
# The sub-agent will dynamically write and execute a version of this script
# based on the user's specific data extraction requirements.
#
# Required libraries:
# pip install pandas openpyxl

def extract_excel_data(source_file, dest_file, sheet_name, filter_query, columns):
    """
    Reads data from a source Excel file, filters it based on a query,
    selects specific columns, and saves the result to a new Excel file.

    Args:
        source_file (str): Path to the source .xlsx or .xlsm file.
        dest_file (str): Path to save the new .xlsx file.
        sheet_name (str): The name of the sheet to read data from.
        filter_query (str): A pandas query string to filter the data (e.g., 'Country == "USA"').
                             If None, no filtering is applied.
        columns (list): A list of column names to include in the final output.
                        If None, all columns are included.
    """
    try:
        # Read the specified sheet from the Excel file.
        # The 'openpyxl' engine is required for .xlsx/.xlsm files.
        print(f"Reading sheet '{sheet_name}' from '{source_file}'...")
        df = pd.read_excel(source_file, sheet_name=sheet_name, engine='openpyxl')
        print("Successfully read the file.")

        # Apply the filter query if one is provided.
        if filter_query:
            print(f"Applying filter query: '{filter_query}'...")
            df = df.query(filter_query)
            print(f"Data filtered. {len(df)} rows remaining.")

        # Select specific columns if a list is provided.
        if columns:
            # Filter out any requested columns that don't actually exist
            existing_columns = [col for col in columns if col in df.columns]
            missing_columns = [col for col in columns if col not in df.columns]
            if missing_columns:
                print(f"Warning: The following requested columns were not found and will be ignored: {missing_columns}")
            
            if not existing_columns:
                print("Error: None of the requested columns exist in the sheet. Aborting.")
                sys.exit(1)

            print(f"Selecting columns: {existing_columns}...")
            df = df[existing_columns]

        # Save the resulting DataFrame to a new Excel file.
        print(f"Saving extracted data to '{dest_file}'...")
        df.to_excel(dest_file, index=False)
        print("Data extraction complete. New file saved successfully.")

    except FileNotFoundError:
        print(f"Error: The file '{source_file}' was not found.", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        # This can happen if the sheet_name doesn't exist
        print(f"Error: Could not find the sheet named '{sheet_name}'. Please check the sheet name.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A flexible tool to extract data from Excel files.")
    
    parser.add_argument("source_file", help="Path to the source Excel file (.xlsx, .xlsm).")
    parser.add_argument("dest_file", help="Path to the destination Excel file.")
    parser.add_argument("--sheet", required=True, help="Name of the sheet to read from.")
    parser.add_argument("--query", help="Pandas query string for filtering rows (e.g., '"Country == \"USA\""').")
    parser.add_argument("--cols", nargs='+', help="A space-separated list of column names to extract.")

    args = parser.parse_args()

    extract_excel_data(
        source_file=args.source_file,
        dest_file=args.dest_file,
        sheet_name=args.sheet,
        filter_query=args.query,
        columns=args.cols
    )
