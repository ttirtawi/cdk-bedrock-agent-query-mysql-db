import os
import ast
import mysql.connector
import boto3
import json
from botocore.exceptions import ClientError

# populate secret manager
def getSecret(secretName):
    client = boto3.client('secretsmanager')
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secretName)
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
    db_port = os.environ.get('db_port', '3306')
    db_name = os.environ.get('db_name', 'mydb')
    db_user = os.environ.get('db_user', 'myuser')
    db_secret_name = os.environ.get('db_password_secret', 'secretname')
    db_password = getSecret(db_secret_name)

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
    connection.commit()
    results = cursor.fetchall()
    return results

def executemany_query(connection, script, values):
    cursor = connection.cursor()
    # covert strings `values` into a Python literal (tupple)
    try:
        values = ast.literal_eval(values)
        cursor.executemany(script,values)
        connection.commit()
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Error dodol: {e}")