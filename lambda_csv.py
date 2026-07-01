import json
import boto3
import os
import csv

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

TARGET_STATES = ["MP", "UP", "KL", "AP"]

def lambda_handler(event, context):
    bucket = event["bucket"]
    key = event["key"]
    
    # Fetch CSV file from S3
    response = s3_client.get_object(Bucket=bucket, Key=key)
    raw_data = response['Body'].read().decode('utf-8').splitlines()
    
    # Parse CSV lines
    reader = csv.DictReader(raw_data)
    filtered_data = {}
    
    for row in reader:
        state = row.get("state", "").upper()
        if state in TARGET_STATES:
            population = int(row.get("population", 0))
            vaccinated = int(row.get("vaccination", 0))
            
            filtered_data[state] = {
                "state": state,
                "total_cases": int(row.get("total_cases", 0)),
                "recovered": int(row.get("recovered", 0)),
                "deaths": int(row.get("deaths", 0)),
                "vaccination": vaccinated,
                "non_vaccination": population - vaccinated
            }
            
    # Push processed results to Output S3 Bucket
    output_bucket = os.environ.get("OUTPUT_BUCKET_NAME", "my-covid-output-bucket")
    s3_client.put_object(
        Bucket=output_bucket,
        Key=f"processed_csv_{key.split('/')[-1]}",
        Body=json.dumps(filtered_data, indent=4),
        ContentType="application/json"
    )
    
    # Push processed results to DynamoDB
    db_table = os.environ.get("DYNAMODB_TABLE_NAME", "covid_filtered_table")
    table = dynamodb.Table(db_table)
    for state, state_metrics in filtered_data.items():
        table.put_item(Item=state_metrics)
        
    return {
        'statusCode': 200,
        'body': json.dumps({"message": "CSV data parsed and pushed successfully"})
    }
