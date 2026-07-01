import json
import urllib.request
import boto3
import os
from datetime import datetime

# Initialize S3 client
s3_client = boto3.client('s3')

# Source API URL
API_URL = "https://data.incovid19.org/v4/min/data.min.json"

# State list definitions by format
CSV_STATES = ["MP", "UP", "AP", "KL", "RJ", "HP", "WB"]     # Madhya Pradesh, Uttar Pradesh, Andhra Pradesh, Kerala, Rajasthan, Himachal Pradesh, West Bengal
XML_STATES = ["DL", "HR", "UT", "PB"]                       # Delhi, Haryana, Uttarakhand, Punjab

def lambda_handler(event, context):
    s3_bucket = os.environ.get("S3_SOURCE_BUCKET_NAME", "covid-etl-source-bucket")
    
    try:
        # 1. Fetch raw data from API
        url = "https://data.incovid19.org/v4/min/data.min.json"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode())
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 2. Upload full raw JSON (JSON parser filters AS, NL, ML, AR dynamically)
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=f"raw/covid_data_{timestamp}.json",
            Body=json.dumps(data, indent=4),
            ContentType="application/json"
        )
        
        # 3. Create and Upload CSV file (using MP, UP, AP, KL, RJ, HP, WB)
        csv_lines = ["state,total_cases,recovered,deaths,vaccination,population"]
        for state in CSV_STATES:
            if state in data:
                total = data[state].get("total", {})
                meta = data[state].get("meta", {})
                line = f"{state},{total.get('confirmed', 0)},{total.get('recovered', 0)},{total.get('deceased', 0)},{total.get('vaccinated1', 0)},{meta.get('population', 0)}"
                csv_lines.append(line)
            
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=f"raw/covid_data_{timestamp}.csv",
            Body="\n".join(csv_lines),
            ContentType="text/csv"
        )
        
        # 4. Create and Upload XML file (using DL, HR, UT, PB)
        xml_lines = ["<covid_records>"]
        for state in XML_STATES:
            if state in data:
                total = data[state].get("total", {})
                meta = data[state].get("meta", {})
                xml_lines.append("  <state_record>")
                xml_lines.append(f"    <state>{state}</state>")
                xml_lines.append(f"    <total_cases>{total.get('confirmed', 0)}</total_cases>")
                xml_lines.append(f"    <recovered>{total.get('recovered', 0)}</recovered>")
                xml_lines.append(f"    <deaths>{total.get('deceased', 0)}</deaths>")
                xml_lines.append(f"    <vaccination>{total.get('vaccinated1', 0)}</vaccination>")
                xml_lines.append(f"    <population>{meta.get('population', 0)}</population>")
                xml_lines.append("  </state_record>")
        xml_lines.append("</covid_records>")
        
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=f"raw/covid_data_{timestamp}.xml",
            Body="\n".join(xml_lines),
            ContentType="application/xml"
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps("Data fetched and uploaded successfully!")
        }
        
    except Exception as e:
        print(f"Error during execution: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)})
        }
