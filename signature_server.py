import os
import base64
import uuid
import threading
import time
import json
from io import BytesIO
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app)

# Папки для хранения
SIGNATURES_FOLDER = "signatures"
FORMS_FOLDER = "forms"
os.makedirs(SIGNATURES_FOLDER, exist_ok=True)
os.makedirs(FORMS_FOLDER, exist_ok=True)

# Keep-alive функция
def keep_alive():
    url = "https://signature-server-87mz.onrender.com/health"
    while True:
        time.sleep(600)
        try:
            import requests
            requests.get(url, timeout=5)
            print("✅ Keep-alive ping отправлен")
        except:
            print("❌ Ошибка пинга")

threading.Thread(target=keep_alive, daemon=True).start()

# =====================
# ПОДПИСИ
# =====================
@app.route('/save_signature', methods=['POST', 'OPTIONS'])
def save_signature():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        data = request.json
        image_data = data.get('signature')
        user_id = data.get('user_id', 'unknown')
        
        if not image_data:
            return jsonify({'error': 'No image'}), 400
        
        if ',' in image_data:
            base64_data = image_data.split(',')[1]
        else:
            base64_data = image_data
        
        image_bytes = base64.b64decode(base64_data)
        
        img = Image.open(BytesIO(image_bytes))
        img.thumbnail((300, 150), Image.Resampling.LANCZOS)
        
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signature_{user_id}_{timestamp}_{unique_id}.jpg"
        filepath = os.path.join(SIGNATURES_FOLDER, filename)
        img.save(filepath, 'JPEG', quality=70, optimize=True)
        
        base_url = os.environ.get('BASE_URL', 'https://signature-server-87mz.onrender.com')
        image_url = f"{base_url}/get_signature/{filename}"
        
        return jsonify({'status': 'ok', 'url': image_url})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_signature/<filename>', methods=['GET'])
def get_signature(filename):
    filepath = os.path.join(SIGNATURES_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return jsonify({'error': 'File not found'}), 404

# =====================
# ХРАНЕНИЕ ДАННЫХ ФОРМЫ
# =====================
@app.route('/save_form_data', methods=['POST', 'OPTIONS'])
def save_form_data():
    """Сохраняет данные формы и возвращает ID"""
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Получаем данные из запроса
        data = request.get_json()
        
        # Проверяем, что данные получены
        if not data:
            print("❌ Нет данных в запросе")
            return jsonify({'error': 'No data received'}), 400
        
        print(f"📥 Получены данные: {data.keys() if isinstance(data, dict) else type(data)}")
        
        # Извлекаем form_data (может быть в разных местах)
        if 'form_data' in data:
            form_data = data['form_data']
        else:
            form_data = data
        
        if not form_data:
            print("❌ Нет form_data")
            return jsonify({'error': 'No form_data'}), 400
        
        # Проверяем обязательные поля
        if not form_data.get('name'):
            print("❌ Нет поля name")
            return jsonify({'error': 'Missing required field: name'}), 400
        
        # Генерируем session_id
        session_id = str(uuid.uuid4())
        
        # Сохраняем данные
        filepath = os.path.join(FORMS_FOLDER, f"{session_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(form_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Данные сохранены: {session_id}")
        
        # Запланируем удаление через 1 час
        def delete_later():
            time.sleep(3600)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"🗑️ Удалены данные: {session_id}")
        
        threading.Thread(target=delete_later, daemon=True).start()
        
        return jsonify({
            'session_id': session_id,
            'status': 'ok'
        })
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'signatures': len(os.listdir(SIGNATURES_FOLDER)),
        'forms': len(os.listdir(FORMS_FOLDER))
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Сервер запущен на порту {port}")
    app.run(host='0.0.0.0', port=port)
