import os
import zipfile
from langchain_community.document_loaders import Docx2txtLoader

ZIP_FILES = ["Detailed_Performance_Reports.zip", "IT_Junior_Entry_Reports.zip"]
DATA_FOLDER = "performance_reviews"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

for zip_file in ZIP_FILES:
    if os.path.exists(zip_file):
        print(f"Unzipping {zip_file}...")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(DATA_FOLDER)
    else:
        print(f"Warning: {zip_file} not found. Make sure it's in this folder.")

print(f"Files extracted to '{DATA_FOLDER}/'")

documents = []
files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".docx")]

print(f"Found {len(files)} documents. Processing...")

for filename in files:
    file_path = os.path.join(DATA_FOLDER, filename)

    loader = Docx2txtLoader(file_path)
    docs = loader.load()
    
    parts = filename.split("_")
    employee_name = f"{parts[0]} {parts[1]}"
    
    for doc in docs:
        doc.metadata["employee"] = employee_name
        doc.metadata["source"] = filename
        # We add a tag "type" so we can filter for just reports later if we add other docs
        doc.metadata["type"] = "performance_report" 
        
    documents.extend(docs)

print(f"\nSUCCESS: Loaded {len(documents)} employee reports.")


print("\n--- PREVIEW OF FIRST DOCUMENT ---")
first_doc = documents[0]
print(f"METADATA (Context): {first_doc.metadata}")
print(f"CONTENT (Snippet): {first_doc.page_content[:300]}...") 