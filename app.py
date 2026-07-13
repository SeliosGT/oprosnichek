from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- Подключение к базе данных ---
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    # Для локального тестирования
    DATABASE_URL = "postgresql://user:pass@localhost:5432/surveys"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- Инициализация базы данных ---
def init_db():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS answers (
                    id SERIAL PRIMARY KEY,
                    survey_type VARCHAR(50) NOT NULL,
                    answer_data JSONB NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации БД: {e}")

init_db()

# ============================================
# ===== ЭНДПОИНТЫ API =====
# ============================================

# --- Сохранение ответа ---
@app.route('/api/submit', methods=['POST'])
def submit_answer():
    try:
        data = request.json
        survey_type = data.get('surveyType', 'unknown')
        answer_data = data.get('answer', {})

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO answers (survey_type, answer_data) VALUES (%s, %s) RETURNING id",
                (survey_type, json.dumps(answer_data))
            )
            conn.commit()
            new_id = cur.fetchone()[0]
        conn.close()

        return jsonify({"success": True, "id": new_id}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- Получение всех ответов ---
@app.route('/api/answers', methods=['GET'])
def get_answers():
    try:
        survey_type = request.args.get('type', 'all')

        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if survey_type == 'all':
                cur.execute("SELECT id, survey_type, answer_data, status, created_at FROM answers ORDER BY id DESC")
            else:
                cur.execute(
                    "SELECT id, survey_type, answer_data, status, created_at FROM answers WHERE survey_type = %s ORDER BY id DESC",
                    (survey_type,)
                )

            rows = cur.fetchall()
            result = []
            for row in rows:
                result.append({
                    "id": row['id'],
                    "surveyType": row['survey_type'],
                    "answer": row['answer_data'],
                    "status": row['status'],
                    "createdAt": row['created_at'].isoformat() if row['created_at'] else None
                })
        conn.close()
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Обновление статуса ---
@app.route('/api/update-status', methods=['POST'])
def update_status():
    try:
        data = request.json
        answer_id = data.get('id')
        status = data.get('status')

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE answers SET status = %s WHERE id = %s", (status, answer_id))
            conn.commit()
        conn.close()

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- Удаление всех ответов ---
@app.route('/api/clear-all', methods=['POST'])
def clear_all():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM answers")
            conn.commit()
        conn.close()
        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# ===== ОТДАЧА СТАТИЧЕСКИХ ФАЙЛОВ =====
# ============================================

# Главная страница
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Опросники</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: #0b1a2e;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 2rem;
            }
            .container {
                max-width: 600px;
                width: 100%;
                background: white;
                border-radius: 32px;
                padding: 3rem;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
            }
            h1 { font-size: 2rem; color: #0b1a2e; margin-bottom: 0.5rem; }
            .subtitle { color: #4a5e78; margin-bottom: 2rem; }
            .links { display: flex; flex-direction: column; gap: 1rem; }
            .link-card {
                display: block;
                padding: 1.2rem 1.5rem;
                border-radius: 16px;
                text-decoration: none;
                color: white;
                font-weight: 600;
                transition: 0.3s;
                font-size: 1.1rem;
            }
            .link-card:hover { transform: scale(1.02); }
            .link-card.discipline { background: #7c3aed; }
            .link-card.discipline:hover { background: #6d28d9; }
            .link-card.hr { background: #059669; }
            .link-card.hr:hover { background: #047857; }
            .link-card.admin { background: #2563eb; }
            .link-card.admin:hover { background: #1d4ed8; }
            .link-card .icon { font-size: 1.5rem; margin-right: 0.5rem; }
            .footer { margin-top: 2rem; font-size: 0.75rem; color: #8b9db0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 Опросники</h1>
            <p class="subtitle">Выберите нужную анкету</p>
            <div class="links">
                <a href="/survey1.html" class="link-card discipline">
                    <span class="icon">🏛️</span> Дисциплинарный инспектор
                </a>
                <a href="/survey2.html" class="link-card hr">
                    <span class="icon">👔</span> HR-менеджер
                </a>
                <a href="/admin.html" class="link-card admin">
                    <span class="icon">🔒</span> Панель администратора
                </a>
            </div>
            <div class="footer">Все данные сохраняются в базе данных · Доступ 24/7</div>
        </div>
    </body>
    </html>
    '''

# Отдаём HTML-файлы и картинки
@app.route('/<path:path>')
def serve_static(path):
    # Проверяем, существует ли файл
    if os.path.exists(path):
        # Определяем MIME-тип
        if path.endswith('.html'):
            return send_from_directory('.', path, mimetype='text/html; charset=utf-8')
        elif path.endswith('.png'):
            return send_from_directory('.', path, mimetype='image/png')
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            return send_from_directory('.', path, mimetype='image/jpeg')
        elif path.endswith('.css'):
            return send_from_directory('.', path, mimetype='text/css')
        elif path.endswith('.js'):
            return send_from_directory('.', path, mimetype='application/javascript')
        else:
            return send_from_directory('.', path)
    else:
        return f"Файл не найден: {path}", 404

# ============================================
# ===== ЗАПУСК =====
# ============================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
