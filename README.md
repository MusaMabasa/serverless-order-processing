# Serverless Order Processing System on AWS

A production-style **serverless order processing system** built on AWS using event-driven architecture, Infrastructure as Code (IaC), authentication, asynchronous processing, monitoring, security controls, automated testing, continuous integration, and failure recovery.

The project demonstrates practical AWS Cloud Engineering skills across REST API development, serverless compute, asynchronous messaging, NoSQL persistence, authentication and authorization, observability, security hardening, Infrastructure as Code, automated testing, and CI.

---

## Architecture

![Serverless Order Processing Architecture](docs/architecture.png)

The system supports four authenticated API operations:

```text
POST /orders
GET  /orders
GET  /orders/{order_id}
```

### Create Order Flow

```text
Client
  |
  v
Amazon Cognito
  |
  v
JWT
  |
  v
API Gateway
  |
  | POST /orders
  v
Create Order Lambda
  |
  v
Amazon SQS
  |
  v
Process Order Lambda
  |
  v
Amazon DynamoDB
```

### Retrieve All Orders Flow

```text
Client
  |
  v
Amazon Cognito
  |
  v
API Gateway
  |
  | GET /orders
  v
Get Orders Lambda
  |
  v
Amazon DynamoDB
```

### Retrieve One Order Flow

```text
Client
  |
  v
Amazon Cognito
  |
  v
API Gateway
  |
  | GET /orders/{order_id}
  v
Get Order Lambda
  |
  v
Amazon DynamoDB
```

### Failure Handling

```text
Processing Failure -> SQS Retry -> Dead-Letter Queue
```

### Monitoring

```text
AWS Services -> CloudWatch -> SNS -> Email Alerts
```

### CI Pipeline

```text
Git Push -> GitHub Actions -> 18 Tests -> SAM Validation -> SAM Build
```

[View detailed architecture](docs/architecture.md)

---

## AWS Services

| Service            | Purpose                                    |
| ------------------ | ------------------------------------------ |
| Amazon Cognito     | Authentication, JWT tokens, optional MFA   |
| Amazon API Gateway | Authenticated REST API                     |
| AWS Lambda         | Create, process, list, retrieve, and update orders |
| Amazon SQS         | Asynchronous order queue                   |
| Amazon SQS DLQ     | Failed-message isolation                   |
| Amazon DynamoDB    | Persistent order storage                   |
| Amazon CloudWatch  | Logs, metrics, alarms, dashboard           |
| Amazon SNS         | Operational notifications                  |
| AWS IAM            | Least-privilege permissions                |
| AWS SAM            | Serverless Infrastructure as Code          |
| AWS CloudFormation | Resource provisioning                      |
| GitHub Actions     | Continuous integration                     |
| GitHub             | Source control and project hosting         |

---

## API Endpoints

| Method | Endpoint             | Purpose                       |
| ------ | -------------------- | ----------------------------- |
| `POST` | `/orders`            | Create a new order            |
| `GET`  | `/orders`            | Retrieve all processed orders |
| `GET`  | `/orders/{order_id}` | Retrieve one order by ID      |
| `PATCH` | `/orders/{order_id}` | Update an order status        |

All endpoints are protected by Amazon Cognito.

Requests without a valid JWT return:

```text
Unauthorized
```

---

## Authentication

Users authenticate through Amazon Cognito.

The JWT is sent to API Gateway:

```text
Authorization: Bearer <JWT_TOKEN>
```

API Gateway uses a Cognito User Pool Authorizer.

The project includes:

* Optional TOTP MFA
* Strong password policy
* Verified email changes
* Short-lived access and ID tokens
* Refresh-token support
* User-existence error protection

Token configuration:

| Token         | Lifetime |
| ------------- | -------: |
| Access Token  |   1 hour |
| ID Token      |   1 hour |
| Refresh Token |   7 days |

---

## POST /orders

Authenticated users submit orders using:

```http
POST /orders
```

Example:

```json
{
  "customer_name": "Mabasa Technologies",
  "customer_email": "customer@example.com",
  "items": [
    {
      "product": "Cloud Server",
      "quantity": 1,
      "price": 250
    }
  ]
}
```

API Gateway validates the request body before invoking Lambda.

The Create Order Lambda:

* Parses the request
* Validates customer data
* Validates item data
* Calculates the total
* Generates an `ORD-` order ID
* Adds a timestamp
* Sets status to `QUEUED`
* Sends the order to SQS

