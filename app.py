import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
import io
import base64
app = Flask(__name__)
app.secret_key = 'super_secret_erp_key'
DATABASE = 'erp_database.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'role' in session:
        return redirect(url_for('dashboard', role=session['role']))
    return render_template('index.html', view='login')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    role_selected = request.form['role']
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ? AND role = ?', 
                        (username, password, role_selected)).fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['ref_id'] = user['ref_id']
        flash(f"Session safely established. Welcome back, {username}!")
        return redirect(url_for('dashboard', role=user['role']))
    else:
        flash("Invalid Credentials or Identity Profile Mismatch.", "error")
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Successfully signed out of secure session.")
    return redirect(url_for('index'))

@app.route('/dashboard/<role>')
def dashboard(role):
    if 'role' not in session or session['role'] != role:
        flash("Access Denied!")
        return redirect(url_for('index'))

    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students ORDER BY name ASC').fetchall()
    reports = conn.execute('SELECT * FROM anti_ragging_reports ORDER BY timestamp DESC').fetchall()
    leaves = conn.execute('SELECT * FROM leave_requests ORDER BY id DESC').fetchall()
    teachers = conn.execute("SELECT * FROM users WHERE role = 'teacher'").fetchall()
    
    performance_records = conn.execute('''
        SELECT s.id, s.name, s.roll_number, s.usn, p.test1, p.test2, p.test3, p.lab_internals, p.externals 
        FROM students s 
        LEFT JOIN performance p ON s.id = p.student_id
    ''').fetchall()
    
    student_own_data = None
    student_own_perf = None

    if role == 'student' and session.get('ref_id'):
        student_own_data = conn.execute('SELECT * FROM students WHERE id = ?', (session['ref_id'],)).fetchone()
        student_own_perf = conn.execute('SELECT * FROM performance WHERE student_id = ?', (session['ref_id'],)).fetchone()

    conn.close()
    
    return render_template('index.html', role=role, view='dashboard', students=students, 
                           reports=reports, leaves=leaves, teachers=teachers,
                           performance=performance_records, student_data=student_own_data, 
                           student_perf=student_own_perf)

@app.route('/teacher/submit_marks/<int:student_id>', methods=['POST'])
def submit_marks(student_id):
    if session.get('role') != 'teacher': return redirect(url_for('index'))
    
    t1 = min(float(request.form['test1'] or 0), 50.0)
    t2 = min(float(request.form['test2'] or 0), 50.0)
    t3 = min(float(request.form['test3'] or 0), 50.0)
    lab = min(float(request.form['lab_internals'] or 0), 50.0)
    
    ext_input = request.form.get('externals', '').strip()
    ext = float(ext_input) if ext_input else None

    conn = get_db_connection()
    conn.execute('''
        UPDATE performance 
        SET test1=?, test2=?, test3=?, lab_internals=?, externals=? 
        WHERE student_id=?
    ''', (t1, t2, t3, lab, ext, student_id))
    conn.commit()
    conn.close()
    flash("Grades written successfully.")
    return redirect(url_for('dashboard', role='teacher'))

