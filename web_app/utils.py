import os
import json
import sqlite3
from typing import List

# Try to import PyPDF2 for PDF processing. If not available, raise ImportError when needed.
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

# Reuse split_text_by_paragraph from existing splitter tool
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '拆分工具'))
from novel_splitter import split_text_by_paragraph


def extract_text(file_path: str) -> str:
    """Extract text from a txt or pdf file."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    if ext == '.pdf':
        if PyPDF2 is None:
            raise ImportError('PyPDF2 is required to read PDF files.')
        text = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text())
        return '\n'.join(text)
    raise ValueError('Unsupported file type: %s' % ext)


def split_text(text: str) -> List[str]:
    """Split text into chunks using existing utility."""
    return split_text_by_paragraph(text, language='ko')


def translate_chunks(chunks: List[str]) -> List[str]:
    """Translate chunks. Placeholder implementation."""
    # TODO: integrate with real translator. Currently just returns the same text.
    return [chunk for chunk in chunks]