Example response:

```json
{
  "message": "Order accepted for processing",
  "order_id": "ORD-A49434F9",
  "status": "QUEUED"
}
```

HTTP status:

```text
202 Accepted
```

---

## Asynchronous Processing

Amazon SQS decouples API submission from backend processing.

```text
Create Order Lambda
        |
        v
   Amazon SQS
        |
        v
Process Order Lambda
        |
        v
Amazon DynamoDB
```

Benefits include:

* Reliability
* Scalability
* Traffic buffering
* Service decoupling
* Retry handling
* Failure isolation

The SQS queue uses server-side encryption.

---

## Process Order Lambda

The Process Order Lambda is triggered automatically by SQS.

It:

1. Reads each SQS record
2. Parses the order
3. Validates `order_id`
4. Sets status to `COMPLETED`
5. Adds `processed_at`
6. Writes the order to DynamoDB

IAM permission:

```text
dynamodb:PutItem
```

---

## DynamoDB

Orders are stored in:

```text
ServerlessOrders
```

Primary key:

```text
order_id
```

Features:

* Server-side encryption
* Point-in-Time Recovery
* PAY_PER_REQUEST billing

Example:

```json
{
  "order_id": "ORD-7ED11B6E",
  "customer_name": "Mabasa Technologies",
  "customer_email": "customer@example.com",
  "status": "COMPLETED",
  "total": 100
}
```

---

## GET /orders

The list endpoint retrieves processed orders:

```http
GET /orders
```

The Get Orders Lambda:

* Scans DynamoDB
* Handles `LastEvaluatedKey`
* Retrieves multiple scan pages
* Sorts by `created_at`
* Returns newest-first results
* Converts DynamoDB `Decimal` values to JSON-compatible values
* Returns HTTP 500 on DynamoDB errors

IAM permission:

```text
dynamodb:Scan
```

Example response:

```json
{
  "count": 6,
  "orders": []
}
```

---

## GET /orders/{order_id}

The single-order endpoint retrieves one order directly by primary key:

```http
GET /orders/{order_id}
```

Example:

```text
GET /orders/ORD-7ED11B6E
```

The Get Order Lambda uses:

```text
dynamodb:GetItem
```

This is more efficient than scanning the table because the order ID is already known.

The function:

* Reads `order_id` from API Gateway path parameters
* Calls DynamoDB `GetItem`
* Converts DynamoDB Decimal values
* Returns the order when found
* Returns HTTP 404 when the order does not exist
* Returns HTTP 400 when the path parameter is missing
* Returns HTTP 500 on DynamoDB errors

Successful live retrieval returned:

```text
order_id: ORD-7ED11B6E
status: COMPLETED
total: 100
```

A nonexistent order correctly returned:

```json
{
  "message": "Order not found",
  "order_id": "ORD-NOTFOUND"
}
```

An unauthenticated request correctly returned:

```json
{
  "message": "Unauthorized"
}
```

---

## Failure Handling

The main SQS queue has a redrive policy:

```text
maxReceiveCount = 3
```

Failure flow:

```text
Main Queue
   |
   v
Process Lambda
   |
 Failure
   |
   v
Retry
   |
Repeated Failure
   |
   v
Dead-Letter Queue
```

The DLQ is:

```text
serverless-order-dlq
```

Failure handling was validated using a deliberately malformed SQS message.

---

## Security

Security controls include:

* Cognito authentication
* JWT-protected API
* Optional TOTP MFA
* Strong password policy
* Verified email changes
* Token lifetime controls
* API throttling
* Request validation
* IAM least privilege
* SQS encryption
* DynamoDB encryption
* Point-in-Time Recovery
* API access logging
* No production credentials stored in Git

---

## IAM Least Privilege

The application Lambda functions use restricted permissions.

### Create Order Lambda

```text
sqs:SendMessage
```

### Process Order Lambda

```text
dynamodb:PutItem
```

### Get Orders Lambda

```text
dynamodb:Scan
```

### Get Order Lambda

```text
dynamodb:GetItem
```

---

## API Gateway Throttling

Configured limits:

```text
Rate Limit: 10 requests/second
Burst Limit: 20 requests
```

CloudWatch metrics are enabled for API Gateway.

---

## Request Validation

`POST /orders` requires:

* `customer_name`
* `customer_email`
* `items`

Validation happens at two levels:

```text
API Gateway Validation
        |
        v
Lambda Validation
```

