import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, session, flash
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'tracker_secret_key_123'

# 🔑 STEP 1 VALA EXTERNAL DATABASE URL YAHAN PASTE KARNA HAI
# Example: "postgres://user:password@host:port/dbname"
DB_URL = "postgresql://budget_tracker_db_udnb_user:kjMCXok7mMN38uDlhgraVc8fFq0Y55nl@dpg-d8fv36f40ujc73bgce30-a.singapore-postgres.render.com/budget_tracker_db_udnb"
GRAPH_FOLDER = os.path.join('static', 'graphs')
os.makedirs(GRAPH_FOLDER, exist_ok=True)

def get_db_connection():
    # Yeh cloud database se safe connection banata hai
    conn = psycopg2.connect(DB_URL)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # PostgreSQL syntax ke mutabik SERIAL primary key use ki hai
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Pehli baar run hote hi cloud database mein tables automatic ban jayengi
try:
    init_db()
except Exception as e:
    print(f"Database Connection Error: {e}. Please check your DB_URL!")

def generate_chart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, SUM(amount) 
        FROM transactions 
        WHERE user_id = %s AND type = 'Expense' 
        GROUP BY category
    """, (user_id,))
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not data:
        chart_path = os.path.join(GRAPH_FOLDER, f'chart_user_{user_id}.png')
        if os.path.exists(chart_path):
            os.remove(chart_path)
        return

    categories = [row[0] for row in data]
    amounts = [row[1] for row in data]

    plt.figure(figsize=(5, 5))
    plt.pie(amounts, labels=categories, autopct='%1.1f%%', colors=['#ff4b4b', '#ff7676', '#ffb3b3', '#ffd1d1', '#ffa4a4'])
    plt.title('Expense Breakdown', color='white', fontsize=14)
    
    fig = plt.gcf()
    fig.patch.set_facecolor('#222f3d')
    plt.gca().set_facecolor('#222f3d')
    
    for text in plt.gca().texts:
        text.set_color('white')

    chart_path = os.path.join(GRAPH_FOLDER, f'chart_user_{user_id}.png')
    plt.savefig(chart_path, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        amount = float(request.form.get('amount'))
        trans_type = request.form.get('type')
        category = request.form.get('category')
        description = request.form.get('description')

        cursor.execute("""
            INSERT INTO transactions (user_id, amount, type, category, description) 
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, amount, trans_type, category, description))
        conn.commit()
        generate_chart(user_id)
        flash('Transaction added successfully!', 'success')

    cursor.execute("SELECT * FROM transactions WHERE user_id = %s", (user_id,))
    transactions = cursor.fetchall()
    cursor.close()

    total_income = 0
    total_expense = 0
    for t in transactions:
        if t[3] == 'Income':
            total_income += t[2]
        else:
            total_expense += t[2]

    balance = total_income - total_expense
    conn.close()

    return render_template('dashboard.html', transactions=transactions, total_income=total_income, total_expense=total_expense, balance=balance)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
