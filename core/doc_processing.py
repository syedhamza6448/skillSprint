import os
import re
import uuid
import hashlib
import fitz  # PyMuPDF
from docx import Document
from core.db import setup_db, insert_document, insert_chunks, document_exists

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def get_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def validate_document(filepath):
    if not os.path.isfile(filepath):
        raise ValueError(f"File not found: {filepath}")
    
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ['.pdf', '.docx']:
        raise ValueError(f"Unsupported file type: {ext}")
        
    size = os.path.getsize(filepath)
    if size == 0:
        raise ValueError("File is empty")
    if size > MAX_FILE_SIZE:
        raise ValueError("File size exceeds 10MB limit")
        
    file_hash = get_file_hash(filepath)
    if document_exists(file_hash):
        raise ValueError("Document already exists (duplicate hash)")
        
    return file_hash, ext

def extract_metadata(text):
    version = "1.0"
    effective_date = "Unknown"
    
    version_match = re.search(r'Version:\s*([^\s\|]+)', text, re.IGNORECASE)
    if version_match:
        version = version_match.group(1)
        
    date_match = re.search(r'Effective:\s*([^\s\n]+)', text, re.IGNORECASE)
    if date_match:
        effective_date = date_match.group(1)
        
    return version, effective_date

def parse_pdf(filepath):
    doc = fitz.open(filepath)
    blocks = []
    
    for page_num, page in enumerate(doc):
        text_blocks = page.get_text("blocks")
        # Sort blocks vertically, then horizontally
        text_blocks.sort(key=lambda b: (b[1], b[0]))
        for b in text_blocks:
            if b[6] == 0:  # text block
                text = b[4].strip()
                if text:
                    for line in text.split('\n'):
                        line = line.strip()
                        if line:
                            blocks.append({
                                'text': line,
                                'page': page_num + 1
                            })
    return blocks

def parse_docx(filepath):
    doc = Document(filepath)
    blocks = []
    
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if text:
            blocks.append({
                'text': text,
                'page': 1  # DOCX doesn't natively expose pages this simply
            })
    return blocks

def chunk_document(doc_id, raw_blocks, version):
    chunks = []
    current_chunk = None
    
    # Matches headings like "1.1 General Conduct", "1. Welcome", "2.1.3 Details"
    heading_pattern = re.compile(r'^(\d+(?:\.\d+)*)\.?\s+(.+)')
    
    for block in raw_blocks:
        text = block['text']
        page = block['page']
        
        match = heading_pattern.match(text)
        if match:
            # Save previous chunk if exists
            if current_chunk and current_chunk['text'].strip():
                chunks.append(current_chunk)
                
            section = match.group(1)
            heading_text = text
            current_chunk = {
                'chunk_id': str(uuid.uuid4()),
                'doc_id': doc_id,
                'section': section,
                'heading': heading_text,
                'page': page,
                'version': version,
                'text': heading_text + '\n'
            }
        else:
            if current_chunk:
                current_chunk['text'] += text + '\n'
            else:
                # Top matter before any numbered heading
                current_chunk = {
                    'chunk_id': str(uuid.uuid4()),
                    'doc_id': doc_id,
                    'section': '0',
                    'heading': 'Metadata/Intro',
                    'page': page,
                    'version': version,
                    'text': text + '\n'
                }
                
    if current_chunk and current_chunk['text'].strip():
        chunks.append(current_chunk)
        
    return chunks

def process_all(folder_path):
    setup_db()
    
    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)
        
        if not os.path.isfile(filepath):
            continue
            
        ext = os.path.splitext(filepath)[1].lower()
        if ext not in ['.pdf', '.docx']:
            continue
            
        print(f"Processing {filename}...")
        try:
            file_hash, file_type = validate_document(filepath)
            
            if file_type == '.pdf':
                raw_blocks = parse_pdf(filepath)
            else:
                raw_blocks = parse_docx(filepath)
                
            # Extract metadata from the first few blocks
            full_text_start = "\n".join([b['text'] for b in raw_blocks[:20]])
            version, effective_date = extract_metadata(full_text_start)
            
            doc_id = str(uuid.uuid4())
            
            doc_data = {
                'doc_id': doc_id,
                'filename': filename,
                'file_type': file_type,
                'version': version,
                'effective_date': effective_date,
                'file_hash': file_hash
            }
            
            chunks = chunk_document(doc_id, raw_blocks, version)
            
            insert_document(doc_data)
            insert_chunks(chunks)
            print(f"  -> Successfully processed {len(chunks)} chunks.")
            
        except Exception as e:
            print(f"  -> Error processing {filename}: {e}")
