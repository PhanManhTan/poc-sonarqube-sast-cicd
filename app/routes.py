from flask import Blueprint, jsonify

from app.services import build_quote


api = Blueprint("api", __name__)


@api.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"service": "quote-api", "status": "ok"}, 200


@api.get("/api/v1/quotes/<symbol>")
def quote(symbol: str):
    try:
        payload = build_quote(symbol)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(payload), 200
