import mysql.connector

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",
    "database": "manorakshat_db",
}

def migrate():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("Creating assessments table...")
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS assessments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        type VARCHAR(20) NOT NULL,
        score INT NOT NULL,
        severity VARCHAR(50) NOT NULL,
        answers TEXT NOT NULL,
        taken_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_assessment_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    try:
        cur.execute(create_table_sql)
        conn.commit()
        print("-> 'assessments' table created successfully.")
    except mysql.connector.Error as err:
        print(f"Error creating assessments table: {err}")
        raise err

    cur.close()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
