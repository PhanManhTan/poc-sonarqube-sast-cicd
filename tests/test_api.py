import pytest

from app.services import build_quote, normalize_symbol


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"service": "quote-api", "status": "ok"}


def test_known_quote_endpoint(client):
    response = client.get("/api/v1/quotes/aapl")

    assert response.status_code == 200
    assert response.get_json() == {
        "currency": "USD",
        "price": "228.50",
        "symbol": "AAPL",
    }


def test_unknown_quote_is_deterministic(client):
    response = client.get("/api/v1/quotes/demo")

    assert response.status_code == 200
    assert response.get_json() == {
        "currency": "USD",
        "price": "29.30",
        "symbol": "DEMO",
    }


@pytest.mark.parametrize("symbol", ["bad symbol", "TOO-LONG-SYMBOL", "@AAPL"])
def test_invalid_symbol_returns_bad_request(client, symbol):
    response = client.get(f"/api/v1/quotes/{symbol}")

    assert response.status_code == 400
    assert "symbol must contain" in response.get_json()["error"]


def test_symbol_normalization():
    assert normalize_symbol("  msft ") == "MSFT"

    with pytest.raises(ValueError, match="symbol must contain"):
        normalize_symbol("")


def test_quote_service_known_and_fallback_prices():
    assert build_quote("SONAR")["price"] == "100.00"
    assert build_quote("XY")["price"] == "17.70"
