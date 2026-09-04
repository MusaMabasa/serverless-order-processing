# Serverless Order Processing System on AWS



A production-style serverless order processing system built on AWS using event-driven architecture, Infrastructure as Code (IaC), authentication, monitoring, security controls, and automatic failure handling.



This project demonstrates practical AWS cloud engineering skills including API development, asynchronous processing, serverless compute, NoSQL storage, authentication, observability, security hardening, failure recovery, and Infrastructure as Code.



## Architecture



The application follows this flow:



```text

Client

&#x20; |

&#x20; v

Amazon Cognito

&#x20; |

&#x20; v

Amazon API Gateway

&#x20; |

&#x20; v

Create Order Lambda

&#x20; |

&#x20; v

Amazon SQS

&#x20; |

&#x20; v

Process Order Lambda

&#x20; |

&#x20; v

Amazon DynamoDB



Processing Failure

&#x20; |

&#x20; v

SQS Retry

&#x20; |

&#x20; v

Dead-Letter Queue



Monitoring

&#x20; |

&#x20; v

Amazon CloudWatch

&#x20; |

&#x20; v

Amazon SNS

&#x20; |

&#x20; v

Email Alerts

```



## AWS Services



| Service            | Purpose                                           |

| ------------------ | ------------------------------------------------- |

| Amazon API Gateway | Provides the REST API endpoint                    |

| Amazon Cognito     | Authenticates and authorizes API users            |

| AWS Lambda         | Runs serverless application logic                 |

| Amazon SQS         | Provides asynchronous order processing            |

| Amazon SQS DLQ     | Isolates messages that repeatedly fail processing |

| Amazon DynamoDB    | Stores completed orders                           |

| Amazon CloudWatch  | Provides logs, metrics, alarms, and dashboards    |

| Amazon SNS         | Sends monitoring notifications                    |

| AWS IAM            | Provides least-privilege access control           |

| AWS SAM            | Defines and deploys serverless infrastructure     |

| AWS CloudFormation | Manages deployed AWS resources                    |



## How It Works



### 1. Authentication



Users authenticate through Amazon Cognito.



API Gateway uses a Cognito authorizer, preventing unauthenticated clients from creating orders.



The Cognito configuration includes:



\* Email-based usernames

\* Verified email addresses

\* Password policy enforcement

\* Optional software-token TOTP MFA

\* Verification before email attribute updates

\* 1-hour access tokens

\* 1-hour ID tokens

\* 7-day refresh tokens

\* User-existence error protection



### 2. Order Submission



An authenticated client sends an HTTP POST request to:



```text

POST /orders

```



Example request:



```json

{

&#x20; "customer\_name": "Mabasa Technologies",

&#x20; "customer\_email": "customer@example.com",

&#x20; "items": \[

&#x20;   {

&#x20;     "product": "Cloud Service",

&#x20;     "quantity": 1,

&#x20;     "price": 250

&#x20;   }

&#x20; ]

}

```



API Gateway validates the request and invokes the Create Order Lambda function.



### 3. Order Queuing



The Create Order Lambda function:



1\. Validates the order.

2\. Generates a unique order ID.

3\. Calculates the order total.

4\. Adds a creation timestamp.

5\. Sets the initial status to `QUEUED`.

6\. Sends the order to Amazon SQS.



Example response:



```json

{

&#x20; "message": "Order accepted for processing",

&#x20; "order\_id": "ORD-XXXXXXXX",

&#x20; "status": "QUEUED"

}

```



The API returns HTTP status `202 Accepted`, allowing order processing to continue asynchronously.



### 4. Asynchronous Processing



Amazon SQS triggers the Process Order Lambda function.



The processing function:



1\. Reads the SQS message.

2\. Parses the order payload.

3\. Validates the order ID.

4\. Changes the status to `COMPLETED`.

5\. Adds a processing timestamp.

6\. Stores the completed order in DynamoDB.



This architecture separates API request handling from backend processing, improving scalability and resilience.



## Failure Handling



The application uses an Amazon SQS dead-letter queue:



```text

serverless-order-dlq

```



The main order queue uses:



```text

maxReceiveCount = 3

VisibilityTimeout = 60 seconds

```



