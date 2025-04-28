import os

# Define target directories
target_dirs = [
    r"C:\Users\Reinpold\Documents\GitHub\re2text\output_files\unibw\all_xmi\struct",
    r"C:\Users\Reinpold\Documents\GitHub\re2text\output_files\unibw\all_xmi\act"
]

# Prefix to remove
prefix = "gen_"

# List to keep track of failed renames
failed_renames = []

# Iterate over each target directory
for target_dir in target_dirs:
    if os.path.exists(target_dir):
        for filename in os.listdir(target_dir):
            if filename.startswith(prefix):
                old_path = os.path.join(target_dir, filename)
                new_filename = filename[len(prefix):]  # Remove prefix
                new_path = os.path.join(target_dir, new_filename)
                
                try:
                    os.rename(old_path, new_path)
                except Exception as e:
                    failed_renames.append((filename, str(e)))
    else:
        print(f"Directory not found: {target_dir}")

# Output failed renames
if failed_renames:
    print("Failed to rename the following files:")
    for file, reason in failed_renames:
        print(f"{file}: {reason}")
else:
    print("All files renamed successfully.")