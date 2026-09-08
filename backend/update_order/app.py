import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["ORDERS_TABLE"])

ALLOWED_STATUSES = {
    "QUEUED",
    "PROCESSING",
    "COMPLETED",
    "CANCELLED",
}


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)

        return super().default(obj)


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, cls=DecimalEncoder)
    }


def lambda_handler(event, context):

    print("Update Order request received")

    path_parameters = event.get("pathParameters") or {}
    order_id = path_parameters.get("order_id")

    if not order_id:
        return response(
            400,
            {"message": "order_id is required"}
        )

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(
            400,
            {"message": "Invalid JSON body"}
        )

    status = body.get("status")

    if not status:
        return response(
            400,
            {"message": "status is required"}
        )

    status = status.upper()

    if status not in ALLOWED_STATUSES:
        return response(
            400,
            {
                "message": "Invalid order status",
                "allowed_statuses": sorted(ALLOWED_STATUSES)
            }
        )

    updated_at = datetime.now(timezone.utc).isoformat()

    try:
        result = table.update_item(
            Key={
                "order_id": order_id
            },
            UpdateExpression=(
                "SET #status = :status, "
                "updated_at = :updated_at"
            ),
            ExpressionAttributeNames={
                "#status": "status"
            },
            ExpressionAttributeValues={
                ":status": status,
                ":updated_at": updated_at
            },
            ConditionExpression="attribute_exists(order_id)",
            ReturnValues="ALL_NEW"
        )

        order = result["Attributes"]

        print(
            f"Order {order_id} updated to {status}"
        )

        return response(
            200,
            {
                "message": "Order updated successfully",
                "order": order
            }
        )

    except ClientError as error:

        error_code = (
            error.response
            .get("Error", {})
            .get("Code")
        )

        if error_code == "ConditionalCheckFailedException":
            return response(
                404,
                {
                    "message": "Order not found",
                    "order_id": order_id
                }
            )

        print(
            f"Error updating order {order_id}: {error}"
        )

        return response(
            500,
            {"message": "Unable to update order"}
        )

    except Exception as error:

        print(
            f"Unexpected error updating order "
            f"{order_id}: {error}"
        )

        return response(
            500,
            {"message": "Unable to update order"}
        )