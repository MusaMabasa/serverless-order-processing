# Serverless Order Processing System on AWS

A production-style **serverless order processing system** built on AWS using event-driven architecture, Infrastructure as Code (IaC), authentication, monitoring, security controls, automated testing, CI, and automatic failure handling.

This project demonstrates practical AWS Cloud Engineering skills including API development, asynchronous processing, serverless compute, NoSQL storage, authentication, observability, security hardening, failure recovery, Infrastructure as Code, and continuous integration.

---

## Architecture

![Serverless Order Processing Architecture](docs/architecture.png)

The application uses an event-driven serverless architecture to securely accept, queue, process, store, and monitor customer orders.

### Core Request Flow

`Client -> Amazon Cognito -> API Gateway -> Create Order Lambda -> Amazon SQS -> Process Order Lambda -> Amazon DynamoDB`

### Failure Handling

`Processing Failure -> SQS Retry -> Dead-Letter Queue`

### Monitoring

`AWS Services -> Amazon CloudWatch -> Amazon SNS -> Email Alerts`

### CI Pipeline

`Git Push -> GitHub Actions -> Unit Tests -> SAM Validation -> SAM Build`

[View detailed architecture and request flow](docs/architecture.md)

---

## AWS Services

| Service            | Purpose                                      |
| ------------------ | -------------------------------------------- |
| Amazon Cognito     | User authentication and JWT token management |
| Amazon API Gateway | Secure REST API endpoint                     |
| AWS Lambda         | Serverless order creation and processing     |
| Amazon SQS         | Asynchronous order queue                     |
| Amazon SQS DLQ     | Stores repeatedly failed messages            |
| Amazon DynamoDB    | Persistent order storage                     |
| Amazon CloudWatch  | Logs, metrics, alarms, and dashboard         |
| Amazon SNS         | Operational alarm notifications              |
| AWS IAM            | Least-privilege permissions                  |
| AWS SAM            | Infrastructure as Code                       |
| AWS CloudFormation | AWS resource provisioning                    |
| GitHub Actions     | Continuous integration                       |
| GitHub             | Source control and project hosting           |

---

## How It Works

### 1. User Authentication

Users authenticate through **Amazon Cognito**.

Cognito provides a JWT token after successful authentication.

The token is included in API requests:

```text
Authorization: Bearer <JWT_TOKEN>
```

API Gateway uses a Cognito Authorizer to validate the token before allowing access to the order API.

Unauthenticated or expired requests are rejected.

---

### 2. Create Order Request

Authenticated clients submit orders using:

```http
POST /orders
```

Example request:

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

API Gateway performs request validation before forwarding valid requests to the Create Order Lambda function.

---

### 3. Create Order Lambda

The **Create Order Lambda**:

* Parses the request body
* Validates customer information
* Validates order items
* Calculates the order total
* Generates a unique order ID
* Adds a creation timestamp
* Sets the initial status to `QUEUED`
* Publishes the order to Amazon SQS

Example response:

```json
{
  "message": "Order accepted for processing",
  "order_id": "ORD-A49434F9",
  "status": "QUEUED"
}
```

The API returns HTTP:

```text
202 Accepted
```

This allows the API to respond without waiting for the complete order-processing operation.

---

### 4. Amazon SQS

Amazon SQS decouples order submission from order processing.

The API-facing Lambda does not directly write the order to DynamoDB.

Instead:

```text
Create Order Lambda
        |
        v
   Amazon SQS
        |
        v
Process Order Lambda
```

This architecture improves:

* Reliability
* Scalability
* Fault tolerance
* Service decoupling
* Failure recovery

SQS server-side encryption is enabled.

---

### 5. Process Order Lambda

The **Process Order Lambda** is triggered automatically when an order becomes available in the SQS queue.

The function:

1. Reads the SQS message
2. Parses the order
3. Validates the `order_id`
4. Changes the order status to `COMPLETED`
5. Adds a `processed_at` timestamp
6. Writes the completed order to DynamoDB

---

### 6. DynamoDB

Processed orders are stored in:

```text
ServerlessOrders
```

Primary key:

```text
order_id
```

Example stored order:

```json
{
  "order_id": "ORD-A49434F9",
  "customer_name": "Mabasa Technologies",
  "customer_email": "customer@example.com",
  "status": "COMPLETED",
  "total": 250,
  "created_at": "2026-09-03T12:13:48+00:00",
  "processed_at": "2026-09-03T12:13:49+00:00"
}
```

DynamoDB security and resilience features include:

* Server-side encryption
* Point-in-Time Recovery
* PAY_PER_REQUEST billing

---

## Failure Handling

The application implements automatic retry and Dead-Letter Queue handling.

