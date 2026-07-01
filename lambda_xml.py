import json
import boto3
import os
import xml.etree.ElementTree as ET

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

TARGET_STATES = ["MP", "UP", "KL", "AP"]

def lambda_handler(event, context):
    bucket = event["bucket"]
    key = event["key"]
    
    # Fetch XML file from S3
    response = s3_client.get_object(Bucket=bucket, Key=key)
    raw_data = response['Body'].read().decode('utf-8')
    
    # Parse XML structure
    root = ET.fromstring(raw_data)
    filtered_data = {}
    
    for state_node in root.findall('state_record'):
        state = state_node.find('state').text.upper()
        if state in TARGET_STATES:
            population = int(state_node.find('population').text)
            vaccinated = int(state_node.find('vaccination').text)
            
            filtered_data[state] = {
                "state": state,
                "total_cases": int(state_node.find('total_cases').text),
                "recovered": int(state_node.find('recovered').text),
                "deaths": int(state_node.find('deaths').text),
                "vaccination": vaccinated,
                "non_vaccination": population - vaccinated
            }
            
    # Push processed results to Output S3 Bucket
    output_bucket = os.environ.get("OUTPUT_BUCKET_NAME", "my-covid-output-bucket")
    s3_client.put_object(
        Bucket=output_bucket,
        Key=f"processed_xml_{key.split('/')[-1]}",
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
        'body': json.dumps({"message": "XML data parsed and pushed successfully"})
    }
