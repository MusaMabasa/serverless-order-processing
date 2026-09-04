import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3


sqs = boto3.client("sqs")

QUEUE_URL = os.environ["ORDER_QUEUE_URL"]


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }


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

    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(order)
    )

    print(
        f"Order {order_id} successfully queued"
    )

    return response(
        202,
        {
            "message": "Order accepted for processing",
            "order_id": order_id,
            "status": "QUEUED"
        }
    )