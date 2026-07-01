import json
import boto3

def lambda_handler(event, context):
    # Main router triggered by S3 Event
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]
    
    # Determine file type based on extension
    file_extension = key.split('.')[-1].lower()
    
    # Select target Lambda function name
    target_lambda = f"covid-parser-{file_extension}-lambda"
    
    # Invoke the target Lambda function asynchronously
    lambda_client = boto3.client('lambda')
    payload = {"bucket": bucket, "key": key}
    
    lambda_client.invoke(
        FunctionName=target_lambda,
        InvocationType='Event', # Asynchronous execution
        Payload=json.dumps(payload)
    )
    
    return {
        'statusCode': 202,
        'body': json.dumps({"message": f"Successfully routed task to {target_lambda}"})
    }
