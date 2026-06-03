import sqlite3

DATABASE = 'erp_database.db'

def initialize_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    print("Initializing cryptographic academic registry database...")

    # 1. Drop existing tables if they exist to prevent schema conflicts
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS students")
    cursor.execute("DROP TABLE IF EXISTS performance")
    cursor.execute("DROP TABLE IF EXISTS leave_requests")
    cursor.execute("DROP TABLE IF EXISTS anti_ragging_reports")

    # 2. Create Core Users Table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            ref_id INTEGER DEFAULT NULL
        )
    ''')

    # 3. Create Students Directory Table
    cursor.execute('''
        CREATE TABLE students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT UNIQUE NOT NULL,
            usn TEXT UNIQUE DEFAULT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            academic_fee REAL NOT NULL
        )
    ''')

    # 4. Create Performance Table
    cursor.execute('''
        CREATE TABLE performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            test1 REAL DEFAULT 0.0,
            test2 REAL DEFAULT 0.0,
            test3 REAL DEFAULT 0.0,
            lab_internals REAL DEFAULT 0.0,
            externals REAL DEFAULT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    ''')

    # 5. Create Leave Requests Table
    cursor.execute('''
        CREATE TABLE leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 6. Create Anti-Ragging Secure Dispatch Table
    cursor.execute('''
        CREATE TABLE anti_ragging_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_details TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    print("Tables drafted successfully. Injecting initial workspace records...")

    # 7. Seed Administrator Credentials
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                   ('admin', 'admin123', 'admin'))

    # 8. Seed Faculty Credentials
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                   ('teacher', 'teacher123', 'teacher'))

    # 9. Seed Sample Students with Clean Conditional Processing
    sample_students = [
        ('2026-R-1001', '1KC22CS001', 'Harry Potter', 'harry@hogwarts.edu', 85000.0, 'harry', 'gryffindor'),
        ('2026-R-1002', '1KC22CS002', 'Hermione Granger', 'hermione@hogwarts.edu', 85000.0, 'hermione', 'brightestwitch'),
        ('2026-R-1003', '1KC22CS003', 'Ron Weasley', 'ron@hogwarts.edu', 45000.0, 'ron', 'maroon')
    ]

    for roll, usn, name, email, fee, uname, passwd in sample_students:
        # Insert student demographic profile
        cursor.execute('''
            INSERT INTO students (roll_number, usn, name, email, academic_fee)
            VALUES (?, ?, ?, ?, ?)
        ''', (roll, usn, name, email, fee))
        
        student_id = cursor.lastrowid
        
        # Clean fixed separation: evaluate conditions in pure Python before executing SQL
        if name == 'Hermione Granger':
            cursor.execute('''
                INSERT INTO performance (student_id, test1, test2, test3, lab_internals, externals)
                VALUES (?, 48.0, 49.0, 50.0, 49.5, 98.0)
            ''', (student_id,))
        else:
            cursor.execute('''
                INSERT INTO performance (student_id, test1, test2, test3, lab_internals, externals)
                VALUES (?, 28.5, 31.0, 34.5, 38.0, NULL)
            ''', (student_id,))
        
        # Create student secure login terminal mapping
        cursor.execute('''
            INSERT INTO users (username, password, role, ref_id)
            VALUES (?, ?, ?, ?)
        ''', (uname, passwd, 'student', student_id))

    conn.commit()
    conn.close()
    print("Database environment completely provisioned! You can now run app.py.")

if __name__ == '__main__':
    initialize_database()