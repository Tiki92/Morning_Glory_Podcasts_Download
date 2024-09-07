import os
import re

# Directory containing the podcast files
podcast_dir = "podcasts"

# Function to format date in the title
def format_date_in_title(title):
    # Find dates in various formats: d.m.yyyy, dd.mm.yyyy, d.m.yyyy
    match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', title)
    if match:
        day, month, year = match.groups()
        # Convert to yyyy.mm.dd format, ensuring two digits for day and month
        return f"{year}.{month.zfill(2)}.{day.zfill(2)}"
    return None

# Function to rename files to include formatted date
def rename_files_with_date():
    for filename in os.listdir(podcast_dir):
        old_file_path = os.path.join(podcast_dir, filename)
        
        # Skip directories
        if os.path.isdir(old_file_path):
            continue
        
        # Extract and format the date from the title
        title = os.path.splitext(filename)[0]
        date_str = format_date_in_title(title)
        
        if date_str:
            # Create new filename with formatted date
            new_title = re.sub(r'\d{1,2}\.\d{1,2}\.\d{4}', date_str, title)
            new_filename = f"{new_title}.mp3"  # Adjust extension based on file type
            new_file_path = os.path.join(podcast_dir, new_filename)
            
            # Rename the file
            os.rename(old_file_path, new_file_path)
            print(f"Renamed file to: {new_file_path}")
        else:
            print(f"No date found in filename: {filename}")

# Run the rename function
rename_files_with_date()

print("File renaming completed.")
