# Serverless Order Processing Architecture

```mermaid
flowchart LR

    User["Client / User"]
    Cognito["Amazon Cognito<br/>Authentication<br/>Optional TOTP MFA"]
    APIGW["Amazon API Gateway<br/>POST /orders<br/>Cognito Authorizer<br/>Request Validation<br/>Throttling"]
    CreateLambda["AWS Lambda<br/>Create Order<br/>Python 3.13"]
    SQS["Amazon SQS<br/>Order Queue<br/>SSE Enabled"]
    ProcessLambda["AWS Lambda<br/>Process Order<br/>Python 3.13"]
    DynamoDB["Amazon DynamoDB<br/>ServerlessOrders<br/>Encryption + PITR"]
    DLQ["Amazon SQS<br/>Dead-Letter Queue"]
    CloudWatch["Amazon CloudWatch<br/>Logs / Metrics<br/>Dashboard / 7 Alarms"]
    SNS["Amazon SNS<br/>Operational Alerts"]
    SAM["AWS SAM / CloudFormation<br/>Infrastructure as Code"]
    GitHub["GitHub Actions<br/>Unit Tests / Validate / Build"]

    User -->|"Authenticate"| Cognito
    Cognito -->|"JWT Token"| User

    User -->|"POST /orders + JWT"| APIGW
    APIGW -->|"Authorized Request"| CreateLambda

    CreateLambda -->|"Send Message"| SQS
    SQS -->|"Event Source"| ProcessLambda
    ProcessLambda -->|"PutItem"| DynamoDB

    SQS -->|"Repeated Failures"| DLQ

    APIGW -.->|"Logs / Metrics"| CloudWatch
    CreateLambda -.->|"Logs / Metrics"| CloudWatch
    ProcessLambda -.->|"Logs / Metrics"| CloudWatch
    SQS -.->|"Queue Metrics"| CloudWatch
    DLQ -.->|"DLQ Metrics"| CloudWatch
    DynamoDB -.->|"Metrics"| CloudWatch

    CloudWatch -->|"Alarm Notifications"| SNS

    SAM -.-> APIGW
    SAM -.-> Cognito
    SAM -.-> CreateLambda
    SAM -.-> SQS
    SAM -.-> ProcessLambda
    SAM -.-> DynamoDB
    SAM -.-> CloudWatch
    SAM -.-> SNS

    GitHub -->|"CI Validation"| SAM
```

## Request Flow

1. The client authenticates using Amazon Cognito.
2. Cognito returns a JWT token.
3. The client submits an authenticated `POST /orders` request to Amazon API Gateway.
4. API Gateway validates authentication, request structure, and throttling limits.
5. Create Order Lambda validates the order and publishes it to Amazon SQS.
6. Amazon SQS decouples order submission from asynchronous processing.
7. Process Order Lambda consumes the SQS message.
8. The processed order is stored in Amazon DynamoDB with status `COMPLETED`.
9. Failed messages are retried and eventually moved to the Dead-Letter Queue.
10. Amazon CloudWatch collects logs, metrics, alarms, and dashboard data.
11. CloudWatch alarms send notifications through Amazon SNS.

## CI Pipeline

GitHub Actions automatically runs on pushes and pull requests to `main`.

`Git Push -> Unit Tests -> SAM Validation -> SAM Build`