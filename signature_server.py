import os
import base64
import uuid
from io import BytesIO
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app)

SIGNATURES_FOLDER = "signatures"
os.makedirs(SIGNATURES_FOLDER, exist_ok=True)

print(f"Signatures folder: {SIGNATURES_FOLDER}")

@app.route('/', methods=['GET'])
def root():
    return jsonify({'status': 'ok', 'message': 'Signature server running'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

@app.route('/save_signature', methods=['POST', 'OPTIONS'])
def save_signature():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        print("=" * 50)
        print("SAVE SIGNATURE CALLED")
        
        data = request.json
        if not data:
            print("ERROR: No JSON data")
            return jsonify({'error': 'No JSON data'}), 400
        
        image_data = data.get('signature')
        user_id = data.get('user_id', 'unknown')
        
        print(f"User ID: {user_id}")
        print(f"Image data present: {bool(image_data)}")
        
        if not image_data:
            print("ERROR: No image data")
            return jsonify({'error': 'No image data'}), 400
        
        # Extract base64
        if ',' in image_data:
            base64_data = image_data.split(',')[1]
        else:
            base64_data = image_data
        
        print(f"Base64 length: {len(base64_data)}")
        
        # Decode
        try:
            image_bytes = base64.b64decode(base64_data)
            print(f"Decoded bytes: {len(image_bytes)}")
        except Exception as decode_error:
            print(f"Base64 decode error: {decode_error}")
            return jsonify({'error': f'Base64 decode error: {str(decode_error)}'}), 400
        
        # Open with PIL
        try:
            img = Image.open(BytesIO(image_bytes))
            print(f"Image opened - mode: {img.mode}, size: {img.size}")
        except Exception as pil_error:
            print(f"PIL error: {pil_error}")
            return jsonify({'error': f'PIL error: {str(pil_error)}'}), 500
        
        # Convert to RGB
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
        
        # Generate filename
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"signature_{user_id}_{timestamp}_{unique_id}.png"
        filepath = os.path.join(SIGNATURES_FOLDER, filename)
        
        # Save
        img.save(filepath, 'PNG')
        print(f"Saved: {filepath}")
        
        # Get base URL
        base_url = os.environ.get('BASE_URL', 'https://signature-server-87mz.onrender.com')
        image_url = f"{base_url}/get_signature/{filename}"
        
        print(f"Returning URL: {image_url}")
        print("=" * 50)
        
        return jsonify({
            'status': 'ok',
            'url': image_url,
            'filename': filename,
            'user_id': user_id
        })
        
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/get_signature/<filename>', methods=['GET'])
def get_signature(filename):
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    filepath = os.path.join(SIGNATURES_FOLDER, filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/png')
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/list_signatures', methods=['GET'])
def list_signatures():
    try:
        files = os.listdir(SIGNATURES_FOLDER)
        files.sort(reverse=True)
        return jsonify({
            'count': len(files),
            'signatures': files[:50]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
