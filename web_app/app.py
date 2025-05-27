from flask import Flask, request, render_template, redirect, url_for
import os
from werkzeug.utils import secure_filename
from . import db, utils

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'txt', 'pdf'}


@app.before_first_request
def setup():
    db.init_db()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    user_id = 1  # Demo purpose, single user
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(save_path)

        text = utils.extract_text(save_path)
        chunks = utils.split_text(text)
        translations = utils.translate_chunks(chunks)

        conn = db.get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO novels (user_id, title, filename) VALUES (?, ?, ?)', (user_id, filename, filename))
        novel_id = cur.lastrowid
        for idx, (orig, trans) in enumerate(zip(chunks, translations), start=1):
            cur.execute('INSERT INTO chapters (novel_id, chapter_index, original_text, translated_text) VALUES (?, ?, ?, ?)',
                        (novel_id, idx, orig, trans))
        conn.commit()
        conn.close()

        return redirect(url_for('preview', novel_id=novel_id))
    return 'Invalid file type', 400


@app.route('/preview/<int:novel_id>')
def preview(novel_id):
    conn = db.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT title FROM novels WHERE id=?', (novel_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return 'Novel not found', 404
    title = row[0]
    cur.execute('SELECT chapter_index, original_text, translated_text FROM chapters WHERE novel_id=? ORDER BY chapter_index', (novel_id,))
    chapters = cur.fetchall()
    conn.close()
    return render_template('preview.html', title=title, chapters=chapters)


if __name__ == '__main__':
    app.run(debug=True)
