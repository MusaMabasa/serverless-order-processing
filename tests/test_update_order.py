import importlib
import json
import os
import sys
from unittest.mock import MagicMock

import boto3
import pytest
from botocore.exceptions import ClientError


os.environ["AWS_DEFAULT_REGION"] = "af-south-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["ORDERS_TABLE"] = "ServerlessOrders"


@pytest.fixture
def update_order_module(monkeypatch):
    mock_table = MagicMock()
    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.return_value = mock_table

    monkeypatch.setattr(
        boto3,
        "resource",
        MagicMock(return_value=mock_dynamodb)
    )

    module_name = "backend.update_order.app"

    if module_name in sys.modules:
        del sys.modules[module_name]

    module = importlib.import_module(module_name)

    return module, mock_table


def make_event(
    order_id="ORD-TEST1234",
    body=None
):
    if body is None:
        body = {
            "status": "CANCELLED"
        }

    return {
        "pathParameters": {
            "order_id": order_id
        },
        "body": json.dumps(body)
    }


def test_update_order_returns_200(update_order_module):
    app, mock_table = update_order_module

    mock_table.update_item.return_value = {
        "Attributes": {
            "order_id": "ORD-TEST1234",
            "customer_name": "Mabasa Technologies",
            "status": "CANCELLED",
            "total": 250
        }
    }

    result = app.lambda_handler(
        make_event(),
        None
    )

    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["message"] == "Order updated successfully"
    assert body["order"]["order_id"] == "ORD-TEST1234"
    assert body["order"]["status"] == "CANCELLED"

    mock_table.update_item.assert_called_once()


def test_update_order_converts_status_to_uppercase(
    update_order_module
):
    app, mock_table = update_order_module

    mock_table.update_item.return_value = {
        "Attributes": {
            "order_id": "ORD-TEST1234",
            "status": "PROCESSING"
        }
    }

    result = app.lambda_handler(
        make_event(
            body={
                "status": "processing"
            }
        ),
        None
    )

    assert result["statusCode"] == 200

    call_args = mock_table.update_item.call_args.kwargs

    assert (
        call_args["ExpressionAttributeValues"][":status"]
        == "PROCESSING"
    )


def test_update_order_returns_400_when_order_id_missing(
    update_order_module
):
    app, mock_table = update_order_module

    event = {
        "pathParameters": {},
        "body": json.dumps({
            "status": "CANCELLED"
        })
    }

    result = app.lambda_handler(event, None)

    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert body["message"] == "order_id is required"

    mock_table.update_item.assert_not_called()


def test_update_order_handles_missing_path_parameters(
    update_order_module
):
    app, mock_table = update_order_module

    event = {
        "body": json.dumps({
            "status": "CANCELLED"
        })
    }

    result = app.lambda_handler(event, None)

    assert result["statusCode"] == 400

    mock_table.update_item.assert_not_called()


def test_update_order_returns_400_for_invalid_json(
    update_order_module
):
    app, mock_table = update_order_module

    event = {
        "pathParameters": {
            "order_id": "ORD-TEST1234"
        },
        "body": "{invalid-json"
    }

    result = app.lambda_handler(event, None)

    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert body["message"] == "Invalid JSON body"

    mock_table.update_item.assert_not_called()


def test_update_order_returns_400_when_status_missing(
    update_order_module
):
    app, mock_table = update_order_module

    result = app.lambda_handler(
        make_event(body={}),
        None
    )

    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert body["message"] == "status is required"

    mock_table.update_item.assert_not_called()


def test_update_order_returns_400_for_invalid_status(
    update_order_module
):
    app, mock_table = update_order_module

    result = app.lambda_handler(
        make_event(
            body={
                "status": "DELETED"
            }
        ),
        None
    )

    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert body["message"] == "Invalid order status"

    assert body["allowed_statuses"] == [
        "CANCELLED",
        "COMPLETED",
        "PROCESSING",
        "QUEUED"
    ]

    mock_table.update_item.assert_not_called()


def test_update_order_returns_404_when_order_not_found(
    update_order_module
):
    app, mock_table = update_order_module

    error_response = {
        "Error": {
            "Code": "ConditionalCheckFailedException",
            "Message": "Condition failed"
        }
    }

    mock_table.update_item.side_effect = ClientError(
        error_response,
        "UpdateItem"
    )

    result = app.lambda_handler(
        make_event(
            order_id="ORD-NOTFOUND"
        ),
        None
    )

    body = json.loads(result["body"])

    assert result["statusCode"] == 404
    assert body["message"] == "Order not found"
    assert body["order_id"] == "ORD-NOTFOUND"


def test_update_order_returns_500_on_dynamodb_error(
    update_order_module
):
    app, mock_table = update_order_module

    error_response = {
        "Error": {
            "Code": "InternalServerError",
            "Message": "DynamoDB failure"
        }
    }

    mock_table.update_item.side_effect = ClientError(
        error_response,
        "UpdateItem"
    )

    result = app.lambda_handler(
        make_event(),
        None
    )

    body = json.loads(result["body"])

    assert result["statusCode"] == 500
    assert body["message"] == "Unable to update order"