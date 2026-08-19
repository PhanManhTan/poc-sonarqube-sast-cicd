from __future__ import annotations
from typing import Tuple
from flask import Blueprint, jsonify

from app.services import build_quote, get_market_status


api = Blueprint("api", __name__)


@api.get("/health")
def health() -> Tuple[dict, int]:
    return {"service": "quote-api", "status": "ok"}, 200


@api.get("/api/v1/market-status")
def market_status() -> Tuple[dict, int]:
    return jsonify(get_market_status()), 200


@api.get("/api/v1/quotes/<symbol>")
def quote(symbol: str):
    try:
        payload = build_quote(symbol)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(payload), 200
