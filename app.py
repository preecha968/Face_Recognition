from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_session import Session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64

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


@app.route('/student_login', methods=['POST','GET'])
def student_login():
    if request.method == 'POST':
        id = request.form['id']
        email = request.form['email']
        password = request.form['password']
        student = students_collection.find_one({'id':id,'email':email,'password':password})
        if student:
            return redirect(url_for('student_profile'))
        else:
            return redirect(url_for('student_login'))
    return render_template ('student_login.html')



@app.route('/student_profile')
def student_profile():
    students = students_collection.find()  # Retrieve all student documents from MongoDB
    return render_template ('student_profile.html',students=students)




@app.route('/admin/dashboard')
def dashboard():
    if 'username' in session:
        students = students_collection.find()  # Retrieve all student documents from MongoDB
        return render_template("dashboard.html",students=students)
    else:
        return redirect(url_for('admin'))
    
    
    
    
@app.route('/admin/add_students', methods=["POST","GET"])
def add_students():
    if 'username' not in session:
            return render_template("admin.html")
    elif request.method == "POST":
        id = request.form['id']
        name = request.form['name']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        dob = request.form['dob']
        city = request.form['city']
        country = request.form['country']
        major = request.form['major']
        starting_year = request.form['starting_year']
        year = request.form['year']
        standing = request.form['standing']
        content = request.form['content']
        image =  request.files['image']
        
        if image:
            # Convert the image to base64 encoding
            image_data = base64.b64encode(image.read()).decode('utf-8')
        else:
            image_data = None
        
        
        students_collection.insert_one({
            "id": id,
            "name":name,
            "password":password,
            "email":email,
            "phone":phone,
            "dob":dob,
            "city":city,
            "country":country,
            "major":major,
            "starting_year":starting_year,
            "year":year,
            "standing":standing,
            "note":content,
            "image":image_data,      
        })
        flash ("added successfully") #อย่าลืมทำต่อ..ยังไม่แสดงผล
        
    return render_template("add_students.html")




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


    

if __name__ == "__main__":
    app.run(debug=True)
