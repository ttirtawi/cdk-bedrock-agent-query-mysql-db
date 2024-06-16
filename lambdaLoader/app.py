import json
import os
from typing import List, Tuple
from datetime import date
from decimal import Decimal
from database_utils import get_db_connection, execute_query, executemany_query

def read_sql_file(file_path: str) -> str:
    print(f"file_path: {file_path}")
    with open(file_path, 'r') as f:
      return f.read()

def execute_sql_scripts(sql_dir, sql_scripts: List[Tuple[str, str]]) -> None:
  conn = None
  try:
    conn = get_db_connection()

    for file_name, description in sql_scripts:
      sql_script = read_sql_file(os.path.join(sql_dir, file_name))
      print(f"Will execute sql: {file_name}")
      result = execute_query(conn, sql_script)
      print(f"result: {result}")
      print(f"{description} successfully.")

  except Exception as e:
    print(f"Error: {e}")


def execute_sql_many_scripts(sql_dir, sql_scripts: List[Tuple[str, str, str]]) -> None:
  conn = None
  try:
    conn = get_db_connection()

    for sql_script_filename, sql_value_filename, description in sql_scripts:
      sql_script = read_sql_file(os.path.join(sql_dir, sql_script_filename))
      sql_values = read_sql_file(os.path.join(sql_dir, sql_value_filename))
      
      print(f"Will execute sql: {sql_script_filename}, with values from: {sql_value_filename}")
      
      result = executemany_query(conn, sql_script, sql_values)
      
      print(f"result: {result}")
      print(f"{description} successfully.")

  except Exception as e:
    print(f"Error: {e}")


def load_database():
  
  function_dir = os.path.dirname(os.path.realpath(__file__))
  sql_dir = os.path.join(function_dir, 'sql')
  
  print(f"function_dir: {function_dir}")
  print(f"sql_dir: {sql_dir}")

  # print all files inside sql_dir
  for file_name in os.listdir(sql_dir):
    print(f"file_name: {file_name}")

  # Create employees table
  execute_sql_scripts(sql_dir, [('employees.sql', 'Employees table created')])

  # Load data
  sql_scripts = [
      ('load_departments.sql', 'load_departments.dump', 'Departments table created'),
      ('load_employees.sql', 'load_employees.dump', 'Employees table loaded'),
      ('load_dept_emp.sql', 'load_dept_emp.dump', 'Employees department table updated'),
      ('load_dept_manager.sql', 'load_dept_manager.dump', 'Department manager updated'),
      ('load_titles.sql', 'load_titles.dump', 'Employee title updated'),
      ('load_salaries1.sql', 'load_salaries1.dump', 'Employee salary 1 updated'),
      ('load_salaries2.sql', 'load_salaries2.dump', 'Employee salary 2 updated'),
      ('load_salaries3.sql', 'load_salaries3.dump', 'Employee salary 3 updated'),
  ]
  execute_sql_many_scripts(sql_dir, sql_scripts)

def on_create(event):
  physical_id = 'TheOnlyCustomResource'
  load_database()
  return {'PhysicalResourceId': physical_id}

def on_update(event):
  print("No action on update")
def on_delete(event):
  print("No action on delete")

def lambda_handler(event, context):
  
  print(f"event: {event}")
  request_type = event['RequestType']
  if request_type == 'Create':
    return on_create(event)
  elif request_type == 'Update':
    return on_update(event)
  elif request_type == 'Delete':
    return on_delete(event)
  else:
    raise Exception("Invalid request type")