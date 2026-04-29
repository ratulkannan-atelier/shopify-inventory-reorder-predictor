from flask import Blueprint, Response, jsonify

main_bp = Blueprint("main", __name__)


@main_bp.get("/health")
def health() -> tuple[Response, int]:
    return jsonify({"status": "ok", "service": "reorder-predictor"}), 200
