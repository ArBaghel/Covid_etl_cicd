import json
import urllib.request
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    s3_bucket = os.environ.get("S3_SOURCE_BUCKET_NAME", "covid-etl-source-bucket")
    s3 = boto3.client('s3')
    
    # 1. Fetch data from API
    url = "https://data.incovid19.org/v4/min/data.min.json"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode())
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 2. Upload JSON file
    s3.put_object(
        Bucket=s3_bucket,
        Key=f"raw/covid_data_{timestamp}.json",
        Body=json.dumps(data, indent=4),
        ContentType="application/json"
    )
    
    # 3. Create and Upload CSV file
    csv_lines = ["state,total_cases,recovered,deaths,vaccination,population"]
    for state, state_data in data.items():
        total = state_data.get("total", {})
        meta = state_data.get("meta", {})
        line = f"{state},{total.get('confirmed', 0)},{total.get('recovered', 0)},{total.get('deceased', 0)},{total.get('vaccinated1', 0)},{meta.get('population', 0)}"
        csv_lines.append(line)
        
    s3.put_object(
        Bucket=s3_bucket,
        Key=f"raw/covid_data_{timestamp}.csv",
        Body="\n".join(csv_lines),
        ContentType="text/csv"
    )
    
    # 4. Create and Upload XML file
    xml_lines = ["<covid_records>"]
    for state, state_data in data.items():
        total = state_data.get("total", {})
        meta = state_data.get("meta", {})
        xml_lines.append("  <state_record>")
        xml_lines.append(f"    <state>{state}</state>")
        xml_lines.append(f"    <total_cases>{total.get('confirmed', 0)}</total_cases>")
        xml_lines.append(f"    <recovered>{total.get('recovered', 0)}</recovered>")
        xml_lines.append(f"    <deaths>{total.get('deceased', 0)}</deaths>")
        xml_lines.append(f"    <vaccination>{total.get('vaccinated1', 0)}</vaccination>")
        xml_lines.append(f"    <population>{meta.get('population', 0)}</population>")
        xml_lines.append("  </state_record>")
    xml_lines.append("</covid_records>")
    
    s3.put_object(
        Bucket=s3_bucket,
        Key=f"raw/covid_data_{timestamp}.xml",
        Body="\n".join(xml_lines),
        ContentType="application/xml"
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps("Data fetched and uploaded successfully!")
    }
