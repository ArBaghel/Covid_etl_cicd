# COVID-19 ETL CI/CD Pipeline (S3 → Unified Parser Lambda → DynamoDB & S3)

A serverless ETL (Extract, Transform, Load) pipeline that fetches daily COVID-19 datasets (supporting JSON, CSV, and XML formats), stores raw records in S3, triggers a unified Lambda parser to extract metrics for specific states (MP, UP, KL, AP), and loads the results into a DynamoDB table and an S3 output folder. The pipeline is tested via GitHub Actions CI and compiled/packaged via AWS CodeBuild.

---

## Architecture Overview

```mermaid
graph TD
    %% Input Layer
    subgraph Data Input
        EventBridge[EventBridge Cron Schedule] -->|1. Triggers fetch| Fetcher[Fetcher Lambda: lambda_fetch.py]
        Fetcher -->|2. Writes raw formats| S3Source[S3 Source Bucket]
    end

    %% Processing Layer
    subgraph ETL Processing Layer
        S3Source -->|3. S3 Event Notification| Parser[Processor Lambda: lambda_function.py]
        Parser -->|4. Detects extension & parses| Process[Extract metrics for: MP, UP, KL, AP]
    end

    %% Storage Layer
    subgraph Storage Layer
        Process -->|5a. Save JSON| S3Dest[S3 Output Bucket]
        Process -->|5b. Write Records| DynamoDB[(DynamoDB Table: covid_filtered_table)]
    end

    style EventBridge fill:#ECECFF,stroke:#9370DB,stroke-width:2px
    style Fetcher fill:#FF9900,stroke:#d87b00,stroke-width:2px,color:#fff
    style S3Source fill:#FF9900,stroke:#d87b00,stroke-width:2px,color:#fff
    style Parser fill:#FF9900,stroke:#d87b00,stroke-width:2px,color:#fff
    style Process fill:#00A88F,stroke:#007a68,stroke-width:2px,color:#fff
    style S3Dest fill:#FF9900,stroke:#d87b00,stroke-width:2px,color:#fff
    style DynamoDB fill:#527FFF,stroke:#3b5cb8,stroke-width:2px,color:#fff
```

---

## ETL Flow

```mermaid
graph TD
    Start([S3 Upload Event]) --> S3Read[Read S3 Bucket & Key]
    S3Read --> Inspect[Inspect File Extension]
    
    Inspect -->|If .json| ParseJSON[Parse Nested JSON Structure]
    Inspect -->|If .csv| ParseCSV[Parse CSV Rows via csv.DictReader]
    Inspect -->|If .xml| ParseXML[Parse XML Elements via ElementTree]
    
    ParseJSON --> Transform[Filter Target States: MP, UP, KL, AP]
    ParseCSV --> Transform
    ParseXML --> Transform
    
    Transform --> Calculate[Calculate non_vaccination = population - vaccination]
    Calculate --> LoadS3[Load: Upload Clean JSON to Output S3 Bucket]
    Calculate --> LoadDB[Load: Insert State Records to DynamoDB Table]

    style Start fill:#ECECFF,stroke:#9370DB,stroke-width:2px
    style Inspect fill:#00A88F,stroke:#007a68,stroke-width:2px,color:#fff
    style LoadS3 fill:#FF9900,stroke:#d87b00,stroke-width:2px,color:#fff
    style LoadDB fill:#527FFF,stroke:#3b5cb8,stroke-width:2px,color:#fff
```

---

## Derived Metrics Calculation

| Output Key | Source Field (JSON / CSV / XML) | Calculation / Logic |
|---|---|---|
| `total_cases` | `confirmed` / `total_cases` | Directly parsed integer |
| `recovered` | `recovered` | Directly parsed integer |
| `deaths` | `deceased` / `deaths` | Directly parsed integer |
| `vaccination` | `vaccinated1` / `vaccination` | First-dose vaccination count |
| `non_vaccination` | `population` and `vaccination` | `population - vaccination` (unvaccinated count) |

---

## CI/CD Pipeline

```
Developer pushes code changes to GitHub
                 │
                 ├───────────────────────────────┐
                 ▼                               ▼
     ┌───────────────────────┐       ┌───────────────────────┐
     │  GitHub Actions (CI)  │       │   AWS CodeBuild (CD)  │
     │  .github/workflows/   │       │   buildspec.yml       │
     │  cicd.yml             │       │                       │
     │                       │       │  • Install Python 3.11│
     │  • Setup Python 3.11  │       │  • Install pip deps   │
     │  • Install pip deps   │       │  • Compile-check all  │
     │  • Syntax check files │       │    Lambda scripts     │
     │    (py_compile check) │       │  • Zip individual     │
     │                       │       │    lambda packages    │
     │  ✅ Success on valid  │       │                       │
     │  ❌ Fail on syntax    │       │  📦 Outputs:          │
     │     errors            │       │     - fetch.zip       │
     │                       │       │     - function.zip    │
     └───────────────────────┘       └───────────────────────┘
```

---

## Dataset & Targets

