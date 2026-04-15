import os
import base64
from io import BytesIO
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from PIL import Image
from datetime import datetime

app = Flask(__name__)
CORS(app)

EXCEL_FILE = "template.xlsx"
SIGNATURES_FOLDER = "signatures"
os.makedirs(SIGNATURES_FOLDER, exist_ok=True)

@app.route('/', methods=['GET'])
def root():
    return jsonify({'status': 'ok', 'message': 'Signature server is running'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

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
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)

        # Сохраняем копию подписи как отдельный файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        signature_file = os.path.join(SIGNATURES_FOLDER, f"signature_{user_id}_{timestamp}.png")
        with open(signature_file, "wb") as f:
            f.write(image_bytes)
        print(f"Signature saved: {signature_file}")

        # Конвертируем в PNG для Excel
        img = Image.open(BytesIO(image_bytes))
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        png_io = BytesIO()
        img.save(png_io, format='PNG')
        png_io.seek(0)

        # Вставляем в Excel
        if not os.path.exists(EXCEL_FILE):
            # Создаём новый Excel файл, если его нет
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
        else:
            wb = load_workbook(EXCEL_FILE)
            ws = wb.active

        xl_img = XLImage(png_io)
        xl_img.width = 200
        xl_img.height = 100
        ws.add_image(xl_img, "F49")
        wb.save(EXCEL_FILE)

        return jsonify({'status': 'ok', 'message': 'Signature added to Excel'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_excel', methods=['GET'])
def get_excel():
    """Отправляет файл template.xlsx клиенту"""
    if os.path.exists(EXCEL_FILE):
        return send_file(
            EXCEL_FILE,
            as_attachment=True,
            download_name=f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )
    return jsonify({'error': 'File not found'}), 404

@app.route('/get_signatures', methods=['GET'])
def get_signatures():
    """Возвращает список всех сохранённых подписей"""
    signatures = []
    for f in os.listdir(SIGNATURES_FOLDER):
        if f.endswith('.png'):
            signatures.append(f)
    return jsonify({'signatures': signatures})

if __name__ == '__main__':
    print("🚀 Signature server starting...")
    print(f"📁 Excel file: {EXCEL_FILE}")
    print(f"📁 Signatures folder: {SIGNATURES_FOLDER}")
    app.run(host='0.0.0.0', port=10000, debug=True)
