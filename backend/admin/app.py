import json
from decimal import Decimal
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


REGION = os.environ.get("AWS_REGION", "af-south-1")
USER_POOL_ID = os.environ["USER_POOL_ID"]
ORDERS_TABLE = os.environ["ORDERS_TABLE"]

cognito = boto3.client("cognito-idp", region_name=REGION)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ORDERS_TABLE)


def json_default(value):
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)

    raise TypeError(
        f"Object of type {value.__class__.__name__} "
        "is not JSON serializable"
    )

def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,PATCH,OPTIONS",
        },
        "body": json.dumps(body, default=json_default),
    }


def get_claims(event):
    return (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )


def get_current_username(event):
    claims = get_claims(event)

    return (
        claims.get("cognito:username")
        or claims.get("username")
        or ""
    )




def get_current_identity(event):
    claims = get_claims(event)

    given_name = str(
        claims.get("given_name", "")
    ).strip()

    family_name = str(
        claims.get("family_name", "")
    ).strip()

    full_name = " ".join(
        part
        for part in (
            given_name,
            family_name,
        )
        if part
    )

    return (
        full_name
        or claims.get("email")
        or claims.get("cognito:username")
        or claims.get("username")
        or "Unknown administrator"
    )

def require_admin(event):
    claims = get_claims(event)
    raw_groups = claims.get("cognito:groups", "")

    if isinstance(raw_groups, list):
        groups = raw_groups
    else:
        groups = [
            group.strip().strip('"').strip("'")
            for group in str(raw_groups).strip("[]").split(",")
            if group.strip()
        ]

    return "Admins" in groups


def parse_body(event):
    try:
        return json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return None


def client_error_message(error, default_message):
    return (
        error.response
        .get("Error", {})
        .get("Message", default_message)
    )


def list_users():
    users = []
    pagination_token = None

    while True:
        kwargs = {
            "UserPoolId": USER_POOL_ID,
            "Limit": 60,
        }

        if pagination_token:
            kwargs["PaginationToken"] = pagination_token

        result = cognito.list_users(**kwargs)

        for user in result.get("Users", []):
            attributes = {
                attribute["Name"]: attribute["Value"]
                for attribute in user.get("Attributes", [])
            }

            groups_result = cognito.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=user["Username"],
            )

            groups = [
                group["GroupName"]
                for group in groups_result.get("Groups", [])
            ]

            users.append({
                "username": user["Username"],
                "given_name": attributes.get("given_name", ""),
                "family_name": attributes.get("family_name", ""),
                "email": attributes.get("email", ""),
                "enabled": user.get("Enabled", False),
                "status": user.get("UserStatus", ""),
                "groups": groups,
                "is_admin": "Admins" in groups,
            })

        pagination_token = result.get("PaginationToken")

        if not pagination_token:
            break

    return response(
        200,
        {
            "count": len(users),
            "users": users,
        },
    )


def create_user(body):
    given_name = str(
        body.get("given_name", "")
    ).strip()

    family_name = str(
        body.get("family_name", "")
    ).strip()

    email = str(
        body.get("email", "")
    ).strip()

    temporary_password = str(
        body.get("temporary_password", "")
    )

    is_admin = bool(
        body.get("is_admin", False)
    )

    if not given_name:
        return response(
            400,
            {"message": "Name is required"},
        )

    if not family_name:
        return response(
            400,
            {"message": "Surname is required"},
        )

    if not email:
        return response(
            400,
            {"message": "Email is required"},
        )

    if not temporary_password:
        return response(
            400,
            {
                "message":
                "Temporary password is required"
            },
        )

    try:
        result = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,

            Username=email,

            UserAttributes=[
                {
                    "Name": "given_name",
                    "Value": given_name,
                },
                {
                    "Name": "family_name",
                    "Value": family_name,
                },
                {
                    "Name": "email",
                    "Value": email,
                },
                {
                    "Name": "email_verified",
                    "Value": "true",
                },
            ],

            TemporaryPassword=temporary_password,

            DesiredDeliveryMediums=[
                "EMAIL"
            ],
        )

        username = result["User"]["Username"]

        if is_admin:
            cognito.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName="Admins",
            )

        return response(
            201,
            {
                "message":
                "User created successfully",

                "username":
                username,

                "given_name":
                given_name,

                "family_name":
                family_name,

                "full_name":
                f"{given_name} {family_name}",

                "email":
                email,

                "admin":
                is_admin,
            },
        )

    except ClientError as error:
        return response(
            400,
            {
                "message":
                client_error_message(
                    error,
                    "Unable to create user",
                )
            },
        )

