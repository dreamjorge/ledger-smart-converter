import pytest
from unittest.mock import patch, MagicMock
from domain.transaction import CanonicalTransaction
from infrastructure.adapters.firefly_api_adapter import (
    FireflyApiAdapter,
    FireflyAuthError,
    FireflyValidationError,
)


def _make_txn(
    amount=100.50,
    txn_type="withdrawal",
    description="OXXO STORE",
    category="Groceries",
    tags="merchant:oxxo",
    bank_id="testbank",
):
    return CanonicalTransaction(
        date="2024-01-15",
        description=description,
        amount=amount,
        bank_id=bank_id,
        account_id="ACC1",
        canonical_account_id="cc:test",
        transaction_type=txn_type,
        category=category,
        tags=tags,
        source="test.csv",
    )


class TestFireflyApiAdapterInit:
    def test_strips_trailing_slash(self):
        adapter = FireflyApiAdapter("http://firefly.local/", "token")
        assert adapter.api_url == "http://firefly.local/api/v1"

    def test_appends_api_v1_if_missing(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        assert adapter.api_url == "http://firefly.local/api/v1"

    def test_keeps_existing_api_v1(self):
        adapter = FireflyApiAdapter("http://firefly.local/api/v1", "token")
        assert adapter.api_url == "http://firefly.local/api/v1"


class TestVerifyConnection:
    def test_returns_true_on_200(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.get", return_value=mock_response):
            assert adapter.verify_connection() is True

    def test_raises_auth_error_on_401(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("requests.get", return_value=mock_response):
            with pytest.raises(FireflyAuthError):
                adapter.verify_connection()

    def test_returns_false_on_other_errors(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        with patch("requests.get", side_effect=Exception("Network error")):
            assert adapter.verify_connection() is False


class TestPushTransactions:
    def test_pushes_single_transaction_successfully(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        txn = _make_txn()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"id": "42"}}

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = adapter.push_transactions([txn])

        assert result["synced_hashes"] == [txn.id]
        assert result["errors"] == []
        mock_post.assert_called_once()

    def test_raises_auth_error_on_401(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        txn = _make_txn()

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(FireflyAuthError):
                adapter.push_transactions([txn])

    def test_raises_validation_error_on_422(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        txn = _make_txn()

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"message": "The given data was invalid."}

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(FireflyValidationError) as exc_info:
                adapter.push_transactions([txn])
            assert "invalid" in str(exc_info.value).lower()

    def test_records_error_on_non_401_422_failure(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        txn = _make_txn()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")

        with patch("requests.post", return_value=mock_response):
            result = adapter.push_transactions([txn])

        assert result["synced_hashes"] == []
        assert len(result["errors"]) == 1
        assert txn.id in result["errors"][0]["hash"]

    def test_processes_multiple_transactions(self):
        import requests as req

        adapter = FireflyApiAdapter("http://firefly.local", "token")
        txn1 = _make_txn(amount=50.0, description="TEST1")
        txn2 = _make_txn(amount=75.0, description="TEST2")

        responses = [MagicMock(status_code=201), MagicMock(status_code=400)]
        responses[0].json.return_value = {"data": {"id": "1"}}
        responses[1].raise_for_status.side_effect = req.HTTPError("400 Bad Request")

        with patch("requests.post", side_effect=responses):
            result = adapter.push_transactions([txn1, txn2])

        assert len(result["synced_hashes"]) == 1
        assert len(result["errors"]) == 1


class TestMapToFireflyJson:
    def test_withdrawal_becomes_negative_amount(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        txn = _make_txn(amount=100.50, txn_type="withdrawal")
        payload = adapter._map_to_firefly_json(txn)

        ff_txn = payload["transactions"][0]
        assert ff_txn["amount"] == "-100.50"
        assert ff_txn["type"] == "withdrawal"

    def test_deposit_becomes_positive_amount(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        txn = _make_txn(amount=100.50, txn_type="deposit")
        payload = adapter._map_to_firefly_json(txn)

        ff_txn = payload["transactions"][0]
        assert ff_txn["amount"] == "100.50"
        assert ff_txn["type"] == "deposit"

    def test_maps_all_fields(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        txn = _make_txn(
            amount=100.50,
            description="OXXO STORE",
            category="Groceries",
            tags="merchant:oxxo,period:2024-01",
        )
        payload = adapter._map_to_firefly_json(txn)

        ff_txn = payload["transactions"][0]
        assert ff_txn["description"] == "OXXO STORE"
        assert ff_txn["category_name"] == "Groceries"
        assert ff_txn["tags"] == ["merchant:oxxo", "period:2024-01"]
        assert ff_txn["external_id"] == txn.id
        assert ff_txn["source_name"] == "ACC1"
        assert ff_txn["currency_code"] == "MXN"

    def test_tags_strip_whitespace(self):
        adapter = FireflyApiAdapter("http://firefly.local", "token")
        txn = _make_txn(tags=" tag1 , tag2 , tag3 ")
        payload = adapter._map_to_firefly_json(txn)

        assert payload["transactions"][0]["tags"] == ["tag1", "tag2", "tag3"]
