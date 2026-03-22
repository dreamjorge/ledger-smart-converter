import pytest
from unittest.mock import patch, MagicMock


def test_client_instantiation():
    from services.firefly_api_client import FireflyApiClient
    client = FireflyApiClient(base_url="http://firefly.local", token="mytoken")
    assert client.base_url == "http://firefly.local"
    assert client._token == "mytoken"


def test_post_transaction_sends_correct_headers():
    from services.firefly_api_client import FireflyApiClient

    client = FireflyApiClient(base_url="http://firefly.local", token="secret")
    txn = {
        "type": "withdrawal", "date": "2024-01-15", "amount": "100.50",
        "currency_code": "MXN", "description": "OXXO",
        "source_name": "ACC1", "destination_name": "Expenses:Food:Groceries",
        "category_name": "Groceries", "tags": "merchant:oxxo",
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"id": "42"}}

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = client.post_transaction(txn)

    call_kwargs = mock_post.call_args
    assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer secret"
    assert result["data"]["id"] == "42"


def test_post_transaction_uses_correct_url():
    from services.firefly_api_client import FireflyApiClient

    client = FireflyApiClient(base_url="http://firefly.local", token="t")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}

    with patch("requests.post", return_value=mock_response) as mock_post:
        client.post_transaction({})

    url = mock_post.call_args.args[0]
    assert url == "http://firefly.local/api/v1/transactions"


def test_post_transaction_raises_on_401():
    from services.firefly_api_client import FireflyApiClient, FireflyAuthError

    client = FireflyApiClient(base_url="http://firefly.local", token="bad")
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(FireflyAuthError):
            client.post_transaction({"type": "withdrawal"})


def test_post_transaction_raises_on_422():
    from services.firefly_api_client import FireflyApiClient, FireflyValidationError

    client = FireflyApiClient(base_url="http://firefly.local", token="tok")
    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {"message": "The given data was invalid."}

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(FireflyValidationError) as exc_info:
            client.post_transaction({"type": "withdrawal"})
    assert "invalid" in str(exc_info.value).lower()


def test_post_transaction_raises_http_error_on_500():
    from services.firefly_api_client import FireflyApiClient
    import requests

    client = FireflyApiClient(base_url="http://firefly.local", token="tok")
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

    with patch("requests.post", return_value=mock_response):
        with pytest.raises(requests.HTTPError):
            client.post_transaction({})
