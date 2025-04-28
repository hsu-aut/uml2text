import os
import shutil
import pandas as pd

# Define file paths
excel_path = r"C:\Users\Reinpold\Documents\GitHub\re2text\generated_text_files\unibw\all_xmi\Ergebnisse.xlsx"
source_dir = r"C:\Users\Reinpold\Documents\GitHub\re2text\input_files\unibw\all_xmi"
target_dir_struct = os.path.join(source_dir, "struct")
target_dir_act = os.path.join(source_dir, "act")

# Ensure target directories exist
os.makedirs(target_dir_struct, exist_ok=True)
os.makedirs(target_dir_act, exist_ok=True)

# Read the Excel file
df = pd.read_excel(excel_path)

# List to keep track of failed moves
failed_moves = []
progess = 0

# Iterate over each row in the dataframe
for index, row in df.iterrows():
    filename = row['Dateiname']
    diagram_type = row['Diagrammtyp']
    
    # Determine target directory based on diagram type
    if diagram_type == 'Struktur':
        target_path = os.path.join(target_dir_struct, filename)
    elif diagram_type == 'Ablauf':
        target_path = os.path.join(target_dir_act, filename)
    else:
        failed_moves.append((filename, "Unknown diagram type"))
        continue
    
    # Construct source file path
    source_path = os.path.join(source_dir, filename)
    
    # Move the file
    try:
        if os.path.exists(source_path):
            shutil.move(source_path, target_path)
        else:
            failed_moves.append((filename, "Source file not found"))
    except Exception as e:
        failed_moves.append((filename, str(e)))
    progess += 1
    print(f"Progress: {progess}/{len(df)}")


# Output failed moves
if failed_moves:
    print("Failed to move the following files:")
    for file, reason in failed_moves:
        print(f"{file}: {reason}")
else:
    print("All files moved successfully.")