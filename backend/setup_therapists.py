import mysql.connector

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",
    "database": "manokart_db",
}

def setup():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # 1. Create therapists table
    print("Creating therapists table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS therapists (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        title VARCHAR(200) NOT NULL,
        specialization VARCHAR(300) NOT NULL,
        experience INT NOT NULL,
        rating FLOAT NOT NULL,
        fees INT NOT NULL,
        location VARCHAR(200) NOT NULL,
        availability VARCHAR(200) NOT NULL,
        contact_email VARCHAR(150) NOT NULL,
        contact_phone VARCHAR(50) NOT NULL,
        photo_url VARCHAR(300) NOT NULL,
        bio TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Create appointments table
    print("Creating appointments table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        therapist_id INT NOT NULL,
        appointment_date DATE NOT NULL,
        appointment_time VARCHAR(50) NOT NULL,
        status VARCHAR(50) DEFAULT 'Pending',
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (therapist_id) REFERENCES therapists(id) ON DELETE CASCADE
    )
    """)
    
    # 3. Check if therapists has records, if not insert mock data
    cur.execute("SELECT COUNT(*) FROM therapists")
    count = cur.fetchone()[0]
    if count == 0:
        print("Inserting mock therapist profiles...")
        mock_therapists = [
            (
                "Dr. Aarav Mehta",
                "Consultant Psychiatrist",
                "Depression, Bipolar Disorder, Mood Swings, Medication Management",
                12,
                4.8,
                1500,
                "Mumbai (Online / In-Person)",
                "Mon-Wed, 10:00 AM - 4:00 PM",
                "aarav.mehta@manokart.com",
                "+91 98765 43210",
                "/static/avatars/therapist_aarav.png",
                "Dr. Aarav Mehta is a highly experienced psychiatrist specializing in mood disorders and medication-assisted therapy, focusing on a holistic recovery path."
            ),
            (
                "Ms. Ananya Sen",
                "Clinical Psychologist & CBT Specialist",
                "Anxiety, OCD, Stress Management, Cognitive Behavioral Therapy (CBT)",
                8,
                4.9,
                1200,
                "Delhi (Online)",
                "Tue-Fri, 9:00 AM - 5:00 PM",
                "ananya.sen@manokart.com",
                "+91 98765 43211",
                "/static/avatars/therapist_ananya.png",
                "Ananya Sen specializes in CBT and mindfulness-based therapies to help clients navigate anxiety, panic attacks, and daily stress management."
            ),
            (
                "Dr. Rohan Deshmukh",
                "Child & Adolescent Psychiatrist",
                "ADHD, Teen Anxiety, Family Counseling, Behavioral Issues",
                15,
                4.7,
                1800,
                "Pune (Online / In-Person)",
                "Mon-Thu, 2:00 PM - 7:00 PM",
                "rohan.deshmukh@manokart.com",
                "+91 98765 43212",
                "/static/avatars/therapist_rohan.png",
                "Dr. Rohan has extensive experience working with children, teenagers, and families to address developmental, behavioral, and academic challenges."
            ),
            (
                "Ms. Meera Nair",
                "Trauma-Informed Counseling Psychologist",
                "Trauma Recovery, Grief Counseling, Self-Esteem, Relationship Advice",
                6,
                4.9,
                1000,
                "Bengaluru (Online)",
                "Wed-Sat, 11:00 AM - 6:00 PM",
                "meera.nair@manokart.com",
                "+91 98765 43213",
                "/static/avatars/therapist_meera.png",
                "Meera Nair is dedicated to providing a safe, non-judgmental space for clients recovering from trauma, grief, or navigating difficult relationship transitions."
            ),
            (
                "Dr. Shalini Kapoor",
                "Neuropsychiatrist",
                "Sleep Disorders, ADHD, Chronic Stress, Cognitive Rehabilitation",
                10,
                4.8,
                1600,
                "Hyderabad (Online / In-Person)",
                "Mon-Fri, 10:00 AM - 1:00 PM",
                "shalini.kapoor@manokart.com",
                "+91 98765 43214",
                "/static/avatars/therapist_shalini.png",
                "Dr. Shalini Kapoor focuses on the intersection of neurological health and psychiatric well-being, helping clients with sleep, attention, and chronic stress issues."
            )
        ]
        
        insert_query = """
        INSERT INTO therapists (name, title, specialization, experience, rating, fees, location, availability, contact_email, contact_phone, photo_url, bio)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.executemany(insert_query, mock_therapists)
        conn.commit()
        print("Mock profiles successfully inserted!")
    else:
        print(f"Therapists table already contains {count} profiles. Skipping mock data insertion.")

    cur.close()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    setup()
