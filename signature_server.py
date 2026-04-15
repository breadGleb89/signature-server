import os
import base64
from io import BytesIO
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)

SIGNATURES_FOLDER = "signatures"
os.makedirs(SIGNATURES_FOLDER, exist_ok=True)

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

        # Извлекаем base64
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)

        # Генерируем уникальное имя файла
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signature_{user_id}_{timestamp}_{unique_id}.png"
        filepath = os.path.join(SIGNATURES_FOLDER, filename)
        
        # Конвертируем в PNG и сохраняем
        img = Image.open(BytesIO(image_bytes))
        
        # Приводим к RGB (на случай прозрачности)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        img.save(filepath, 'PNG')
        
        # Формируем URL для скачивания
        file_url = f"https://signature-server-87mz.onrender.com/get_signature/{filename}"
        
        print(f"✅ Signature saved: {filepath}")
        
        return jsonify({
            'status': 'ok',
            'url': file_url,
            'filename': filename
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_signature/<filename>', methods=['GET'])
def get_signature(filename):
    """Отдаёт сохранённую подпись по имени файла"""
    filepath = os.path.join(SIGNATURES_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/png')
    return jsonify({'error': 'File not found'}), 404

@app.route('/list_signatures', methods=['GET'])
def list_signatures():
    """Список всех подписей (для отладки)"""
    files = os.listdir(SIGNATURES_FOLDER)
    return jsonify({'signatures': files})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("=" * 50)
    print("SIGNATURE SERVER STARTED")
    print(f"Signatures folder: {SIGNATURES_FOLDER}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=10000, debug=True)
