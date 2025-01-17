import os
import yaml
import logging
from termcolor import cprint
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import ProcessPoolExecutor

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import (
    PDFMinerLoader,
    Docx2txtLoader,
    TextLoader,
    JSONLoader,
    EverNoteLoader,
    UnstructuredEmailLoader,
    UnstructuredCSVLoader,
    UnstructuredExcelLoader
)

ENABLE_PRINT = True

def my_cprint(*args, **kwargs):
    if ENABLE_PRINT:
        filename = "document_processor.py"
        modified_message = f"{filename}: {args[0]}"
        cprint(modified_message, *args[1:], **kwargs)

ROOT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
SOURCE_DIRECTORY = f"{ROOT_DIRECTORY}/Docs_for_DB"
INGEST_THREADS = os.cpu_count() or 8

DOCUMENT_MAP = {
    ".pdf": PDFMinerLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
    ".json": JSONLoader,
    ".enex": EverNoteLoader,
    ".eml": UnstructuredEmailLoader,
    ".msg": UnstructuredEmailLoader,
    ".csv": UnstructuredCSVLoader,
    ".xls": UnstructuredExcelLoader,
    ".xlsx": UnstructuredExcelLoader,
}

def load_single_document(file_path: str) -> Document:
    file_extension = os.path.splitext(file_path)[1]
    loader_class = DOCUMENT_MAP.get(file_extension)
    if loader_class:
        if file_extension == ".txt":
            loader = loader_class(file_path, encoding='utf-8')
        else:
            loader = loader_class(file_path)
    else:
        raise ValueError("Document type is undefined")
    
    document = loader.load()[0]
    
    return document

def load_document_batch(filepaths):
    with ThreadPoolExecutor(len(filepaths)) as exe:
        futures = [exe.submit(load_single_document, name) for name in filepaths]
        data_list = [future.result() for future in futures]
    return (data_list, filepaths)

def load_documents(source_dir: str) -> list[Document]:
    all_files = os.listdir(source_dir)
    paths = [os.path.join(source_dir, file_path) for file_path in all_files if os.path.splitext(file_path)[1] in DOCUMENT_MAP.keys()]
    
    n_workers = min(INGEST_THREADS, max(len(paths), 1))
    my_cprint(f"Number of workers assigned: {n_workers}", "magenta")
    chunksize = round(len(paths) / n_workers)
    docs = []
    
    with ProcessPoolExecutor(n_workers) as executor:
        futures = [executor.submit(load_document_batch, paths[i : (i + chunksize)]) for i in range(0, len(paths), chunksize)]
        for future in as_completed(futures):
            contents, _ = future.result()
            docs.extend(contents)
            my_cprint(f"Number of files loaded: {len(docs)}", "magenta")
    
    return docs

def split_documents(documents):
    logging.info("Splitting documents...")
    
    # Read chunk size and chunk overlap from config.yaml
    with open("config.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)
        chunk_size = config["chunk_size"]
        chunk_overlap = config["chunk_overlap"]
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    texts = text_splitter.split_documents(documents)
    
    my_cprint("Splitting chunks completed.", "magenta")
    my_cprint(f"Number of Chunks: {len(texts)}", "magenta")
    
    chunk_sizes = [len(text.page_content) for text in texts]
    min_size = min(chunk_sizes)
    average_size = sum(chunk_sizes) / len(texts)
    max_size = max(chunk_sizes)
    
    my_cprint(f"Minimum Chunk Size: {min_size}", "magenta")
    my_cprint(f"Maximum Chunk Size: {max_size}", "magenta")
    
    size_ranges = range(1, max_size+1, 100)
    for size_range in size_ranges:
        lower_bound = size_range
        upper_bound = size_range + 99
        count = sum(lower_bound <= size <= upper_bound for size in chunk_sizes)
        my_cprint(f"Chunks between {lower_bound} and {upper_bound} characters: {count}", "magenta")
    
    return texts

if __name__ == "__main__":
    documents = load_documents(SOURCE_DIRECTORY)
    split_documents(documents)
