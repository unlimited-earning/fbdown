import os
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from downloader import get_video_info

# Configure Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("App")

app = Flask(__name__)
CORS(app)

INDEX_PATH = os.path.join(os.path.dirname(__file__), 'index.html')

# Ensure API returns JSON for all error statuses
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"success": False, "message": "Bad request payload."}), 400

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "message": "API endpoint not found."}), 404
    return "File not found", 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"success": False, "message": "HTTP method not allowed."}), 405

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "message": "Internal server error occurred."}), 500

@app.route('/', methods=['GET'])
def index():
    """Serves the single-file frontend."""
    if os.path.exists(INDEX_PATH):
        return send_file(INDEX_PATH)
    return jsonify({"success": False, "message": "index.html is missing."}), 404

@app.route('/api/download', methods=['POST'])
def handle_download():
    """
    POST API Endpoint: Accepts JSON payload with video URL.
    Returns JSON response containing title, thumbnail, duration, and download links.
    """
    try:
        data = request.get_json(force=True, silent=True)
        
        if not data or not isinstance(data, dict):
            return jsonify({
                "success": False,
                "message": "Invalid JSON input."
            }), 400

        video_url = data.get('url', '').strip()
        if not video_url:
            return jsonify({
                "success": False,
                "message": "URL parameter cannot be empty."
            }), 400

        result = get_video_info(video_url)

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"API Handler Exception: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Server error processing request."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
