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
    
    print("Migrating database to Version 2...")

    # 1. Create victim_profiles table
    print("Creating victim_profiles table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS victim_profiles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        case_number VARCHAR(100) NOT NULL UNIQUE,
        category VARCHAR(150) NOT NULL,
        judicial_stage VARCHAR(100) DEFAULT 'Investigation',
        counselor_id INT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (counselor_id) REFERENCES therapists(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """)
    conn.commit()
    print("-> Table victim_profiles created or verified.")

    # 2. Create victim_distress_scores table
    print("Creating victim_distress_scores table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS victim_distress_scores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        score FLOAT NOT NULL,
        sentiment_score FLOAT DEFAULT NULL,
        vocal_stress FLOAT DEFAULT NULL,
        assessment_score INT DEFAULT NULL,
        details_json TEXT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """)
    conn.commit()
    print("-> Table victim_distress_scores created or verified.")

    # 3. Create victim_alerts table
    print("Creating victim_alerts table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS victim_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        score FLOAT NOT NULL,
        reason TEXT NOT NULL,
        status VARCHAR(50) DEFAULT 'Active',
        resolution_notes TEXT DEFAULT NULL,
        resolved_by INT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        resolved_at DATETIME NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """)
    conn.commit()
    print("-> Table victim_alerts created or verified.")

    # 4. Create victim_vault_incidents table
    print("Creating victim_vault_incidents table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS victim_vault_incidents (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        incident_type VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        evidence_file_path VARCHAR(255) DEFAULT NULL,
        threat_severity VARCHAR(20) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """)
    conn.commit()
    print("-> Table victim_vault_incidents created or verified.")

    # 5. Create victim_sos_alerts table
    print("Creating victim_sos_alerts table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS victim_sos_alerts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        latitude VARCHAR(50) NOT NULL,
        longitude VARCHAR(50) NOT NULL,
        status VARCHAR(50) DEFAULT 'Active',
        dispatched_officer VARCHAR(150) DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """)
    conn.commit()
    print("-> Table victim_sos_alerts created or verified.")

    # 6. Create victim_compensation_claims table
    print("Creating victim_compensation_claims table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS victim_compensation_claims (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        case_number VARCHAR(100) NOT NULL,
        amount_entitled FLOAT NOT NULL,
        stage VARCHAR(100) NOT NULL,
        status VARCHAR(50) DEFAULT 'Pending Officer Review',
        petition_text TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    """)
    conn.commit()
    print("-> Table victim_compensation_claims created or verified.")

    cur.close()
    conn.close()
    print("Version 2 Database Migration Complete!")

if __name__ == "__main__":
    migrate()
