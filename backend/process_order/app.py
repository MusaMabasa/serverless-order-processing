import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["ORDERS_TABLE"])


def lambda_handler(event, context):
    """
    Process orders received from Amazon SQS
    and store completed orders in DynamoDB.
    """

    records = event.get("Records", [])

    print(f"Received {len(records)} SQS record(s)")

    for record in records:

        # Parse JSON numbers as Decimal instead of float.
        # DynamoDB supports Decimal but not Python float.
        order = json.loads(
            record["body"],
            parse_float=Decimal
        )

        print(f"Processing order: {order}")

        order_id = order.get("order_id")

        if not order_id:
            raise ValueError("order_id is required")

        order["status"] = "COMPLETED"

        order["processed_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        table.put_item(
            Item=order
        )

        print(
            f"Order {order_id} processed successfully"
        )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Orders processed successfully"
            }
        )
    }