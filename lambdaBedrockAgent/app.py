import json
import os
from datetime import date
from decimal import Decimal
from database_utils import get_db_connection, execute_query, getSecret

# custom JSON encoder for handling date and Decimal objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return super().default(obj)

    
def lambda_handler(event, context):

    print(f"event: {event}")
    agent = event['agent']["name"]
    actionGroup = event['actionGroup']
    session_attributes = event['sessionAttributes']
    prompt_session_attributes = event['promptSessionAttributes']
    inputText = event['inputText']
    apiPath = event['apiPath']

    print(f"apiPath: {apiPath}")
    print(f"inputText: {inputText}")
    print(f"agent: {agent}")
    print(f"actionGroup: {actionGroup}  ")

    if apiPath == '/queryDB':
        request_body = event['requestBody']

        # Get the content from the request body
        content = request_body.get('content', {})

        # Get the application/json content
        json_content = content.get('application/json', {})

        # Get the list of properties
        properties = json_content.get('properties', [])

        # Iterate over the properties
        for param in properties:
            # Check if the parameter name is 'SQLINPUT'
            if param.get('name') == 'SQLINPUT':
                # Extract the parameter value and store it in the 'sqlinput' variable
                sqlinput = param.get('value')
                break
        else:
            # Handle the case where the 'SQLINPUT' parameter is not found
            sqlinput = None

        # Print the value of the 'sqlinput' variable
        print(f"SQLINPUT: {sqlinput}")
        
    else:
        response_code = 404
        result = {"error": f"Unrecognized api path: {actionGroup}::{apiPath}"}

    conn = get_db_connection()
    query = sqlinput
    results = execute_query(conn, query)
    print(f"results: {results}") 

    # Convert the results to a list of dictionaries
    serialized_results = []
    for result in results:
        serialized_row = {}
        for i, value in enumerate(result):
            serialized_row[f"column_{i+1}"] = value
        serialized_results.append(serialized_row)

    # Serialize the results to JSON using the custom encoder
    response_body = {
        'responseData': json.dumps(serialized_results, cls=CustomJSONEncoder)
    }

    response_code = 200
    print(f"response_body: {response_body}")


    response = {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": actionGroup,
            "apiPath": apiPath,
            "httpMethod": event.get('httpMethod'),
            "httpStatusCode": response_code,
            "responseBody": {
                "application/json": {
                    "body": response_body
                }
            }
        },
        "sessionAttributes": session_attributes,
        "promptSessionAttributes": prompt_session_attributes
    }


    print(f"action_response: {response}")

    return response

