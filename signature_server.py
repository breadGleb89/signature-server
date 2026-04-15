import os
import base64
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from PIL import Image

app = Flask(__name__)
CORS(app)

EXCEL_FILE = "template.xlsx"

@app.route('/save_signature', methods=['POST'])
def save_signature():
    try:
        data = request.json
        image_data = data.get('signature')
        if not image_data:
            return jsonify({'error': 'Нет изображения'}), 400

        if ',' in image_data:
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)

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

        if not os.path.exists(EXCEL_FILE):
            return jsonify({'error': f'Файл {EXCEL_FILE} не найден'}), 404

        wb = load_workbook(EXCEL_FILE)
        ws = wb.active
        xl_img = XLImage(png_io)
        xl_img.width = 200
        xl_img.height = 100
        ws.add_image(xl_img, "F49")
        wb.save(EXCEL_FILE)

        return jsonify({'status': 'ok', 'message': 'Подпись добавлена'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)