```text
Main SQS Queue
      |
      v
Process Lambda
      |
   Failure
      |
      v
SQS Retry
      |
Repeated Failure
      |
      v
Dead-Letter Queue
```

The main queue uses a redrive policy with:

```text
maxReceiveCount = 3
```

Failed messages are retried automatically.

Messages that continue failing are moved to:

```text
serverless-order-dlq
```

This prevents problematic messages from blocking normal order processing.

---

## DLQ Validation

Failure handling was tested using a deliberately invalid SQS message.

The Process Order Lambda failed while parsing the invalid message.

The message was automatically retried and eventually transferred to the Dead-Letter Queue.

The DLQ message showed:

```text
ApproximateReceiveCount: 4
DeadLetterQueueSourceArn: serverless-order-queue
```

This successfully demonstrated:

* Lambda failure handling
* SQS retry behavior
* Redrive policy
* DLQ routing
* Failed-message isolation

The test message was deleted after validation and the DLQ was returned to an empty state.

---

## Security

The project includes multiple AWS security controls.

### Amazon Cognito

The API is protected by an Amazon Cognito User Pool.

Authentication flow:

```text
User
 |
 v
Amazon Cognito
 |
 v
JWT Token
 |
 v
API Gateway
```

API Gateway validates the JWT before invoking the Create Order Lambda.

---

### Optional MFA

Software-token MFA is enabled using:

```text
TOTP
```

MFA configuration:

```text
OPTIONAL
```

Users can therefore configure an authenticator application without MFA being mandatory for every account.

---

### Cognito Token Security

Configured token lifetimes:

| Token         | Lifetime |
| ------------- | -------: |
| Access Token  |   1 hour |
| ID Token      |   1 hour |
| Refresh Token |   7 days |

User-existence error protection is enabled.

Email changes require verification before the new email becomes active.

---

### Password Policy

Cognito password requirements include:

* Minimum 8 characters
* Uppercase characters
* Lowercase characters
* Numbers
* Symbols

---

### API Gateway Throttling

API throttling protects the endpoint against excessive requests.

Configured limits:

```text
Rate Limit: 10 requests/second
Burst Limit: 20 requests
```

CloudWatch API metrics are also enabled.

---

### SQS Encryption

Both queues have Amazon SQS managed server-side encryption enabled:

```text
serverless-order-queue
serverless-order-dlq
```

---

### DynamoDB Protection

The DynamoDB table has:

* Server-side encryption
* Point-in-Time Recovery
* On-demand capacity

This provides data-at-rest protection and recovery capabilities.

---

### IAM Least Privilege

Application Lambda functions use restricted IAM permissions.

The Create Order Lambda receives permission to:

```text
sqs:SendMessage
```

against the required order queue.

The Process Order Lambda receives permission to:

```text
dynamodb:PutItem
```

against the required DynamoDB table.

This reduces unnecessary application permissions.

---

## Request Validation

API Gateway performs request-body validation before invoking the application.

The order model requires:

* `customer_name`
* `customer_email`
* `items`

For example, a request missing `customer_name` is rejected by API Gateway.

Additional business validation is performed inside Lambda.

This creates two validation layers:

```text
API Gateway Validation
        |
        v
Lambda Business Validation
```

Lambda validates:

* Customer name
* Customer email
* Items list
* Product name
* Quantity
* Price

This is important because some JSON Schema constraints are not fully enforced by API Gateway's request-model implementation.

---

## API Access Logging

API Gateway access logging is enabled.

Log group:

```text
/aws/apigateway/serverless-order-api
```

Access logs capture information including:

* Request ID
* Source IP
* Request time
* HTTP method
* Resource path
* HTTP status
* Response size
* Response latency
* Integration latency
* Integration errors

Example:

```json
{
  "httpMethod": "POST",
  "resourcePath": "/orders",
  "status": "202",
  "responseLatency": "895",
  "integrationLatency": "841"
}
```

API Gateway uses an account-level CloudWatch Logs IAM role in the deployment region.

---

## Monitoring and Alerting

Amazon CloudWatch provides centralized monitoring for the application.

The project contains **seven CloudWatch alarms**.

### CloudWatch Alarms

1. Process Order Lambda errors
2. Create Order Lambda errors
3. DLQ messages detected
4. Main queue backlog
5. API Gateway 5XX errors
6. API Gateway 4XX errors
7. API Gateway high latency

These alarms provide visibility across the API, Lambda, SQS, and failure-processing layers.

---

## SNS Notifications

CloudWatch alarms publish notifications to an Amazon SNS topic.

```text
CloudWatch Alarm
       |
       v
   Amazon SNS
       |
       v
Operational Alert
```

