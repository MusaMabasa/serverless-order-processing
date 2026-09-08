import importlib.util
import json
import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock


os.environ["AWS_DEFAULT_REGION"] = "af-south-1"
os.environ["AWS_REGION"] = "af-south-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["ORDERS_TABLE"] = "TestOrders"


spec = importlib.util.spec_from_file_location(
    "get_orders_app",
    "backend/get_orders/app.py"
)

get_orders_app = importlib.util.module_from_spec(spec)

sys.modules["get_orders_app"] = get_orders_app

spec.loader.exec_module(get_orders_app)


def test_get_orders_returns_200():

    mock_table = MagicMock()

    mock_table.scan.return_value = {
        "Items": [
            {
                "order_id": "ORD-0001",
                "customer_name": "Mabasa Technologies",
                "total": Decimal("250"),
                "created_at": "2026-09-04T10:00:00+00:00"
            }
        ]
    }

    get_orders_app.table = mock_table

    response = get_orders_app.lambda_handler(
        {},
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["count"] == 1
    assert body["orders"][0]["order_id"] == "ORD-0001"
    assert body["orders"][0]["total"] == 250

    mock_table.scan.assert_called_once()


def test_get_orders_returns_empty_list():

    mock_table = MagicMock()

    mock_table.scan.return_value = {
        "Items": []
    }

    get_orders_app.table = mock_table

    response = get_orders_app.lambda_handler(
        {},
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["count"] == 0
    assert body["orders"] == []


def test_get_orders_sorts_newest_first():

    mock_table = MagicMock()

    mock_table.scan.return_value = {
        "Items": [
            {
                "order_id": "ORD-OLD",
                "created_at": "2026-09-01T10:00:00+00:00"
            },
            {
                "order_id": "ORD-NEW",
                "created_at": "2026-09-04T10:00:00+00:00"
            }
        ]
    }

    get_orders_app.table = mock_table

    response = get_orders_app.lambda_handler(
        {},
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["orders"][0]["order_id"] == "ORD-NEW"
    assert body["orders"][1]["order_id"] == "ORD-OLD"


def test_get_orders_handles_pagination():

    mock_table = MagicMock()

    mock_table.scan.side_effect = [
        {
            "Items": [
                {
                    "order_id": "ORD-0001",
                    "created_at": "2026-09-01T10:00:00+00:00"
                }
            ],
            "LastEvaluatedKey": {
                "order_id": "ORD-0001"
            }
        },
        {
            "Items": [
                {
                    "order_id": "ORD-0002",
                    "created_at": "2026-09-02T10:00:00+00:00"
                }
            ]
        }
    ]

    get_orders_app.table = mock_table

    response = get_orders_app.lambda_handler(
        {},
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["count"] == 2

    assert mock_table.scan.call_count == 2


def test_get_orders_returns_500_on_dynamodb_error():

    mock_table = MagicMock()

    mock_table.scan.side_effect = Exception(
        "DynamoDB unavailable"
    )

    get_orders_app.table = mock_table

    response = get_orders_app.lambda_handler(
        {},
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 500

    assert body["message"] == (
        "Unable to retrieve orders"
    )