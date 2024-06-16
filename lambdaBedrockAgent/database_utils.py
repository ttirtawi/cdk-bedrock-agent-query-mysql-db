import os
import mysql.connector
import boto3
import json
from botocore.exceptions import ClientError

# populate secret manager
def getSecret(secretName):
    client = boto3.client('secretsmanager')
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secretName)
        print(f"get_secret_value_response: {get_secret_value_response}")
        password = json.loads(get_secret_value_response['SecretString'])["password"]
        return password
    # finish the catch
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            raise e


def get_db_connection():

    db_host = os.environ.get('db_host', 'localhost')    
    db_port = os.environ.get('db_port', '5432')
    db_name = os.environ.get('db_name', 'mydb')
    db_user = os.environ.get('db_user', 'myuser')
    db_password_secret = os.environ.get('db_password_secret', 'secretname')
    db_password = getSecret(db_password_secret)

    connection = mysql.connector.connect(
        host=db_host,
        port=db_port, 
        database=db_name,
        user=db_user,
        password=db_password
    )
    return connection

def execute_query(connection, query):
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    return results

