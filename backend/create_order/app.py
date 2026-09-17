import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError


sqs = boto3.client("sqs")

QUEUE_URL = os.environ["ORDER_QUEUE_URL"]
ORDERS_TABLE = os.environ.get("ORDERS_TABLE")


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,Idempotency-Key",
            "Access-Control-Allow-Methods": "GET,POST,PATCH,OPTIONS"
        },
        "body": json.dumps(body)
    }


def get_header(event, header_name):
    headers = event.get("headers") or {}

    for key, value in headers.items():
        if key.lower() == header_name.lower():
            return value

    return None


def dynamodb_safe(value):
    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, list):
        return [dynamodb_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            key: dynamodb_safe(item)
            for key, item in value.items()
        }

    return value


def lambda_handler(event, context):

    print("Create Order request received")

    try:
        body = json.loads(event.get("body") or "{}")

    except json.JSONDecodeError:
        return response(
            400,
            {"message": "Request body must contain valid JSON"}
        )

    customer_name = body.get("customer_name")
    customer_email = body.get("customer_email")
    items = body.get("items")

    if not customer_name:
        return response(
            400,
            {"message": "customer_name is required"}
        )

    if not customer_email:
        return response(
            400,
            {"message": "customer_email is required"}
        )

    if not isinstance(items, list) or len(items) == 0:
        return response(
            400,
            {"message": "At least one order item is required"}
        )

    total = Decimal("0")

    try:

        for item in items:

            product = item.get("product")
            quantity = int(item.get("quantity", 0))
            price = Decimal(str(item.get("price", 0)))

            if not product:
                raise ValueError("Product name is required")

            if quantity <= 0:
                raise ValueError(
                    "Quantity must be greater than zero"
                )

            if price < 0:
                raise ValueError(
                    "Price cannot be negative"
                )

            total += Decimal(quantity) * price

    except (ValueError, TypeError):
        return response(
            400,
            {"message": "Invalid order item"}
        )

    idempotency_key = get_header(
        event,
        "Idempotency-Key"
    )

    if idempotency_key:
        idempotency_key = str(idempotency_key).strip()

        if len(idempotency_key) > 200:
            return response(
                400,
                {"message": "Idempotency-Key is too long"}
            )

    if idempotency_key:
        order_hash = hashlib.sha256(
            idempotency_key.encode("utf-8")
        ).hexdigest()[:8].upper()

        order_id = f"ORD-{order_hash}"

    else:
        # Backward compatibility for clients that do not yet
        # send an Idempotency-Key.
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    order = {
        "order_id": order_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "items": items,
        "total": float(total),
        "status": "QUEUED",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    if idempotency_key:
        order["idempotency_key"] = idempotency_key

        if not ORDERS_TABLE:
            return response(
                500,
                {"message": "Idempotency configuration is missing"}
            )

        orders_table = boto3.resource(
            "dynamodb"
        ).Table(ORDERS_TABLE)

        try:
            orders_table.put_item(
                Item=dynamodb_safe(order),
                ConditionExpression=(
                    "attribute_not_exists(order_id)"
                )
            )

        except ClientError as error:
            error_code = (
                error.response
                .get("Error", {})
                .get("Code")
            )

            if error_code != "ConditionalCheckFailedException":
                raise

            existing = orders_table.get_item(
                Key={"order_id": order_id},
                ConsistentRead=True
            ).get("Item", {})

            print(
                f"Duplicate request detected for {order_id}"
            )

            return response(
                200,
                {
                    "message": "Order already accepted",
                    "order_id": order_id,
                    "status": existing.get(
                        "status",
                        "QUEUED"
                    ),
                    "idempotent_replay": True
                }
            )

    try:
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(order)
        )

    except Exception:

        if idempotency_key:
            try:
                orders_table.delete_item(
                    Key={"order_id": order_id}
                )

            except Exception as cleanup_error:
                print(
                    "Unable to remove idempotency "
                    f"reservation: {cleanup_error}"
                )

        raise

    print(
        f"Order {order_id} successfully queued"
    )

    return response(
        202,
        {
            "message": "Order accepted for processing",
            "order_id": order_id,
            "status": "QUEUED",
            "idempotent_replay": False
        }
    )