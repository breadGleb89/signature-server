import os
import base64
import json
import uuid
from io import BytesIO
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app)  # Разрешаем запросы с любых доменов (нужно для MiniApp)

# Папка для сохранения подписей
SIGNATURES_FOLDER = "signatures"
os.makedirs(SIGNATURES_FOLDER, exist_ok=True)

@app.route('/', methods=['GET'])
def root():
    """Корневой маршрут - проверка что сервер работает"""
    return jsonify({
        'status': 'ok',
        'message': 'Signature server is running',
        'version': '1.0',
        'endpoints': ['/health', '/save_signature', '/get_signature/<filename>', '/list_signatures']
    })

@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья сервера"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/save_signature', methods=['POST', 'OPTIONS'])
def save_signature():
    """Сохраняет подпись из MiniApp и возвращает URL"""
    
    # Обработка preflight CORS запроса
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Получаем данные
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data'}), 400
        
        image_data = data.get('signature')
        user_id = data.get('user_id', 'unknown')
        
        if not image_data:
            return jsonify({'error': 'No image data'}), 400
        
        print(f"Received signature from user {user_id}")
        
        # Извлекаем base64 данные (убираем префикс "data:image/jpeg;base64,")
        if ',' in image_data:
            base64_data = image_data.split(',')[1]
        else:
            base64_data = image_data
        
        # Декодируем base64 в байты
        image_bytes = base64.b64decode(base64_data)
        
        # Открываем изображение через PIL
        img = Image.open(BytesIO(image_bytes))
        
        # Конвертируем в RGB (на случай прозрачности или других режимов)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Создаём белый фон
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            # Вставляем изображение на белый фон
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Генерируем уникальное имя файла
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signature_{user_id}_{timestamp}_{unique_id}.png"
        filepath = os.path.join(SIGNATURES_FOLDER, filename)
        
        # Сохраняем изображение
        img.save(filepath, 'PNG')
        print(f"Signature saved: {filepath}")
        
        # Формируем URL для доступа к подписи
        # ВАЖНО: замените signature-server-87mz.onrender.com на ваш реальный адрес Render
        base_url = os.environ.get('BASE_URL', 'https://signature-server-87mz.onrender.com')
        image_url = f"{base_url}/get_signature/{filename}"
        
        return jsonify({
            'status': 'ok',
            'url': image_url,
            'filename': filename,
            'user_id': user_id,
            'timestamp': timestamp
        })
        
    except Exception as e:
        print(f"Error saving signature: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_signature/<filename>', methods=['GET'])
def get_signature(filename):
    """Возвращает файл подписи по имени"""
    # Проверяем безопасность - не допускаем переходов в другие папки
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    filepath = os.path.join(SIGNATURES_FOLDER, filename)
    
    if os.path.exists(filepath):
        return send_file(
            filepath,
            mimetype='image/png',
            as_attachment=False,
            download_name=filename
        )
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/list_signatures', methods=['GET'])
def list_signatures():
    """Возвращает список всех сохранённых подписей (для отладки)"""
    try:
        files = os.listdir(SIGNATURES_FOLDER)
        # Сортируем по времени создания (новые первые)
        files.sort(reverse=True)
        return jsonify({
            'count': len(files),
            'signatures': files[:50]  # только последние 50
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_signature/<filename>', methods=['DELETE'])
def delete_signature(filename):
    """Удаляет подпись (опционально)"""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    filepath = os.path.join(SIGNATURES_FOLDER, filename)
    
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'status': 'ok', 'deleted': filename})
    else:
        return jsonify({'error': 'File not found'}), 404

# Для локального запуска
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("=" * 50)
    print("SIGNATURE SERVER STARTED")
    print(f"Port: {port}")
    print(f"Signatures folder: {SIGNATURES_FOLDER}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)
