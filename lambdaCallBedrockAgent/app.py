import boto3
import json
from botocore.exceptions import ClientError
import uuid
import os

REGION_NAME = os.environ.get('region_name')
AGENT_ID = os.environ.get('agent_id')
AGENT_ALIAS_ID = os.environ.get('agent_alias_id')

agent = boto3.client('bedrock-agent', region_name=REGION_NAME)
agentruntime = boto3.client('bedrock-agent-runtime', region_name=REGION_NAME)


def lambda_handler(event, context):
    print(f"event: {event}")
    try:
        # generate unique session id using uuid
        sessionId = str(uuid.uuid4())
        # get prompt from rawQueryString and throw error if it is empty
        prompt = event.get('queryStringParameters', {}).get('prompt', '')
        if not prompt:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json; charset=utf-8'
                },
                'body': json.dumps({
                    "message": 'Invalid prompt'
                })
            }  
        try:
            # invoke agent
            response = agentruntime.invoke_agent(
                agentId=AGENT_ID,
                agentAliasId=AGENT_ALIAS_ID,
                inputText=prompt,
                sessionId=sessionId
            )
        except Exception as e:
            print(f"An error occurred: {e}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json; charset=utf-8'
                },
                'body': json.dumps({
                    "message": f"An error occurred: {e}"
                })
            }  

        event_stream = response['completion']
        final_answer = None
        try:
            for event in event_stream:
                if 'chunk' in event:
                    data = event['chunk']['bytes']
                    final_answer = data.decode('utf8')
                    print(f"Question ->\n{prompt}")
                    print(f"Final answer ->\n{final_answer}")
                    end_event_received = True

                elif 'trace' in event:
                    print(json.dumps(event['trace'], indent=2))
                else: 
                    print(f"An error occurred")
        except Exception as e:
            print(f"An error occurred: {e}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json; charset=utf-8'
                },
                'body': json.dumps({
                    "message": f"An error occurred: {e}"
                })
            }  

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8'
            },
            'body': final_answer
        }  
    except ClientError as e:
        print(f"An error occurred: {e}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8'
            },
            'body': json.dumps({
                "message": f"An error occurred: {e}"
            })
        }  