def delete_user(username, current_username):
    if not username:
        return response(
            400,
            {"message": "username is required"},
        )

    # Prevent administrator from deleting own active account.
    if username == current_username:
        return response(
            409,
            {
                "message": (
                    "You cannot delete your own "
                    "administrator account."
                )
            },
        )

    try:
        cognito.admin_delete_user(
            UserPoolId=USER_POOL_ID,
            Username=username,
        )

        return response(
            200,
            {
                "message": "User deleted successfully",
                "username": username,
            },
        )

    except ClientError as error:
        return response(
            400,
            {
                "message": client_error_message(
                    error,
                    "Unable to delete user",
                )
            },
        )


def set_user_enabled(
    username,
    enabled,
    current_username,
):
    if not username:
        return response(
            400,
            {"message": "username is required"},
        )

    if username == current_username and not enabled:
        return response(
            409,
            {
                "message": (
                    "You cannot disable your own "
                    "administrator account."
                )
            },
        )

    try:
        if enabled:
            cognito.admin_enable_user(
                UserPoolId=USER_POOL_ID,
                Username=username,
            )
        else:
            cognito.admin_disable_user(
                UserPoolId=USER_POOL_ID,
                Username=username,
            )

        return response(
            200,
            {
                "message": (
                    "User enabled"
                    if enabled
                    else "User disabled"
                ),
                "username": username,
                "enabled": enabled,
            },
        )

    except ClientError as error:
        return response(
            400,
            {
                "message": client_error_message(
                    error,
                    "Unable to update user",
                )
            },
        )


def set_admin_status(
    username,
    is_admin,
    current_username,
):
    if not username:
        return response(
            400,
            {"message": "username is required"},
        )

    # Prevent the signed-in administrator from accidentally
    # removing their own administrative access.
    if username == current_username and not is_admin:
        return response(
            409,
            {
                "message": (
                    "You cannot revoke your own "
                    "administrator access."
                )
            },
        )

    try:
        if is_admin:
            cognito.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName="Admins",
            )

            message = "Administrator access granted"

        else:
            cognito.admin_remove_user_from_group(
                UserPoolId=USER_POOL_ID,
                Username=username,
                GroupName="Admins",
            )

            message = "Administrator access revoked"

        return response(
            200,
            {
                "message": message,
                "username": username,
                "admin": is_admin,
            },
        )

    except ClientError as error:
        return response(
            400,
            {
                "message": client_error_message(
                    error,
                    "Unable to update administrator access",
                )
            },
        )


def update_user(
    username,
    body,
    current_username,
):
    if "enabled" in body:
        return set_user_enabled(
            username,
            bool(body["enabled"]),
            current_username,
        )

    if "is_admin" in body:
        return set_admin_status(
            username,
            bool(body["is_admin"]),
            current_username,
        )

    return response(
        400,
        {
            "message": (
                "Specify either enabled or is_admin."
            )
        },
    )


def list_deleted_orders():
    try:
        result = table.scan(
            FilterExpression="#status = :deleted_status",
            ExpressionAttributeNames={
                "#status": "status",
            },
            ExpressionAttributeValues={
                ":deleted_status": "DELETED",
            },
        )

        orders = result.get("Items", [])

        while "LastEvaluatedKey" in result:
            result = table.scan(
                FilterExpression="#status = :deleted_status",
                ExpressionAttributeNames={
                    "#status": "status",
                },
                ExpressionAttributeValues={
                    ":deleted_status": "DELETED",
                },
                ExclusiveStartKey=result["LastEvaluatedKey"],
            )

            orders.extend(
                result.get("Items", [])
            )

        orders.sort(
            key=lambda order: order.get(
                "deleted_at",
                ""
            ),
            reverse=True,
        )

        return response(
            200,
            {
                "count": len(orders),
                "orders": orders,
            },
        )

    except ClientError as error:
        print(
            "DynamoDB list_deleted_orders error:",
            error,
        )

        return response(
            500,
            {
                "message": (
                    "Unable to retrieve deleted orders"
                )
            },
        )