Lambda also validates:

* Product
* Quantity
* Price
* Empty item lists
* Invalid JSON

---

## API Access Logging

API Gateway access logs are sent to:

```text
/aws/apigateway/serverless-order-api
```

Captured fields include:

* Request ID
* Source IP
* Request time
* HTTP method
* Resource path
* Status
* Response size
* Response latency
* Integration latency
* Integration error

---

## CloudWatch Logs

Relevant log groups include:

```text
/aws/lambda/serverless-create-order
/aws/lambda/serverless-process-order
/aws/lambda/serverless-get-orders
/aws/lambda/serverless-get-order
/aws/apigateway/serverless-order-api
```

---

## Monitoring and Alerting

The project now contains **10 CloudWatch alarms**.

### Alarms

1. Create Order Lambda errors
2. Process Order Lambda errors
3. Get Orders Lambda errors
4. Get Order Lambda errors
5. DLQ messages
6. Main SQS queue backlog
7. API Gateway 5XX errors
8. API Gateway 4XX errors
9. API Gateway high latency

The new single-order alarm is:

```text
serverless-get-order-errors
```

It was successfully verified in:

```text
OK
```

state.

---

## SNS Notifications

CloudWatch alarms publish to Amazon SNS.

```text
CloudWatch Alarm
       |
       v
Amazon SNS
       |
       v
Email Alert
```

---

## CloudWatch Dashboard

Dashboard:

```text
serverless-order-processing-dashboard
```

It tracks:

* API requests
* API errors
* API latency
* Lambda invocations
* Lambda errors
* SQS queue depth
* DLQ messages
* DynamoDB activity

---

## Infrastructure as Code

Infrastructure is defined in:

```text
template.yaml
```

using AWS SAM.

AWS SAM deploys through CloudFormation.

Managed resources include:

* Cognito User Pool
* Cognito App Client
* API Gateway
* Cognito Authorizer
* 5 Lambda functions
* Lambda IAM roles
* Lambda permissions
* Main SQS queue
* DLQ
* SQS event source mapping
* DynamoDB table
* 10 CloudWatch alarms
* CloudWatch dashboard
* API access log group
* SNS topic
* SNS subscription

---

## Deployment

### Prerequisites

Install:

* AWS CLI
* AWS SAM CLI
* Python 3.13
* Git

Configure AWS:

```powershell
aws configure
```

Region:

```text
af-south-1
```

### Validate

```powershell
sam validate --template-file template.yaml --lint
```

### Build

```powershell
sam build
```

Expected:

```text
Build Succeeded
```

### Deploy

```powershell
sam deploy `
  --parameter-overrides AlertEmail=<YOUR_EMAIL_ADDRESS>
```

Stack:

```text
serverless-order-processing
```

---

## Automated Testing

The project now has **27 passing pytest tests**.

Run:

```powershell
python -m pytest -v
```

Expected:

```text
27 passed
```

### Create Order Tests

Covers:

* Valid order
* Missing customer name
* Empty items
* Invalid JSON

### Get Orders Tests

Covers:

* HTTP 200
* Empty table
* Sorting
* Pagination
* DynamoDB error handling

### Get Order Tests

Covers:

* HTTP 200
* HTTP 404
* Missing `order_id`
* Missing path parameters
* DynamoDB error handling

### Process Order Tests

Covers:

* DynamoDB write
* Missing order ID
* Invalid JSON
* Multiple SQS records

---

## Continuous Integration

GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

Runs on:

* Pushes to `main`
* Pull requests to `main`

Pipeline:

```text
Git Push
   |
   v
GitHub Actions
   |
   v
Python 3.13
   |
   v
27 Unit Tests
   |
   v
SAM Validation
   |
   v
