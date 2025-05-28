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
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '翻译工具'))
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


def _detect_language(text: str) -> str:
    """Very naive language detection between Korean and Chinese/Japanese."""
    for ch in text[:200]:
        if '\uac00' <= ch <= '\ud7a3':
            return 'ko'
    return 'ja'  # Treat Chinese similar to Japanese for splitting


def split_text(text: str, language: str | None = None, max_chars: int = 800) -> List[str]:
    """Split text into chunks using existing utility with optional language."""
    lang = language or _detect_language(text)
    return split_text_by_paragraph(text, language=lang, max_chars=max_chars)


def translate_chunks(chunks: List[str]) -> List[str]:
    """Translate chunks using the simple translator if available."""
    try:
        from simple_translator import SimplifiedApiClient, SimplifiedPromptBuilder
        import config as tconfig

        client = SimplifiedApiClient(api_key=tconfig.API_KEY, api_url=tconfig.API_URL, model_name=tconfig.MODEL_NAME)
        builder = SimplifiedPromptBuilder()
        results: List[str] = []
        for chunk in chunks:
            prompt = builder.build_translation_prompt(korean_text=chunk)
            translated = client.translate_text(prompt=prompt) or ""
            results.append(translated)
        return results
    except Exception:
        # Fallback: return original chunks if translation fails
        return list(chunks)