This allows operational problems to generate notifications rather than relying solely on manual dashboard monitoring.

---

## CloudWatch Dashboard

A CloudWatch dashboard is deployed through Infrastructure as Code.

Dashboard:

```text
serverless-order-processing-dashboard
```

The dashboard includes widgets for:

* API Gateway requests
* API Gateway errors
* API Gateway latency
* Lambda invocations
* Lambda errors
* SQS queue depth
* Dead-Letter Queue messages
* DynamoDB activity

This provides a centralized operational view of the application.

---

## CloudWatch Logs

Application logs are available under:

```text
/aws/lambda/serverless-create-order
/aws/lambda/serverless-process-order
/aws/apigateway/serverless-order-api
```

Logs are useful for:

* Troubleshooting
* Request tracing
* Error investigation
* Performance analysis
* Operational monitoring

---

## Infrastructure as Code

The AWS infrastructure is defined using:

**AWS Serverless Application Model (SAM)**

The main infrastructure template is:

```text
template.yaml
```

AWS SAM deploys resources through AWS CloudFormation.

Infrastructure managed by the project includes:

* Cognito User Pool
* Cognito App Client
* API Gateway
* Lambda functions
* Lambda IAM roles
* Lambda permissions
* SQS queue
* SQS Dead-Letter Queue
* SQS event source mapping
* DynamoDB table
* CloudWatch alarms
* CloudWatch dashboard
* API Gateway access log group
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

Configure AWS credentials:

```powershell
aws configure
```

The project was developed in:

```text
af-south-1
```

---

### Validate the Template

```powershell
sam validate --template-file template.yaml --lint
```

Expected result:

```text
template.yaml is a valid SAM Template
```

---

### Build

```powershell
sam build
```

The Lambda functions do not currently require third-party Python dependencies, so SAM may report that `requirements.txt` was not found.

That message is expected for the current application.

---

### Deploy

For the initial deployment:

```powershell
sam deploy --guided
```

For subsequent deployments:

```powershell
sam deploy
```

---

## Testing

The project contains automated Python unit tests using:

```text
pytest
```

Tests are located under:

```text
tests/
```

Run them with:

```powershell
python -m pytest -v
```

Current test suite:

```text
8 tests
```

The tests cover both Lambda functions.

---

### Create Order Tests

Tests verify:

* Valid order returns HTTP 202
* Order status is `QUEUED`
* Generated order IDs start with `ORD-`
* SQS `send_message` is called
* Missing customer name returns HTTP 400
* Empty item lists return HTTP 400
* Invalid JSON returns HTTP 400

---

### Process Order Tests

Tests verify:

* Valid orders are written to DynamoDB
* Completed status is applied
* Decimal values are supported
* Missing `order_id` raises an error
* Invalid JSON raises a JSON parsing error
* Multiple SQS records are processed

Current result:

```text
8 passed
```

---

## Continuous Integration

GitHub Actions automatically validates the project.

Workflow:

```text
.github/workflows/ci.yml
```

The workflow runs when:

* Code is pushed to `main`
* A pull request targets `main`

CI pipeline:

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
Install pytest + boto3
   |
   v
Unit Tests
   |
   v
SAM Validation
   |
   v