SAM Build
```

The latest single-order feature commit passed the GitHub Actions workflow successfully.

---

## Project Structure

```text
serverless-order-processing/
|
|-- .github/
|   `-- workflows/
|       `-- ci.yml
|
|-- backend/
|   |-- create_order/
|   |   `-- app.py
|   |
|   |-- get_orders/
|   |   `-- app.py
|   |
|   |-- get_order/
|   |   `-- app.py
|   |
|   `-- process_order/
|       `-- app.py
|
|-- docs/
|   |-- architecture.md
|   `-- architecture.png
|
|-- tests/
|   |-- test_create_order.py
|   |-- test_get_orders.py
|   |-- test_get_order.py
|   `-- test_process_order.py
|
|-- .gitignore
|-- README.md
|-- samconfig.toml
`-- template.yaml
```

---

## Troubleshooting and Lessons Learned

This project included practical AWS engineering issues and fixes.

### DynamoDB Float Handling

DynamoDB rejected Python floats.

Solution:

```text
Decimal
```

was used for numeric handling.

### DynamoDB JSON Serialization

DynamoDB returns numeric values as `Decimal`.

Custom JSON encoding converts them for API responses.

### DynamoDB Pagination

`GET /orders` handles:

```text
LastEvaluatedKey
```

to retrieve additional result pages.

### SQS Invalid JSON

Malformed SQS messages were used to test retry and DLQ behavior.

### Cognito Token Expiry

Expired tokens returned:

```text
Unauthorized
```

A fresh ID token restored access.

### API Gateway CloudWatch Role

API Gateway access logging initially failed because the regional CloudWatch Logs role was not configured.

### GitHub Actions Region Error

The first CI run failed with:

```text
NoRegionError: You must specify a region.
```

The CI test environment was updated with a test AWS region and mock credentials.

### SAM YAML Errors

Template editing produced YAML indentation and code-fence errors.

Running:

```powershell
sam validate --template-file template.yaml --lint
```

before builds prevented broken deployments.

### CloudFormation Resource Ownership

CloudFormation logical resource IDs had to remain consistent with previously deployed resources.

### Required Alert Parameter

Deployments require:

```text
AlertEmail
```

### Single Order Retrieval

Using `GetItem` instead of `Scan` for:

```text
GET /orders/{order_id}
```

demonstrates efficient primary-key access.

---

## Reliability Features

* Event-driven design
* Asynchronous processing
* SQS retries
* Dead-Letter Queue
* Lambda scaling
* DynamoDB Point-in-Time Recovery
* DynamoDB pagination support
* CloudWatch monitoring
* 10 CloudWatch alarms
* SNS notifications
* Automated testing
* GitHub Actions CI
* Infrastructure as Code

---

## Skills Demonstrated

### AWS

* AWS Lambda
* API Gateway
* SQS
* DynamoDB
* Cognito
* CloudWatch
* SNS
* IAM
* SAM
* CloudFormation

### Development

* Python 3.13
* boto3
* REST APIs
* JSON
* Event-driven architecture
* Asynchronous processing
* DynamoDB pagination
* Error handling
* Unit testing
* pytest

### DevOps

* Git
* GitHub
* GitHub Actions
* CI
* Infrastructure as Code
* SAM validation
* SAM builds
* CloudFormation deployments

### Security

* JWT authentication
* Cognito authorization
* Optional MFA
* IAM least privilege
* Encryption at rest
* API throttling
* Request validation
* Secure credential handling

### Operations

* CloudWatch Logs
* CloudWatch Metrics
* CloudWatch Alarms
* CloudWatch Dashboard
* SNS
* DLQ monitoring
* API access logging
* AWS troubleshooting

---

## Future Improvements

Potential next improvements include:

* `PATCH /orders/{order_id}`
* Order cancellation
* DynamoDB Query-based list retrieval
* API pagination tokens
* Cognito groups and RBAC
* Amazon SES notifications
* AWS X-Ray
* API custom domain
* Automated deployment pipeline
* Dev/staging/prod environments
* Front-end application
* Desktop client
* Business metrics

---

## Project Status

| Component                   | Status   |
| --------------------------- | -------- |
| `POST /orders`              | Complete |
| `GET /orders`               | Complete |
| `GET /orders/{order_id}`    | Complete |
| Cognito authentication      | Complete |
| Optional MFA                | Complete |
| Asynchronous SQS processing | Complete |
| DynamoDB persistence        | Complete |
| DLQ handling                | Complete |
| API validation              | Complete |
| Security hardening          | Complete |
| 10 CloudWatch alarms         | Complete |
| CloudWatch dashboard        | Complete |
| SNS notifications           | Complete |
| Infrastructure as Code      | Complete |
| 27 automated tests          | Complete |
| GitHub Actions CI           | Complete |
| Architecture documentation  | Complete |

---

## Author

**Musa Mabasa**

AWS Cloud Engineer & IT Professional

* BSc in IT Management
* AWS Certified Cloud Practitioner
* AWS Certified Solutions Architect - Associate
* A+ Certified

This project forms part of my practical AWS Cloud Engineering portfolio.