* **Primary Dataset Source:** [inCOVID19 India COVID-19 API](https://data.incovid19.org/)
* **Monitored States by Format:**
  * **JSON**: Assam (`AS`), Nagaland (`NL`), Meghalaya (`ML`), Arunachal Pradesh (`AR`)
  * **XML**: Delhi (`DL`), Haryana (`HR`), Uttarakhand (`UT`), Punjab (`PB`)
  * **CSV**: Madhya Pradesh (`MP`), Uttar Pradesh (`UP`), Andhra Pradesh (`AP`), Kerala (`KL`), Rajasthan (`RJ`), Himachal Pradesh (`HP`), West Bengal (`WB`)

---

## AWS Services Used

| Service | Role |
|---|---|
| **Amazon S3** | Data Lake — stores source uploads (`.json`, `.csv`, `.xml`) |
| **AWS Lambda** | ETL Engines — 1 Fetcher Lambda + 1 Unified Processor Lambda |
| **Amazon DynamoDB** | Clean Record Store — stores final processed states data |
| **AWS IAM** | Execution roles giving Lambda permissions to S3 and DynamoDB |
| **AWS CodeBuild** | Runs compilation validation and packages individual Lambda zip files |
| **GitHub Actions** | Automated CI pipeline checking syntax errors on push/pull requests |

---

## DynamoDB Table Design

* **Table name:** `covid_filtered_table`
* **Partition key:** `state` (String)
* **Capacity mode:** On-demand

```
state (PK) │ total_cases │ recovered │ deaths │ vaccination │ non_vaccination
───────────┼─────────────┼───────────┼────────┼─────────────┼────────────────
MP         │ 1054938     │ 1044140   │ 10786  │ 54378190    │ 18241902
UP         │ 2128103     │ 2102602   │ 23620  │ 154210982   │ 83610920
```

---

## Repository Structure

```
etl-s3-lambda-unified-parser/
├── README.md                      # Detailed System Documentation
├── lambda_function.py             # Unified Processor Lambda (processes JSON, CSV, and XML)
├── lambda_fetch.py                # Fetcher Lambda (fetches COVID API -> uploads JSON/CSV/XML to S3)
├── requirements.txt               # Main python dependency file (boto3)
├── buildspec.yml                  # CodeBuild instructions to package Lambda ZIPs
└── .github/
    └── workflows/
        └── cicd.yml               # GitHub Actions: syntax verification on push/PR
```

---

## Setup & Testing Steps

### 1. S3 Buckets Setup
Create two S3 buckets in your AWS account:
* `covid-etl-source-bucket` (for raw data input)
* `covid-etl-output-bucket` (for clean output storage)

### 2. DynamoDB Table Setup
Create a DynamoDB table named `covid_filtered_table` with `state` as the Partition key (String).

### 3. Deploy Lambda Functions
1. Create two Lambda functions in the AWS Console (Python 3.11).
2. Upload the zipped code generated by your CodeBuild/pipeline or insert the raw code files:
   * **Fetcher Lambda**: `lambda_fetch.py`
   * **Processor Lambda**: `lambda_function.py`
3. Configure environment variables:
   * For the **Fetcher Lambda**: Set `S3_SOURCE_BUCKET_NAME` = Name of your S3 source bucket.
   * For the **Processor Lambda**: Set `OUTPUT_BUCKET_NAME` = Name of your output bucket, and `DYNAMODB_TABLE_NAME` = `covid_filtered_table`.
4. Configure permissions (IAM execution roles):
   * **Fetcher Lambda**: Needs S3 Write (`s3:PutObject`) permissions.
   * **Processor Lambda**: Needs S3 Read/Write (`s3:GetObject`, `s3:PutObject`) and DynamoDB Write (`dynamodb:PutItem`) permissions.

### 4. Create S3 event Notification
1. Open the source S3 bucket properties.
2. Under **Event notifications**, add a trigger on `All object create events` (`s3:ObjectCreated:*`).
3. Set the destination to the Processor Lambda function (`covid-parser-lambda`).

### 5. Set up EventBridge Schedule (Automated Trigger)
To fetch daily data automatically:
1. Open the **Amazon EventBridge Console**.
2. Click **Create rule** and choose schedule (e.g. `rate(1 day)` or cron expression).
3. Set the target to invoke the `covid-fetcher-lambda` function.

### 6. Push Code & Trigger
* Push code to GitHub to verify CI/CD pipelines run cleanly.
* Trigger the `covid-fetcher-lambda` manually (or wait for the schedule) to fetch, convert, and push raw files to S3, which automatically triggers the Processor Lambda and completes the ETL workflow.

---

## Reflection

**Why DynamoDB?**  
No servers to configure, scales instantly, and on-demand mode matches the intermittent execution pattern of file uploads (you pay $0 when no files are uploaded).

**Why partition key `state`?**  
Since we only filter and track specific states (`MP`, `UP`, `KL`, `AP`), the state code provides an ideal partition key that guarantees fast key-value retrieval for state summaries.

**What files should never be committed to GitHub?**  
`.env` files (confidential configuration), `*.zip` build artifacts (compilable from source), local virtual environments (`venv/`), and raw data mock logs (to prevent repo bloat).
