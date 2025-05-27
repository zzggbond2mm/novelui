# Web App

This directory contains a simple Flask-based web interface for uploading novels
and previewing their translations.

## Features

- Upload TXT or PDF files.
- Files are stored in a local SQLite database per user (demo uses a single user).
- Uploaded text is split into smaller chunks using the existing splitting
  utility.
- Placeholder translation is generated for each chunk and shown side-by-side
  with the original text.

## Usage

```bash
pip install flask werkzeug PyPDF2
python -m web_app.app
```

Open `http://localhost:5000` in your browser, upload a novel file and the
preview page will display the split text and its translation.

> **Note**: Actual translation should be integrated in `utils.translate_chunks`.
