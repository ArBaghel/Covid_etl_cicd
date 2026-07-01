import json
import boto3
import os
import csv
import xml.etree.ElementTree as ET

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# State code definitions by format
JSON_TARGETS = {"AS", "NL", "ML", "AR"}                       # Assam, Nagaland, Meghalaya, Arunachal Pradesh
XML_TARGETS = {"DL", "HR", "UT", "PB"}                        # Delhi, Haryana, Uttarakhand, Punjab
CSV_TARGETS = {"MP", "UP", "AP", "KL", "RJ", "HP", "WB"}      # Madhya Pradesh, Uttar Pradesh, Andhra Pradesh, Kerala, Rajasthan, Himachal Pradesh, West Bengal

def lambda_handler(event, context):
    # Triggered by S3 Event
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]
    
    file_extension = key.split('.')[-1].lower()
    
    # 1. Fetch raw data file from S3
    response = s3_client.get_object(Bucket=bucket, Key=key)
    raw_data = response['Body'].read().decode('utf-8')
    
    filtered_data = {}
    
    # 2. Parse file content based on extension and apply dynamic state filtering
    if file_extension == "json":
        data = json.loads(raw_data)
        for state in JSON_TARGETS:
            if state in data:
                state_data = data[state]
                vaccinated = state_data["total"].get("vaccinated1", 0)
                filtered_data[state] = {
                    "state": state,
                    "total_cases": state_data["total"].get("confirmed", 0),
                    "recovered": state_data["total"].get("recovered", 0),
                    "deaths": state_data["total"].get("deceased", 0),
                    "vaccination": vaccinated,
                    "non_vaccination": state_data["meta"].get("population", 0) - vaccinated
                }
                
    elif file_extension == "csv":
        reader = csv.DictReader(raw_data.splitlines())
        for row in reader:
            state = row.get("state", "").upper()
            if state in CSV_TARGETS:
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
                
    elif file_extension == "xml":
        root = ET.fromstring(raw_data)
        for state_node in root.findall('state_record'):
            state = state_node.find('state').text.upper()
            if state in XML_TARGETS:
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
    else:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Unsupported file type: {file_extension}")
        }
        
    
    # 3. Save records to the DynamoDB Table
    db_table = os.environ.get("DYNAMODB_TABLE_NAME", "covid_filtered_table")
    table = dynamodb.Table(db_table)
    for state, state_metrics in filtered_data.items():
        table.put_item(Item=state_metrics)
        
    return {
        'statusCode': 200,
        'body': json.dumps("Data processed and uploaded successfully!")
    }