@app.route('/admin/register_student', methods=['POST'])
def register_student():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    name = request.form['name']
    email = request.form['email']
    academic_fee = float(request.form['academic_fee'])
    student_username = request.form['student_username']
    student_password = request.form['student_password']

    conn = get_db_connection()
    try:
        existing_count = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
        roll_number = f"2026-R-{1001 + existing_count}"

        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO students (roll_number, name, email, academic_fee)
            VALUES (?, ?, ?, ?)
        ''', (roll_number, name, email, academic_fee))
        student_id = cursor.lastrowid
        
        conn.execute('INSERT INTO performance (student_id) VALUES (?)', (student_id,))
        conn.execute('INSERT INTO users (username, password, role, ref_id) VALUES (?, ?, ?, ?)',
                     (student_username, student_password, 'student', student_id))
        
        conn.commit()
        flash(f"Student Registered Successfully! Roll No: {roll_number}")
    except sqlite3.IntegrityError:
        flash("Registration failure: Profile conflicts present.", "error")
    finally:
        conn.close()
        
    return redirect(url_for('dashboard', role='admin'))

@app.route('/admin/register_teacher', methods=['POST'])
def register_teacher():
    if session.get('role') != 'admin': return redirect(url_for('index'))
    teacher_username = request.form['teacher_username']
    teacher_password = request.form['teacher_password']

    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                     (teacher_username, teacher_password, 'teacher'))
        conn.commit()
        flash(f"Faculty Account '{teacher_username}' Provisioned Successfully!")
    except sqlite3.IntegrityError:
        flash("Error: Username already exists.", "error")
    finally:
        conn.close()
        
    return redirect(url_for('dashboard', role='admin'))

@app.route('/admin/update_usn/<int:student_id>', methods=['POST'])
def update_usn(student_id):
    if session.get('role') != 'admin': return redirect(url_for('index'))
    usn = request.form['usn']
    conn = get_db_connection()
    conn.execute('UPDATE students SET usn = ? WHERE id = ?', (usn, student_id))
    conn.commit()
    conn.close()
    flash("USN updated successfully across the registry.")
    return redirect(url_for('dashboard', role='admin'))

@app.route('/student/apply_leave', methods=['POST'])
def apply_leave():
    if session.get('role') != 'student': return redirect(url_for('index'))
    student_name = request.form['student_name']
    reason = request.form['reason']
    conn = get_db_connection()
    conn.execute('INSERT INTO leave_requests (student_name, reason) VALUES (?, ?)', (student_name, reason))
    conn.commit()
    conn.close()
    flash("Leave tracked successfully.")
    return redirect(url_for('dashboard', role='student'))


@app.route('/analyze_performance/<int:student_id>')
def analyze_performance(student_id):
    if 'role' not in session:
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    # Fetch student personal data
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    # Fetch performance numbers
    perf = conn.execute('SELECT * FROM performance WHERE student_id = ?', (student_id,)).fetchone()
    conn.close()
    
    if not student or not perf:
        return "Academic marks array not configured for this profile context.", 404

    # Extract score values safely (defaulting to 0.0 if empty)
    scores = [
        perf['test1'] if perf['test1'] is not None else 0.0,
        perf['test2'] if perf['test2'] is not None else 0.0,
        perf['test3'] if perf['test3'] is not None else 0.0,
        perf['lab_internals'] if perf['lab_internals'] is not None else 0.0
    ]
    metrics_labels = ['Test 1', 'Test 2', 'Test 3', 'Lab Internals']

    # Generate the performance analytics line plot using matplotlib
    plt.figure(figsize=(7, 4.5))
    plt.style.use('dark_background') # Matches our magical dark theme perfectly!
    
    # Customize plot style with a glowing gold/amber theme color line
    plt.plot(metrics_labels, scores, marker='o', linestyle='-', color='#eab308', linewidth=2.5, markersize=8)
    plt.title(f"Academic Performance Matrix - {student['name']}", fontsize=12, pad=15, color='#f8fafc', fontname='sans-serif')
    plt.ylabel("Acquired Scores (Max 50)", color='#94a3b8')
    plt.ylim(0, 55)
    plt.grid(True, linestyle='--', alpha=0.2, color='#334155')
    
    # Tight layout ensures clean image boundaries
    plt.tight_layout()
    
    # Save chart memory payload to a BytesIO buffer stream
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    plt.close()
    
    # Encode plot data array into base64 text token string
    plot_url = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    # Return a stylized, clean glassmorphic presentation view back to the viewport
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Performance Analytics Matrix</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; background: radial-gradient(circle at 50% 50%, #131c31 0%, #070a12 100%); }}
            .magical-title {{ font-family: 'Cinzel', serif; }}
        </style>
    </head>
    <body class="text-slate-100 min-h-screen flex items-center justify-center p-4">
        <div class="max-w-2xl w-full bg-slate-900/60 backdrop-blur-md border border-amber-500/20 rounded-2xl p-6 shadow-2xl text-center">
            <h2 class="magical-title text-xl font-bold text-amber-400 tracking-wider mb-2">MINISTRY OF ANALYTICS</h2>
            <p class="text-xs text-slate-400 uppercase tracking-widest mb-6">Dynamic Progression Assessment Map</p>
            
            <div class="bg-slate-950/80 p-4 rounded-xl border border-slate-800 flex justify-center mb-6">
                <img src="data:image/png;base64,{plot_url}" alt="Performance Matrix Line Chart" class="max-w-full h-auto rounded">
            </div>
            
            <button onclick="window.close()" class="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-amber-300 font-semibold text-xs rounded-lg uppercase tracking-wider transition-colors border border-slate-700">
                Dismiss Interface View
            </button>
        </div>
    </body>
    </html>
    """
if __name__ == '__main__':
    app.run(debug=True)