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

def _valid_idempotent_event(key="test-idempotency-key"):
    return {
        "headers": {
            "Idempotency-Key": key
        },
        "body": json.dumps(
            {
                "customer_name": "Mabasa Technologies",
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


def test_idempotency_first_request_returns_202():
    event = _valid_idempotent_event()

    table = MagicMock()

    with patch.object(
        create_order_app,
        "ORDERS_TABLE",
        "ServerlessOrders"
    ), patch.object(
        create_order_app.boto3,
        "resource"
    ) as mock_resource, patch.object(
        create_order_app.sqs,
        "send_message"
    ) as mock_send:

        mock_resource.return_value.Table.return_value = table

        result = create_order_app.lambda_handler(
            event,
            None
        )

    body = json.loads(result["body"])

    assert result["statusCode"] == 202
    assert body["status"] == "QUEUED"
    assert body["idempotent_replay"] is False
    assert body["order_id"].startswith("ORD-")

    table.put_item.assert_called_once()
    mock_send.assert_called_once()


def test_same_idempotency_key_only_sends_one_sqs_message():
    event = _valid_idempotent_event(
        "duplicate-order-key"
    )

    table = MagicMock()

    duplicate_error = create_order_app.ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "Duplicate request"
            }
        },
        "PutItem"
    )

    table.put_item.side_effect = [
        None,
        duplicate_error
    ]

    table.get_item.return_value = {
        "Item": {
            "order_id": "placeholder",
            "status": "COMPLETED"
        }
    }

    with patch.object(
        create_order_app,
        "ORDERS_TABLE",
        "ServerlessOrders"
    ), patch.object(
        create_order_app.boto3,
        "resource"
    ) as mock_resource, patch.object(
        create_order_app.sqs,
        "send_message"
    ) as mock_send:

        mock_resource.return_value.Table.return_value = table

        first = create_order_app.lambda_handler(
            event,
            None
        )

        second = create_order_app.lambda_handler(
            event,
            None
        )

    first_body = json.loads(first["body"])
    second_body = json.loads(second["body"])

    assert first["statusCode"] == 202
    assert second["statusCode"] == 200

    assert (
        first_body["order_id"]
        == second_body["order_id"]
    )

    assert first_body["idempotent_replay"] is False
    assert second_body["idempotent_replay"] is True
    assert second_body["status"] == "COMPLETED"

    assert table.put_item.call_count == 2

    mock_send.assert_called_once()


def test_idempotency_header_is_case_insensitive():
    event = _valid_idempotent_event()

    event["headers"] = {
        "idempotency-key": "lowercase-header-key"
    }

    table = MagicMock()

    with patch.object(
        create_order_app,
        "ORDERS_TABLE",
        "ServerlessOrders"
    ), patch.object(
        create_order_app.boto3,
        "resource"
    ) as mock_resource, patch.object(
        create_order_app.sqs,
        "send_message"
    ) as mock_send:

        mock_resource.return_value.Table.return_value = table

        result = create_order_app.lambda_handler(
            event,
            None
        )

    body = json.loads(result["body"])

    assert result["statusCode"] == 202
    assert body["idempotent_replay"] is False

    table.put_item.assert_called_once()
    mock_send.assert_called_once()


def test_idempotency_key_over_200_characters_returns_400():
    event = _valid_idempotent_event(
        "x" * 201
    )

    with patch.object(
        create_order_app.sqs,
        "send_message"
    ) as mock_send:

        result = create_order_app.lambda_handler(
            event,
            None
        )

    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert body["message"] == "Idempotency-Key is too long"

    mock_send.assert_not_called()


def test_sqs_failure_removes_idempotency_reservation():
    event = _valid_idempotent_event(
        "sqs-failure-key"
    )

    table = MagicMock()

    with patch.object(
        create_order_app,
        "ORDERS_TABLE",
        "ServerlessOrders"
    ), patch.object(
        create_order_app.boto3,
        "resource"
    ) as mock_resource, patch.object(
        create_order_app.sqs,
        "send_message",
        side_effect=RuntimeError("SQS unavailable")
    ):

        mock_resource.return_value.Table.return_value = table

        with pytest.raises(
            RuntimeError,
            match="SQS unavailable"
        ):
            create_order_app.lambda_handler(
                event,
                None
            )

    table.put_item.assert_called_once()

    reserved_item = (
        table
        .put_item
        .call_args
        .kwargs["Item"]
    )

    reserved_order_id = reserved_item["order_id"]

    table.delete_item.assert_called_once_with(
        Key={
            "order_id": reserved_order_id
        }
    )
