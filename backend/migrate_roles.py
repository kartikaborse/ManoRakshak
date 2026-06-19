import mysql.connector

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",
    "database": "manokart_db",
}

def migrate():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 1. Add role column to users
    print("Migrating users table...")
    try:
        cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'")
        conn.commit()
        print("-> Added 'role' column successfully.")
    except mysql.connector.Error as err:
        if err.errno == 1060: # Column already exists
            print("-> 'role' column already exists.")
        else:
            raise err
            
    # 2. Add user_id column to therapists
    print("Migrating therapists table...")
    try:
        cur.execute("ALTER TABLE therapists ADD COLUMN user_id INT NULL")
        conn.commit()
        print("-> Added 'user_id' column successfully.")
    except mysql.connector.Error as err:
        if err.errno == 1060:
            print("-> 'user_id' column already exists.")
        else:
            raise err

    # 3. Add foreign key constraint
    try:
        cur.execute("ALTER TABLE therapists ADD CONSTRAINT fk_therapist_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL")
        conn.commit()
        print("-> Added foreign key constraint fk_therapist_user successfully.")
    except mysql.connector.Error as err:
        if err.errno == 1061 or err.errno == 1205 or err.errno == 1826: # Duplicate key name or constraint already exists
            print("-> Foreign key constraint already exists.")
        else:
            print(f"-> FK Warning: {err}")

    cur.close()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
