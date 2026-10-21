from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'campus_problem_map_secret_key'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect('database.db')
    # Updated table with building, priority, and date
    conn.execute('''
        CREATE TABLE IF NOT EXISTS problem (
            problem_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            building TEXT NOT NULL,
            floor TEXT NOT NULL,
            room_number TEXT NOT NULL,
            area TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Pending',
            date TEXT NOT NULL
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', 'password123'))
    
    conn.commit()
    conn.close()

@app.route('/')
def role_select():
    return render_template('role_select.html')

@app.route('/dashboard')
def index():
    search_query = request.args.get('search', '').strip()
    status_filter = request.args.get('status', 'All')
    priority_filter = request.args.get('priority', 'All')
    sort_by = request.args.get('sort', 'newest')
    
    conn = get_db_connection()
    
    query = "SELECT * FROM problem WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND (title LIKE ? OR building LIKE ? OR area LIKE ? OR description LIKE ?)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term, like_term])
        
    if status_filter and status_filter != 'All':
        query += " AND status = ?"
        params.append(status_filter)
        
    if priority_filter and priority_filter != 'All':
        query += " AND priority = ?"
        params.append(priority_filter)
        
    # Sorting
    if sort_by == 'status':
        query += " ORDER BY status ASC"
    elif sort_by == 'priority':
        query += " ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END"
    else:  # newest first
        query += " ORDER BY problem_id DESC"
        
    problems = conn.execute(query, params).fetchall()
    conn.close()
    
    # Determine current role name for display
    role_name = 'Administrator' if session.get('user_id') else 'Student'
    
    return render_template('index.html', problems=problems, 
                           search=search_query, 
                           current_status=status_filter, 
                           current_priority=priority_filter, 
                           current_sort=sort_by,
                           role_name=role_name)

@app.route('/report', methods=('GET', 'POST'))
def report():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        building = request.form['building']
        floor = request.form['floor']
        room_number = request.form['room_number']
        area = request.form['area']
        priority = request.form.get('priority', 'Medium')
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO problem (title, description, building, floor, room_number, area, priority, status, date) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
        ''', (title, description, building, floor, room_number, area, priority, date_str))
        conn.commit()
        conn.close()
        flash('Problem reported successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('report.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('role_select'))

@app.route('/update/<int:problem_id>', methods=['GET', 'POST'])
def update_problem(problem_id):
    if 'user_id' not in session:
        flash('Please log in first to update status.', 'danger')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    problem = conn.execute('SELECT * FROM problem WHERE problem_id = ?', (problem_id,)).fetchone()

    if request.method == 'POST':
        status = request.form['status']
        conn.execute('UPDATE problem SET status = ? WHERE problem_id = ?', (status, problem_id))
        conn.commit()
        conn.close()
        flash('Problem status updated successfully!', 'success')
        return redirect(url_for('index'))

    conn.close()
    return render_template('update.html', problem=problem)

@app.route('/delete/<int:problem_id>')
def delete_problem(problem_id):
    if 'user_id' not in session:
        flash('Please log in first to delete a problem.', 'danger')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM problem WHERE problem_id = ?', (problem_id,))
    conn.commit()
    conn.close()
    
    flash('Problem deleted successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)