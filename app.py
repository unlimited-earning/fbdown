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

# Global JSON error handlers so Flask never returns HTML error pages to API callers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Endpoint not found."}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"success": False, "error": "Method not allowed."}), 405

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal server error occurred."}), 500

@app.route('/', methods=['GET'])
def index():
    """Renders single-file frontend."""
    if os.path.exists(INDEX_PATH):
        return send_file(INDEX_PATH)
    return jsonify({"success": False, "error": "index.html file not found."}), 404

@app.route('/api/download', methods=['POST'])
def handle_download():
    """POST Endpoint: Accepts JSON payload with 'url' and returns extracted video info."""
    try:
        data = request.get_json(force=True, silent=True)
        if not data or 'url' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'url' field in JSON request payload."
            }), 400

        video_url = str(data.get('url', '')).strip()
        if not video_url:
            return jsonify({
                "success": False,
                "error": "URL field cannot be empty."
            }), 400

        result = extract_facebook_info(video_url)

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"API Route Crash: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Server error processing request. Please check link and try again."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