def delete_order(order_id, actor):
    if not order_id:
        return response(
            400,
            {"message": "order_id is required"},
        )

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    actor = str(
        actor or "Unknown administrator"
    ).strip()

    try:
        result = table.update_item(
            Key={
                "order_id": order_id,
            },

            UpdateExpression=(
                "SET #previous_status = #status, "
                "#status = :deleted_status, "
                "#deleted_at = :deleted_at, "
                "#deleted_by = :deleted_by"
            ),

            ConditionExpression=(
                "attribute_exists(order_id) "
                "AND #status <> :deleted_status"
            ),

            ExpressionAttributeNames={
                "#status": "status",
                "#previous_status": "previous_status",
                "#deleted_at": "deleted_at",
                "#deleted_by": "deleted_by",
            },

            ExpressionAttributeValues={
                ":deleted_status": "DELETED",
                ":deleted_at": timestamp,
                ":deleted_by": actor,
            },

            ReturnValues="ALL_NEW",
        )

        return response(
            200,
            {
                "message": "Order moved to Deleted Orders",
                "order_id": order_id,
                "status": "DELETED",
                "deleted_at": timestamp,
                "deleted_by": actor,
                "previous_status": (
                    result
                    .get("Attributes", {})
                    .get("previous_status")
                ),
            },
        )

    except ClientError as error:
        code = (
            error.response
            .get("Error", {})
            .get("Code")
        )

        if code == "ConditionalCheckFailedException":
            return response(
                409,
                {
                    "message": (
                        "Order was not found or has "
                        "already been deleted."
                    ),
                    "order_id": order_id,
                },
            )

        print(
            "DynamoDB delete_order error:",
            error,
        )

        return response(
            500,
            {"message": "Unable to delete order"},
        )


def restore_order(order_id, actor):
    if not order_id:
        return response(
            400,
            {"message": "order_id is required"},
        )

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    actor = str(
        actor or "Unknown administrator"
    ).strip()

    try:
        existing = table.get_item(
            Key={
                "order_id": order_id,
            },
            ConsistentRead=True,
        ).get("Item")

        if not existing:
            return response(
                404,
                {
                    "message": "Order not found",
                    "order_id": order_id,
                },
            )

        if existing.get("status") != "DELETED":
            return response(
                409,
                {
                    "message": "Order is not deleted",
                    "order_id": order_id,
                },
            )

        previous_status = str(
            existing.get(
                "previous_status",
                "QUEUED",
            )
        ).strip().upper()

        if previous_status not in {
            "QUEUED",
            "ACCEPTED",
            "COMPLETED",
        }:
            previous_status = "QUEUED"

        table.update_item(
            Key={
                "order_id": order_id,
            },

            UpdateExpression=(
                "SET #status = :restored_status, "
                "#restored_at = :restored_at, "
                "#restored_by = :restored_by "
                "REMOVE #deleted_at, "
                "#deleted_by, "
                "#previous_status"
            ),

            ConditionExpression=(
                "attribute_exists(order_id) "
                "AND #status = :deleted_status"
            ),

            ExpressionAttributeNames={
                "#status": "status",
                "#restored_at": "restored_at",
                "#restored_by": "restored_by",
                "#deleted_at": "deleted_at",
                "#deleted_by": "deleted_by",
                "#previous_status": "previous_status",
            },

            ExpressionAttributeValues={
                ":restored_status": previous_status,
                ":deleted_status": "DELETED",
                ":restored_at": timestamp,
                ":restored_by": actor,
            },

            ReturnValues="NONE",
        )

        return response(
            200,
            {
                "message": "Order restored successfully",
                "order_id": order_id,
                "status": previous_status,
                "restored_at": timestamp,
                "restored_by": actor,
            },
        )

    except ClientError as error:
        code = (
            error.response
            .get("Error", {})
            .get("Code")
        )

        if code == "ConditionalCheckFailedException":
            return response(
                409,
                {
                    "message": (
                        "Order could not be restored "
                        "because its status changed."
                    ),
                    "order_id": order_id,
                },
            )

        print(
            "DynamoDB restore_order error:",
            error,
        )

        return response(
            500,
            {"message": "Unable to restore order"},
        )

