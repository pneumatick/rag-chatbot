from flask import Flask, request, jsonify
from flask_cors import CORS

from chunking import VectorInterface

server = Flask(__name__)
# Allow the Svelte dev server (default Vite port) to call this API.
# Tighten this to your actual frontend origin in production.
CORS(server, resources={r"/api/*": {"origins": "*"}})

vec = VectorInterface()

@server.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@server.route("/api/query", methods=["POST"])
def query():
    body = request.get_json(silent=True) or {}
    user_query = (body.get("query") or "").strip()

    if not user_query:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    result = vec.query(user_query)

    return jsonify({
        "answer": result["answer"],
        "sources": result["sources"],
    })


@server.route("/api/add_docs", methods=["POST"])
def add_docs():
    body = request.get_json(silent=True) or {}
    dirname = body.get("dirname", "user-docs")

    try:
        count = vec.add_docs(dirname)
        return jsonify({"status": "ok", "chunks_added": count})
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the frontend
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=5000, debug=True)
