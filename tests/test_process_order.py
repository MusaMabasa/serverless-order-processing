import importlib.util
import json
import os
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


PROCESS_ORDER_PATH = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "process_order"
    / "app.py"
)


def load_process_order_app():
    spec = importlib.util.spec_from_file_location(
        "process_order_app",
        PROCESS_ORDER_PATH
    )

    module = importlib.util.module_from_spec(spec)

    with patch.dict(
        os.environ,
        {"ORDERS_TABLE": "TestOrders"}
    ):
        spec.loader.exec_module(module)

    return module


process_order_app = load_process_order_app()


def test_valid_order_is_written_to_dynamodb():
    event = {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "order_id": "ORD-TEST1234",
                        "customer_name": "Mabasa Technologies",
                        "customer_email": "test@example.com",
                        "items": [
                            {
                                "product": "Laptop",
                                "quantity": 2,
                                "price": 15000
                            }
                        ],
                        "total": 30000,
                        "status": "QUEUED"
                    }
                )
            }
        ]
    }

    with patch.object(
        process_order_app.table,
        "put_item"
    ) as mock_put_item:

        result = process_order_app.lambda_handler(
            event,
            None
        )

    assert result["statusCode"] == 200

    body = json.loads(result["body"])

    assert (
        body["message"]
        == "Orders processed successfully"
    )

    mock_put_item.assert_called_once()

    saved_item = (
        mock_put_item.call_args.kwargs["Item"]
    )

    assert saved_item["order_id"] == "ORD-TEST1234"
    assert saved_item["status"] == "COMPLETED"
    assert "processed_at" in saved_item
    assert saved_item["total"] == Decimal("30000")


def test_missing_order_id_raises_value_error():
    event = {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "customer_name": "Mabasa Technologies",
                        "customer_email": "test@example.com",
                        "total": 100
                    }
                )
            }
        ]
    }

    try:
        process_order_app.lambda_handler(
            event,
            None
        )

        assert False, "Expected ValueError"

    except ValueError as error:
        assert str(error) == "order_id is required"


def test_invalid_json_raises_json_decode_error():
    event = {
        "Records": [
            {
                "body": "{invalid-json}"
            }
        ]
    }

    try:
        process_order_app.lambda_handler(
            event,
            None
        )

        assert False, "Expected JSONDecodeError"

    except json.JSONDecodeError:
        pass


def test_multiple_orders_are_processed():
    event = {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "order_id": "ORD-TEST0001",
                        "customer_name": "Customer One",
                        "customer_email": "one@example.com",
                        "items": [],
                        "total": 100
                    }
                )
            },
            {
                "body": json.dumps(
                    {
                        "order_id": "ORD-TEST0002",
                        "customer_name": "Customer Two",
                        "customer_email": "two@example.com",
                        "items": [],
                        "total": 200
                    }
                )
            }
        ]
    }

    with patch.object(
        process_order_app.table,
        "put_item"
    ) as mock_put_item:

        result = process_order_app.lambda_handler(
            event,
            None
        )

    assert result["statusCode"] == 200
    assert mock_put_item.call_count == 2