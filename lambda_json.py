import json
import boto3
import os

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

TARGET_STATES = ["MP", "UP", "KL", "AP"]

def lambda_handler(event, context):
    bucket = event["bucket"]
    key = event["key"]
    
    # Fetch JSON file from S3
    response = s3_client.get_object(Bucket=bucket, Key=key)
    raw_data = response['Body'].read().decode('utf-8')
    data = json.loads(raw_data)
    
    filtered_data = {}
    for state in TARGET_STATES:
        if state in data:
            state_data = data[state]
            cases = state_data["total"]["confirmed"]
            recovered = state_data["total"]["recovered"]
            deaths = state_data["total"]["deceased"]
            vaccinated = state_data["total"]["vaccinated1"]
            non_vaccinated = state_data["meta"]["population"] - vaccinated
            
            filtered_data[state] = {
                "state": state,
                "total_cases": cases,
                "recovered": recovered,
                "deaths": deaths,
                "vaccination": vaccinated,
                "non_vaccination": non_vaccinated
            }
            
    # Push processed results to Output S3 Bucket
    output_bucket = os.environ.get("OUTPUT_BUCKET_NAME", "my-covid-output-bucket")
    s3_client.put_object(
        Bucket=output_bucket,
        Key=f"processed_json_{key.split('/')[-1]}",
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
        'body': json.dumps({"message": "JSON data parsed and pushed successfully"})
    }
