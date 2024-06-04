from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import time
import os
import threading

db_host = os.getenv("DB_HOST", "db")
db_user = os.getenv("DB_USER", "user")
db_password = os.getenv("DB_PASSWORD", "pw")
db_name = os.getenv("DB_NAME", "notes")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}/{db_name}'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

SLEEP_DELAY = 0.5

def setup_db():
    for i in range(1, 20):
        try:
            with app.app_context():
                db.create_all()
            break
        except OperationalError:
            time.sleep(SLEEP_DELAY)

database_setup_thread = threading.Thread(target=setup_db)
database_setup_thread.start()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        note_content = request.form.get('content')
        new_note = Note(content=note_content, user_id=session['user_id'])
        db.session.add(new_note)
        db.session.commit()
        return redirect(url_for('index'))

    user_id = session['user_id']
    notes = Note.query.filter_by(user_id=user_id).all()
    return render_template('index.html', notes=notes)


@app.route('/delete/<int:note_id>')
def delete(note_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    note_to_delete = Note.query.get_or_404(note_id)
    if note_to_delete.user_id != session['user_id']:
        return redirect(url_for('index'))

    db.session.delete(note_to_delete)
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/healthz')
def healthz():
    return jsonify({"status": "OK"})


@app.route('/readyz', methods=['GET'])
def readiness_probe():
    try:
        # Attempt a simple query to check database connection
        db.session.execute(text('SELECT 1'))
        return jsonify(success=True, message="Database is reachable and initialized"), 200
    except OperationalError as e:
        # Log the exception if needed
        return jsonify(success=False, message="Database is not reachable"), 500

if __name__ == '__main__':
    app.run(debug=True)
