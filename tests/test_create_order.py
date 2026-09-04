import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath("backend/create_order"))

with patch.dict(os.environ, {"ORDER_QUEUE_URL": "https://example.com/queue"}):
    import app as create_order_app


def test_valid_order_returns_202():
    event = {
        "body": json.dumps(
            {
                "customer_name": "Mabasa Technologies",
                "customer_email": "test@example.com",
                "items": [
                    {
                        "product": "Laptop",
                        "quantity": 2,
                        "price": 15000
                    }
                ]
            }
        )
    }

    with patch.object(create_order_app.sqs, "send_message") as mock_send:
        result = create_order_app.lambda_handler(event, None)

    body = json.loads(result["body"])

    assert result["statusCode"] == 202
    assert body["message"] == "Order accepted for processing"
    assert body["status"] == "QUEUED"
    assert body["order_id"].startswith("ORD-")

    mock_send.assert_called_once()


def test_missing_customer_name_returns_400():
    event = {
        "body": json.dumps(
            {
                "customer_email": "test@example.com",
                "items": [
                    {
                        "product": "Laptop",
                        "quantity": 1,
                        "price": 100
                    }
                ]
            }
        )
    }

    result = create_order_app.lambda_handler(event, None)

    assert result["statusCode"] == 400
    assert json.loads(result["body"])["message"] == "customer_name is required"


def test_empty_items_returns_400():
    event = {
        "body": json.dumps(
            {
                "customer_name": "Mabasa Technologies",
                "customer_email": "test@example.com",
                "items": []
            }
        )
    }

    result = create_order_app.lambda_handler(event, None)

    assert result["statusCode"] == 400
    assert (
        json.loads(result["body"])["message"]
        == "At least one order item is required"
    )


def test_invalid_json_returns_400():
    event = {
        "body": "{invalid-json}"
    }

    result = create_order_app.lambda_handler(event, None)

    assert result["statusCode"] == 400
    assert (
        json.loads(result["body"])["message"]
        == "Request body must contain valid JSON"
    )