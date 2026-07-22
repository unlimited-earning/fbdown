import os
import logging
from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS
from downloader import extract_facebook_info

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("App")

app = Flask(__name__)
CORS(app)

# Load index.html directly for single-folder deployments
INDEX_PATH = os.path.join(os.path.dirname(__file__), 'index.html')

@app.route('/', methods=['GET'])
def index():
    """Renders the single-file frontend."""
    if os.path.exists(INDEX_PATH):
        return send_file(INDEX_PATH)
    return "Error: index.html not found.", 404

@app.route('/api/download', methods=['POST'])
def handle_download():
    """
    POST API Endpoint: Accepts Facebook URL and returns video metadata & download links.
    """
    try:
        data = request.get_json(force=True, silent=True)
        if not data or 'url' not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'url' parameter in request payload."
            }), 400

        video_url = data.get('url', '').strip()
        if not video_url:
            return jsonify({
                "success": False,
                "error": "URL parameter cannot be empty."
            }), 400

        # Execute extraction logic
        result = extract_facebook_info(video_url)

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error occurred processing request."
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
