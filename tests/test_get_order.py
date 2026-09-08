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
    "get_order_app",
    "backend/get_order/app.py"
)

get_order_app = importlib.util.module_from_spec(spec)

sys.modules["get_order_app"] = get_order_app

spec.loader.exec_module(get_order_app)


def test_get_order_returns_200():

    mock_table = MagicMock()

    mock_table.get_item.return_value = {
        "Item": {
            "order_id": "ORD-TEST1234",
            "customer_name": "Mabasa Technologies",
            "customer_email": "test@example.com",
            "status": "COMPLETED",
            "total": Decimal("250")
        }
    }

    get_order_app.table = mock_table

    event = {
        "pathParameters": {
            "order_id": "ORD-TEST1234"
        }
    }

    response = get_order_app.lambda_handler(
        event,
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["order"]["order_id"] == "ORD-TEST1234"
    assert body["order"]["status"] == "COMPLETED"
    assert body["order"]["total"] == 250

    mock_table.get_item.assert_called_once_with(
        Key={
            "order_id": "ORD-TEST1234"
        }
    )


def test_get_order_returns_404():

    mock_table = MagicMock()

    mock_table.get_item.return_value = {}

    get_order_app.table = mock_table

    event = {
        "pathParameters": {
            "order_id": "ORD-NOTFOUND"
        }
    }

    response = get_order_app.lambda_handler(
        event,
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 404
    assert body["message"] == "Order not found"
    assert body["order_id"] == "ORD-NOTFOUND"


def test_get_order_returns_400_when_order_id_missing():

    event = {
        "pathParameters": {}
    }

    response = get_order_app.lambda_handler(
        event,
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert body["message"] == "order_id is required"


def test_get_order_handles_missing_path_parameters():

    event = {}

    response = get_order_app.lambda_handler(
        event,
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert body["message"] == "order_id is required"


def test_get_order_returns_500_on_dynamodb_error():

    mock_table = MagicMock()

    mock_table.get_item.side_effect = Exception(
        "DynamoDB unavailable"
    )

    get_order_app.table = mock_table

    event = {
        "pathParameters": {
            "order_id": "ORD-ERROR"
        }
    }

    response = get_order_app.lambda_handler(
        event,
        None
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 500
    assert body["message"] == "Unable to retrieve order"