SAM Build
```

The pipeline automatically checks that application code and infrastructure remain buildable.

---

## GitHub Actions Test Environment

Unit tests use non-production AWS environment variables in GitHub Actions.

These include test-only credentials and resource names.

The unit tests mock AWS service calls and therefore do not require production AWS credentials.

No production AWS access keys are stored in the repository.

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
|   `-- process_order/
|       `-- app.py
|
|-- docs/
|   |-- architecture.md
|   `-- architecture.png
|
|-- tests/
|   |-- test_create_order.py
|   `-- test_process_order.py
|
|-- .gitignore
|-- README.md
`-- template.yaml
```

Local SAM build artifacts and development files are excluded through `.gitignore`.

---

## Troubleshooting and Lessons Learned

This project included practical troubleshooting scenarios that commonly occur in real AWS environments.

### DynamoDB Float Error

An early Lambda execution produced:

```text
TypeError: Float types are not supported. Use Decimal types instead.
```

DynamoDB's Python SDK requires `Decimal` rather than Python floating-point values.

The processor was updated to parse JSON floating-point numbers using `Decimal`.

---

### Invalid SQS JSON

Malformed SQS test messages produced JSON parsing errors such as:

```text
JSONDecodeError: Expecting property name enclosed in double quotes
```

This demonstrated the importance of correct JSON escaping when sending messages through PowerShell and the AWS CLI.

---

### API Authentication

Requests without a valid Cognito JWT correctly returned:

```text
Unauthorized
```

Expired Cognito tokens also caused authentication failures.

Generating a fresh ID token restored authenticated API access.

---

### API Gateway CloudWatch Logging

API Gateway access logging initially failed during deployment because the AWS account did not have an API Gateway CloudWatch Logs role configured.

An API Gateway CloudWatch Logs IAM role was created and configured at the regional account level.

After configuration, SAM deployment succeeded and API access logs were delivered to CloudWatch.

This account-level setting is a deployment prerequisite rather than an application-specific Lambda permission.

---

### Request Validation

API Gateway correctly rejected requests missing required properties.

However, some JSON Schema constraints such as an empty-array `minItems` rule were not enforced as expected by the API Gateway model.

Lambda therefore performs additional business validation.

This provides defense in depth.

---

### SQS Retry and DLQ Testing

A deliberately invalid message was used to verify retry behavior.

The message:

1. Entered the main SQS queue
2. Triggered the processor
3. Failed processing
4. Was automatically retried
5. Reached the configured receive limit
6. Was transferred to the DLQ

This validated the application's failure-recovery architecture.

---

### SAM Template Editing

Several YAML formatting issues were encountered while modifying the SAM template.

These reinforced the importance of running:

```powershell
sam validate --template-file template.yaml --lint
```

before building or deploying infrastructure changes.

---

### GitHub Actions AWS Region

The first CI execution failed with:

```text
NoRegionError: You must specify a region.
```

The test environment was updated with a non-production AWS region and mock AWS credentials.

The workflow subsequently passed.

---

### Infrastructure Ownership

Monitoring resources were initially tested manually and later recreated through AWS SAM.

This ensures the application infrastructure is reproducible and managed through CloudFormation rather than depending on undocumented manual resources.

---

## Reliability Features

The architecture includes several reliability mechanisms:

* Asynchronous SQS processing
* Lambda automatic scaling
* SQS retries
* Dead-Letter Queue
* DynamoDB Point-in-Time Recovery
* CloudWatch monitoring
* CloudWatch alarms
* SNS operational notifications
* Infrastructure as Code
* Automated unit testing
* CI validation

---

## Security Features

Security controls demonstrated by the project include:

* Cognito authentication
* JWT-protected API
* Optional TOTP MFA
* Strong password policy
* Verified email changes
* Reduced token lifetime
* API throttling
* API request validation
* SQS server-side encryption
* DynamoDB encryption
* IAM least privilege
* CloudWatch access logging
* No production credentials committed to Git

---

## Skills Demonstrated

This project demonstrates practical experience with:

### AWS

* AWS Lambda
* Amazon API Gateway
* Amazon SQS
* Amazon DynamoDB
* Amazon Cognito
* Amazon CloudWatch
* Amazon SNS
* AWS IAM
* AWS SAM
* AWS CloudFormation

### Development

* Python
* boto3
* JSON
* REST APIs
* Event-driven architecture
* Asynchronous processing
* Exception handling
* Unit testing
* pytest

### DevOps

* Git
* GitHub
* GitHub Actions
* CI pipelines
* Infrastructure as Code
* Automated SAM validation
* Automated SAM builds

### Security

* JWT authentication
* Cognito authorization
* MFA
* IAM least privilege
* Encryption at rest
* API throttling
* Request validation
* Secure credential handling

### Operations

* CloudWatch Logs
* CloudWatch Metrics
* CloudWatch Alarms
* CloudWatch Dashboards
* SNS notifications
* SQS retry policies
* Dead-Letter Queues
* Troubleshooting distributed AWS applications

---

## Future Improvements

Potential future improvements include:

* `GET /orders` endpoint
* Retrieve individual orders by ID
* Cognito groups and role-based authorization
* Order status updates
* Order cancellation
* DynamoDB indexes
* Amazon SES customer notifications
* AWS X-Ray distributed tracing
* AWS WAF protection
* Custom domain name
* Automated deployment pipeline
* Separate development and production environments
* Desktop client application
* Front-end web application
* CloudWatch custom business metrics

---

## Project Status

Core backend architecture:

**Complete**

Authentication:

**Complete**

Security hardening:

**Complete**

Monitoring and alerting:

**Complete**

CloudWatch dashboard:

**Complete**

SQS retry and DLQ validation:

**Complete**

Infrastructure as Code:

**Complete**

Unit testing:

**Complete**

GitHub Actions CI:

**Complete**

Architecture documentation:

**Complete**

---

## Author

**Musa Mabasa**

AWS Cloud Engineer & IT Professional

* BSc in IT Management
* AWS Certified Cloud Practitioner
* AWS Certified Solutions Architect – Associate
* A+ Certified

This project forms part of my practical AWS cloud engineering portfolio.
