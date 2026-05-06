"""
Mock Chatbot API Server
=======================
A Flask-based mock chatbot API that simulates real chatbot behavior.
Used as the target for all API tests in this framework.

Run: python app.py
"""

import time
import json
import uuid
import random
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ─── Simulated knowledge base ───────────────────────────────────────────────
RESPONSES = {
    "hello":        "Hello! How can I assist you today?",
    "hi":           "Hi there! What can I help you with?",
    "help":         "I can help you with questions, information, and general assistance.",
    "weather":      "I don't have real-time data, but I can help you find weather resources.",
    "time":         f"The current server time is {datetime.now().strftime('%H:%M')}.",
    "joke":         "Why don't scientists trust atoms? Because they make up everything!",
    "bye":          "Goodbye! Have a great day!",
    "default":      "I understand your query. Let me help you with that.",
}

TOXIC_KEYWORDS = ["hate", "kill", "harm", "abuse", "violence", "illegal"]

# ─── Routes ─────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }), 200


@app.route("/api/v1/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Expects: { "message": "user input", "session_id": "optional" }
    Returns: { "response": "...", "session_id": "...", "latency_ms": ... }
    """
    start = time.time()

    # ── Validate Content-Type ──────────────────────────────────────────────
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    # ── Validate required fields ───────────────────────────────────────────
    if "message" not in data:
        return jsonify({"error": "Field 'message' is required"}), 422

    message = data.get("message", "")
    session_id = data.get("session_id", str(uuid.uuid4()))

    # ── Guard: empty message ───────────────────────────────────────────────
    if not isinstance(message, str) or message.strip() == "":
        return jsonify({"error": "Message cannot be empty"}), 422

    # ── Guard: payload too large (>1000 chars treated as large payload) ────
    if len(message) > 1000:
        return jsonify({"error": "Message exceeds maximum length of 1000 characters"}), 413

    # ── Guard: toxic content ───────────────────────────────────────────────
    lower_msg = message.lower()
    for keyword in TOXIC_KEYWORDS:
        if keyword in lower_msg:
            return jsonify({
                "error": "Message contains inappropriate content",
                "code": "CONTENT_POLICY_VIOLATION"
            }), 400

    # ── Generate response ──────────────────────────────────────────────────
    response_text = RESPONSES["default"]
    for keyword, reply in RESPONSES.items():
        if keyword in lower_msg:
            response_text = reply
            break

    # Simulate variable processing time (50–200 ms)
    time.sleep(random.uniform(0.05, 0.2))

    latency_ms = round((time.time() - start) * 1000, 2)

    return jsonify({
        "response":   response_text,
        "session_id": session_id,
        "latency_ms": latency_ms,
        "timestamp":  datetime.utcnow().isoformat(),
        "tokens_used": len(message.split()) + len(response_text.split()),
    }), 200


@app.route("/api/v1/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """Return session metadata."""
    return jsonify({
        "session_id":  session_id,
        "created_at":  datetime.utcnow().isoformat(),
        "message_count": random.randint(1, 20),
        "active": True
    }), 200


@app.route("/api/v1/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Delete a session."""
    return jsonify({"message": f"Session {session_id} deleted successfully"}), 200


@app.route("/api/v1/feedback", methods=["POST"])
def feedback():
    """Submit feedback for a chatbot response."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    required = ["session_id", "rating"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Field '{field}' is required"}), 422
    rating = data.get("rating")
    if not isinstance(rating, int) or rating not in range(1, 6):
        return jsonify({"error": "Rating must be an integer between 1 and 5"}), 422
    return jsonify({"message": "Feedback submitted successfully", "feedback_id": str(uuid.uuid4())}), 201


@app.route("/api/v1/history/<session_id>", methods=["GET"])
def history(session_id):
    """Return mock chat history for a session."""
    return jsonify({
        "session_id": session_id,
        "messages": [
            {"role": "user",      "content": "Hello",          "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": "Hello! How can I assist you today?", "timestamp": datetime.utcnow().isoformat()},
        ]
    }), 200


# ─── Error handlers ──────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    print("🚀 Mock Chatbot API running at http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
