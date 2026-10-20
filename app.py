from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'campus_problem_map_secret_key'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS problem (
                problem_id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_type TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                priority TEXT NOT NULL,
                building TEXT NOT NULL,
                floor TEXT,
                room_no TEXT,
                area_name TEXT NOT NULL,
                status TEXT DEFAULT 'Pending'
            )
        ''')
    conn.close()

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    sort_option = request.args.get('sort', 'newest')

    conn = get_db_connection()
    
    query = 'SELECT * FROM problem WHERE 1=1'
    params = []

    if search_query:
        query += ' AND (problem_type LIKE ? OR description LIKE ? OR building LIKE ?)'
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)

    if priority_filter:
        query += ' AND priority = ?'
        params.append(priority_filter)

    if sort_option == 'oldest':
        query += ' ORDER BY problem_id ASC'
    elif sort_option == 'priority':
        query += ''' ORDER BY CASE priority 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High' THEN 2 
                    WHEN 'Medium' THEN 3 
                    WHEN 'Low' THEN 4 
                    ELSE 5 END'''
    else:
        query += ' ORDER BY problem_id DESC'

    problems = conn.execute(query, params).fetchall()
    conn.close()
    
    role = session.get('role', 'student')
    return render_template('index.html', problems=problems, search_query=search_query, 
                           status_filter=status_filter, priority_filter=priority_filter, 
                           sort_option=sort_option, role=role)

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        session['role'] = request.form['role']
        flash('Successfully switched role!', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('role', None)
    return redirect(url_for('index'))

@app.route('/report', methods=('GET', 'POST'))
def report():
    if request.method == 'POST':
        problem_type = request.form['problem_type']
        description = request.form['description']
        date = request.form['date']
        priority = request.form['priority']
        building = request.form['building']
        floor = request.form['floor']
        room_no = request.form['room_no']
        area_name = request.form['area_name']

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO problem (problem_type, description, date, priority, building, floor, room_no, area_name) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (problem_type, description, date, priority, building, floor, room_no, area_name))
        conn.commit()
        conn.close()
        
        flash('Problem reported successfully!', 'success')
        return redirect(url_for('index'))
        
    return render_template('report.html')

@app.route('/update/<int:problem_id>', methods=('GET', 'POST'))
def update_status(problem_id):
    if session.get('role') != 'staff':
        flash('Access denied! Staff privileges required.', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    problem = conn.execute('SELECT * FROM problem WHERE problem_id = ?', (problem_id,)).fetchone()

    if request.method == 'POST':
        new_status = request.form['status']
        conn.execute('UPDATE problem SET status = ? WHERE problem_id = ?', (new_status, problem_id))
        conn.commit()
        conn.close()
        
        flash('Problem status updated successfully!', 'success')
        return redirect(url_for('index'))

    conn.close()
    return render_template('update.html', problem=problem)

@app.route('/delete/<int:problem_id>', methods=('POST',))
def delete_problem(problem_id):
    if session.get('role') != 'staff':
        flash('Access denied! Staff privileges required.', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    conn.execute('DELETE FROM problem WHERE problem_id = ?', (problem_id,))
    conn.commit()
    conn.close()
    
    flash('Problem deleted successfully!', 'success')
    return redirect(url_for('index'))

import os

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)