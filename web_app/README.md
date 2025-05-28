# Web App

This directory contains a simple Flask-based web interface for uploading novels
and previewing their translations.

## Features

- Upload TXT or PDF files.
- Files are stored in a local SQLite database per user (demo uses a single user).
- Uploaded text is automatically split into smaller chunks using the
  `split_text` helper which now detects the language and allows custom chunk
  size.
- Each chunk is translated through the simple translator from the `翻译工具`
  package if API settings are available. Otherwise the original text is shown.

## Usage

```bash
pip install flask werkzeug PyPDF2
python -m web_app.app
```

Open `http://localhost:5000` in your browser, upload a novel file and the
preview page will display the split text and its translation if a translation
API is configured.
