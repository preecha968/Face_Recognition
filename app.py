from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_session import Session
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

bcrypt = Bcrypt(app)

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['attendance_system']
# collections
users_collection = db['users']
students_collection = db['students']

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = users_collection.find_one({"username": username})

    if user and bcrypt.check_password_hash(user['password'], password):
        session['username'] = username
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid username or password')
        return redirect(url_for('admin'))

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    
    # Check if the user already exists
    if users_collection.find_one({"username": username}):
        flash('Username already exists')
        return redirect(url_for('admin'))

    # Hash the password and store the new user
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    users_collection.insert_one({
        "username": username,
        "email": email,
        "password": hashed_password
    })

    flash('Signup successful! Please log in.')
    return redirect(url_for('admin'))

@app.route('/admin/dashboard')
def dashboard():
    if 'username' in session:
        return render_template("dashboard.html")
    else:
        return redirect(url_for('admin'))
    
@app.route('/admin/add_students', methods=["POST","GET"])
def add_students():
    if request.method == "POST":
        id = request.form['id']
        name = request.form['name']
        password = request.form['password']
        dob = request.form['dob']
        
        students_collection.insert_one({
            "id": id,
            "name":name,
            "password":password,
            "dob":dob,
        })
        flash ("added successfully")
    
        if 'username' in session:
            return render_template("add_students.html")
        else:
            return redirect(url_for('admin'))
    return render_template("add_students.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


    

if __name__ == "__main__":
    app.run(debug=True)
