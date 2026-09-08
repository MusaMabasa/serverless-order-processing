import json
import os
from decimal import Decimal

import boto3


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["ORDERS_TABLE"])


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
        "body": json.dumps(
            body,
            cls=DecimalEncoder
        )
    }


def lambda_handler(event, context):

    print("Get Order request received")

    path_parameters = event.get("pathParameters") or {}

    order_id = path_parameters.get("order_id")

    if not order_id:
        return response(
            400,
            {
                "message": "order_id is required"
            }
        )

    try:

        result = table.get_item(
            Key={
                "order_id": order_id
            }
        )

        order = result.get("Item")

        if not order:
            return response(
                404,
                {
                    "message": "Order not found",
                    "order_id": order_id
                }
            )

        print(
            f"Order {order_id} retrieved successfully"
        )

        return response(
            200,
            {
                "order": order
            }
        )

    except Exception as error:

        print(
            f"Error retrieving order {order_id}: {error}"
        )

        return response(
            500,
            {
                "message": "Unable to retrieve order"
            }
        )