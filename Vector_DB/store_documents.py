import os
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

DATA_FOLDER = "performance_reviews"
DB_PATH = "./chroma_db_local"  

print("--- LOADING DOCUMENTS ---")
documents = []

if not os.path.exists(DATA_FOLDER):
    print(f"Error: Folder '{DATA_FOLDER}' not found. Did you run Step 1?")
    exit()

files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".docx")]

for filename in files:
    file_path = os.path.join(DATA_FOLDER, filename)
    loader = Docx2txtLoader(file_path)
    docs = loader.load()

    parts = filename.split("_")
    name = f"{parts[0]} {parts[1]}"
    date_part = parts[2]
    
    for doc in docs:
        doc.metadata["employee"] = name
        doc.metadata["report_date"] = date_part
        doc.metadata["source"] = filename
        
    documents.extend(docs)

print(f"Loaded {len(documents)} reports.")

print("\n--- CHUNKING TEXT ---")

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100
)

splits = text_splitter.split_documents(documents)
print(f"Split into {len(splits)} chunks.")

embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Create the Database
vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embedding_function,
    persist_directory=DB_PATH
)

print(f"\nSUCCESS! Local Database created at: {DB_PATH}")