def update_order_status(order_id, body, actor):
    if not order_id:
        return response(
            400,
            {"message": "order_id is required"},
        )

    requested_status = str(
        body.get("status", "")
    ).strip().upper()

    transitions = {
        "ACCEPTED": {
            "from": "QUEUED",
            "message": "Order accepted successfully",
            "timestamp_field": "accepted_at",
            "actor_field": "accepted_by",
        },

        "COMPLETED": {
            "from": "ACCEPTED",
            "message": "Order completed successfully",
            "timestamp_field": "completed_at",
            "actor_field": "completed_by",
        },
    }

    if requested_status not in transitions:
        return response(
            400,
            {
                "message":
                "status must be ACCEPTED or COMPLETED"
            },
        )

    transition = transitions[requested_status]

    timestamp_field = transition["timestamp_field"]
    actor_field = transition["actor_field"]

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    actor = str(
        actor or "Unknown administrator"
    ).strip()

    try:
        table.update_item(
            Key={
                "order_id": order_id
            },

            UpdateExpression=(
                "SET #status = :new_status, "
                "#timestamp = :timestamp, "
                "#actor = :actor"
            ),

            ConditionExpression=(
                "attribute_exists(order_id) "
                "AND #status = :current_status"
            ),

            ExpressionAttributeNames={
                "#status": "status",
                "#timestamp": timestamp_field,
                "#actor": actor_field,
            },

            ExpressionAttributeValues={
                ":new_status": requested_status,
                ":current_status": transition["from"],
                ":timestamp": timestamp,
                ":actor": actor,
            },

            ReturnValues="NONE",
        )

        return response(
            200,
            {
                "message": transition["message"],
                "order_id": order_id,
                "status": requested_status,
                timestamp_field: timestamp,
                actor_field: actor,
            },
        )

    except ClientError as error:
        code = (
            error.response
            .get("Error", {})
            .get("Code")
        )

        if code == "ConditionalCheckFailedException":
            return response(
                409,
                {
                    "message": (
                        f"Order cannot transition to "
                        f"{requested_status}. "
                        f"Current status must be "
                        f"{transition['from']}."
                    )
                },
            )

        print(
            "DynamoDB update_order_status error:",
            error,
        )

        return response(
            500,
            {
                "message":
                "Unable to update order status"
            },
        )

def lambda_handler(event, context):
    if not require_admin(event):
        return response(
            403,
            {"message": "Administrator access required"},
        )

    method = event.get("httpMethod", "")
    path = event.get("path", "")
    parameters = event.get("pathParameters") or {}

    current_username = get_current_username(event)

    if method == "GET" and path.endswith("/admin/users"):
        return list_users()

    if method == "POST" and path.endswith("/admin/users"):
        body = parse_body(event)

        if body is None:
            return response(
                400,
                {"message": "Invalid JSON body"},
            )

        return create_user(body)

    if (
        method == "DELETE"
        and "/admin/users/" in path
    ):
        return delete_user(
            parameters.get("username"),
            current_username,
        )

    if (
        method == "PATCH"
        and "/admin/users/" in path
    ):
        body = parse_body(event)

        if body is None:
            return response(
                400,
                {"message": "Invalid JSON body"},
            )

        return update_user(
            parameters.get("username"),
            body,
            current_username,
        )



    if (
        method == "GET"
        and path == "/admin/orders/deleted"
    ):
        return list_deleted_orders()
    if (
        method == "PATCH"
        and "/admin/orders/" in path
        and path.endswith("/restore")
    ):
        return restore_order(
            parameters.get("order_id"),
            get_current_identity(event),
        )
    if (
        method == "PATCH"
        and "/admin/orders/" in path
    ):
        body = parse_body(event)
        if body is None:
            return response(400, {"message": "Invalid JSON body"})
        return update_order_status(
            parameters.get("order_id"),
            body,
            get_current_identity(event),
        )
    if (
        method == "DELETE"
        and "/admin/orders/" in path
    ):
        return delete_order(
            parameters.get("order_id"),
            get_current_identity(event),
        )

    return response(
        404,
        {"message": "Admin operation not found"},
    )










