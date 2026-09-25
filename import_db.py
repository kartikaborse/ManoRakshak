import os
import mysql.connector
from mysql.connector import Error

# Aiven MySQL Credentials
DB_CONFIG = {
    "host": "mysql-3eca9ec8-kartikaborse64-8afc.i.aivencloud.com",
    "port": 27138,
    "user": "avnadmin",
    "password": "",  # To be filled or read from input
    "database": "defaultdb",
}

def parse_sql(sql_text):
    statements = []
    current_stmt = []
    in_string = False
    string_char = None
    escaped = False
    
    for char in sql_text:
        if escaped:
            current_stmt.append(char)
            escaped = False
            continue
            
        if char == '\\':
            current_stmt.append(char)
            escaped = True
            continue
            
        if char in ("'", '"', '`'):
            if not in_string:
                in_string = True
                string_char = char
            elif string_char == char:
                in_string = False
                string_char = None
            current_stmt.append(char)
        elif char == ';' and not in_string:
            current_stmt.append(char)
            statements.append("".join(current_stmt).strip())
            current_stmt = []
        else:
            current_stmt.append(char)
            
    if current_stmt:
        stmt = "".join(current_stmt).strip()
        if stmt:
            statements.append(stmt)
            
    return statements

def clean_sql_text(sql_text):
    lines = sql_text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('--') or stripped.startswith('#') or not stripped:
            continue
        cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

def main():
    print("=== Aiven MySQL Database Importer ===")
    password = input("Enter Aiven MySQL Password: ").strip()
    if not password:
        print("Password cannot be empty!")
        return
        
    DB_CONFIG["password"] = password
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file_path = os.path.join(script_dir, "manorakshak_db.sql")
    if not os.path.exists(sql_file_path):
        print(f"Error: {sql_file_path} not found in the current directory.")
        return
        
    print(f"Reading {sql_file_path}...")
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_text = f.read()
        
    cleaned_sql = clean_sql_text(sql_text)
    statements = parse_sql(cleaned_sql)
    print(f"Parsed {len(statements)} SQL statements to execute.")
    
    print("Connecting to Aiven MySQL...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Connected successfully!")
        
        # We need to execute each statement
        for i, stmt in enumerate(statements, 1):
            if not stmt:
                continue
            # Aiven MySQL database is defaultdb. The SQL file might have:
            # CREATE DATABASE IF NOT EXISTS `manorakshak_db`;
            # USE `manorakshak_db`;
            # Aiven free tier MySQL only allows us to write to `defaultdb`. We should bypass or rewrite database switching.
            if stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE "):
                print(f"Skipping database creation/switch statement: {stmt[:50]}...")
                continue
                
            print(f"Executing statement {i}/{len(statements)}...")
            try:
                cursor.execute(stmt)
            except Error as err:
                print(f"Error executing statement {i}: {err}")
                print(f"Statement: {stmt[:200]}...")
                # We can choose to roll back or continue. Usually, we want to see errors.
                
        conn.commit()
        print("\nDatabase import completed successfully!")
        
    except Error as e:
        print(f"Database Connection Error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("Connection closed.")

if __name__ == "__main__":
    main()
