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

    print("Get Orders request received")

    try:
        result = table.scan()

        orders = result.get("Items", [])

        while "LastEvaluatedKey" in result:
            result = table.scan(
                ExclusiveStartKey=result["LastEvaluatedKey"]
            )

            orders.extend(
                result.get("Items", [])
            )

        orders.sort(
            key=lambda order: order.get(
                "created_at",
                ""
            ),
            reverse=True
        )

        print(
            f"Retrieved {len(orders)} order(s)"
        )

        return response(
            200,
            {
                "count": len(orders),
                "orders": orders
            }
        )

    except Exception as error:

        print(
            f"Error retrieving orders: {error}"
        )

        return response(
            500,
            {
                "message": "Unable to retrieve orders"
            }
        )