If Lambda repeatedly fails to process a message, Amazon SQS automatically moves it to the dead-letter queue instead of retrying indefinitely.



### DLQ Validation



Failure handling was tested by deliberately sending an invalid message directly to the primary SQS queue.



The Process Order Lambda failed as expected, producing a JSON parsing error.



SQS automatically retried the message before moving it to the dead-letter queue.



The controlled test confirmed:



\* Lambda processing failure detection

\* Automatic SQS retries

\* Dead-letter queue redrive

\* Preservation of the original message

\* Preservation of source-queue metadata

\* Failed-message inspection

\* Safe DLQ cleanup



The DLQ message identified its source as:



```text

serverless-order-queue

```



The controlled test message reached an `ApproximateReceiveCount` of 4 before inspection in the DLQ.



After testing and cleanup, both the primary queue and dead-letter queue returned to zero messages.



## Security



The project implements multiple security controls.



### Cognito Authentication



Amazon Cognito protects the REST API.



Requests without valid authentication are rejected before the Create Order Lambda is invoked.



### Optional MFA



Software-token TOTP MFA is enabled in the Cognito User Pool.



MFA is optional, allowing users to enroll an authenticator application without making MFA mandatory for every user.



### API Throttling



API Gateway uses throttling limits of:



```text

Rate limit: 10 requests per second

Burst limit: 20 requests

```



This helps protect the API against excessive traffic.



### SQS Encryption



Both the primary order queue and dead-letter queue use Amazon SQS server-side encryption.



### DynamoDB Protection



The DynamoDB table uses:



\* Server-side encryption

\* Point-in-Time Recovery (PITR)

\* On-demand billing



Point-in-Time Recovery provides additional protection against accidental writes or deletions.



### IAM Least Privilege



The Lambda functions use separate IAM roles.



The Create Order Lambda is granted permission to send messages to the required SQS queue.



The Process Order Lambda is granted permission to write orders to the required DynamoDB table.



Application permissions are scoped to the required resources rather than granting broad access.



## Request Validation



API Gateway performs request validation before invoking the Create Order Lambda.



Application-level validation is also performed inside Lambda.



The two validation layers help prevent malformed orders from entering the processing pipeline.



Required fields include:



\* `customer\_name`

\* `customer\_email`

\* `items`



Lambda also validates individual order items, quantities, and prices.



## API Access Logging



API Gateway access logs are written to:



```text

/aws/apigateway/serverless-order-api

```



The access logs capture information including:



\* Request ID

\* Source IP

\* Request time

\* HTTP method

\* Resource path

\* HTTP status

\* Response length

\* Response latency

\* Integration latency

\* Integration errors



API Gateway's regional account configuration also includes the required IAM role for publishing logs to CloudWatch.



## Monitoring and Alerting



Amazon CloudWatch monitors the application.



Seven CloudWatch alarms are configured:



1\. Create Order Lambda errors

2\. Process Order Lambda errors

3\. SQS queue backlog

4\. DLQ messages

5\. API Gateway 4XX errors

6\. API Gateway 5XX errors

7\. API Gateway high latency



Alarm notifications are delivered through Amazon SNS.



This provides visibility into application failures and abnormal conditions.



## CloudWatch Dashboard



The project includes a CloudFormation-managed CloudWatch dashboard:



```text

serverless-order-processing-dashboard

```



The dashboard displays:



\* API Gateway requests

\* API Gateway errors

\* API Gateway latency

\* Lambda invocations

\* Lambda errors

\* SQS queue depth

\* Dead-letter queue depth

\* DynamoDB activity



The dashboard is managed through Infrastructure as Code rather than being manually maintained.



## Infrastructure as Code



The AWS application infrastructure is defined in:



```text

template.yaml

```



AWS SAM and AWS CloudFormation are used to create and manage the application's resources.



Typical deployment workflow:



```powershell

sam validate --lint

sam build

sam deploy

```



For an initial deployment:



```powershell

sam deploy --guided

```



Using Infrastructure as Code makes the architecture repeatable, version-controlled, and easier to maintain.



## Testing



Automated tests are stored under:



```text

tests/

```



The project currently includes:



```text

test\_create\_order.py

test\_process\_order.py

```



