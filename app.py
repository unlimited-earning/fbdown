import os
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from downloader import extract_facebook_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("App")

app = Flask(__name__)
CORS(app)

INDEX_PATH = os.path.join(os.path.dirname(__file__), 'index.html')

# Ensure JSON error handling so server NEVER sends HTML error pages to API
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"success": False, "error": "Bad request format."}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "API route not found."}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"success": False, "error": "HTTP method not allowed."}), 405

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal server error occurred."}), 500

@app.route('/', methods=['GET'])
def index():
    if os.path.exists(INDEX_PATH):
        return send_file(INDEX_PATH)
    return jsonify({"success": False, "error": "index.html not found."}), 404

@app.route('/api/download', methods=['POST'])
def handle_download():
    try:
        data = request.get_json(force=True, silent=True)
        if not data or 'url' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'url' field in JSON body."
            }), 400

        video_url = str(data.get('url', '')).strip()
        if not video_url:
            return jsonify({
                "success": False,
                "error": "Please enter a valid Facebook URL."
            }), 400

        result = extract_facebook_info(video_url)

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"API Route Crash: {str(e)}")
        return jsonify({
            "success": False,
            "error": "An internal server error occurred. Please try again."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