Tests can be executed with:



```powershell

pytest

```



The application has also been tested end-to-end using the complete serverless workflow:



```text

Cognito Authentication

&#x20;       |

&#x20;       v

API Gateway

&#x20;       |

&#x20;       v

Create Order Lambda

&#x20;       |

&#x20;       v

Amazon SQS

&#x20;       |

&#x20;       v

Process Order Lambda

&#x20;       |

&#x20;       v

Amazon DynamoDB

```



A successful authenticated test confirmed that an order could be accepted, queued, processed, and stored in DynamoDB with:



```text

status = COMPLETED

```



The test also confirmed that the main SQS queue returned to zero messages after successful processing.



## Troubleshooting and Lessons Learned



Building the project involved resolving several real-world AWS and development issues.



### DynamoDB Float Types



DynamoDB does not support Python `float` values directly through boto3.



The Process Order Lambda was updated to deserialize JSON floating-point values as Python `Decimal` objects.



### Invalid SQS JSON



Malformed JSON messages produced `JSONDecodeError` exceptions.



This demonstrated the importance of validating message payloads and implementing a DLQ for messages that cannot be processed.



### PowerShell and AWS CLI JSON



PowerShell quoting caused issues when passing JSON directly to AWS CLI commands.



AWS CLI shorthand, PowerShell objects, and JSON files were used where appropriate to avoid escaping problems.



### API Gateway CloudWatch Logging



API Gateway access logging initially failed because an account-level CloudWatch Logs IAM role had not been configured.



The required IAM role was created and configured for API Gateway in the deployment region.



After configuring the role, API access logging deployed successfully.



### Cognito Configuration



Amazon Cognito was progressively hardened with:



\* Reduced token lifetime

\* User-existence protection

\* Verified email updates

\* Optional software-token MFA



### API Gateway Request Validation



API Gateway correctly rejects requests missing required properties.



Some JSON Schema constraints are not enforced in the same way by API Gateway model validation, so additional application-level validation remains inside Lambda.



This provides defence in depth.



### Infrastructure as Code



Some monitoring resources were initially created manually during development.



They were later deleted and recreated through AWS SAM so the application's monitoring infrastructure is managed through CloudFormation.



### SQS Retry and DLQ Testing



A controlled invalid message was used to verify the failure path.



The test demonstrated that SQS and Lambda automatically retry failed processing and eventually isolate the failed message in the DLQ.



This confirmed that the application's failure-handling architecture works in practice rather than existing only as configuration.



## Project Structure



```text

serverless-order-processing/

|

+-- backend/

|   |

|   +-- create\_order/

|   |   +-- app.py

|   |

|   +-- process\_order/

|       +-- app.py

|

+-- tests/

|   +-- test\_create\_order.py

|   +-- test\_process\_order.py

|

+-- docs/

|

+-- .gitignore

+-- README.md

+-- template.yaml

```



Local SAM build files, development backups, temporary test payloads, environment files, and application build artifacts are excluded through `.gitignore`.



## Skills Demonstrated



This project demonstrates practical experience with:



\* AWS serverless architecture

\* Event-driven architecture

\* AWS Lambda

\* Amazon API Gateway

\* Amazon SQS

\* Dead-letter queues

\* Amazon DynamoDB

\* Amazon Cognito

\* AWS IAM

\* Amazon CloudWatch

\* Amazon SNS

\* AWS SAM

\* AWS CloudFormation

\* Infrastructure as Code

\* REST APIs

\* Python

\* boto3

\* Authentication and authorization

\* Multi-factor authentication

\* API throttling

\* Encryption

\* Logging and monitoring

\* Failure handling

\* Cloud security

\* Troubleshooting

\* Automated testing



## Future Improvements



Planned enhancements include:



\* Windows desktop client

\* Cognito authentication from the desktop application

\* Order-history retrieval

\* CI/CD using GitHub Actions

\* Additional automated tests

\* Enhanced structured logging

\* AWS X-Ray distributed tracing



## Author



\*\*Musa Mabasa\*\*



AWS Cloud Engineer \& IT Professional



AWS Certified Cloud Practitioner

AWS Certified Solutions Architect - Associate




