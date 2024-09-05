from flask import Flask, render_template, request, redirect, url_for, session, flash,Response,jsonify
from flask_bcrypt import Bcrypt
from flask_session import Session
from pymongo import MongoClient
from bson.objectid import ObjectId
import base64
import face_recognition
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from datetime import datetime
import os
import requests
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

bcrypt = Bcrypt(app)

###############################################################################################################

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['attendance_system']
# collections
users_collection = db['users']
students_collection = db['students']
students_face_collection = db['students_face']

###############################################################################################################

# Directory to save captured faces
captured_faces_dir = os.path.join('static', 'captured_faces')
os.makedirs(captured_faces_dir, exist_ok=True)


# Dictionary to store the last capture time of each person
last_capture_time = {}

# Set a cooldown time (in seconds) to avoid multiple captures for the same person
CAPTURE_COOLDOWN = 10  # Cooldown of 10 seconds between captures


# Your LINE Notify access token
LINE_NOTIFY_TOKEN = 'pMKUcLIdvfcH7I9A3tEjGS0MOc3AgdEXHUUtFqwEF8V'

def send_line_notify(message, image_path):
    """Send a notification to LINE with an image."""
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {LINE_NOTIFY_TOKEN}'}
    data = {'message': message}
    
    with open(image_path, 'rb') as image_file:
        files = {'imageFile': image_file}
        response = requests.post(url, headers=headers, data=data, files=files)
    
    print(f"LINE Notify response status: {response.status_code}")
    return response.status_code == 200

###############################################################################################################

def load_known_faces():
    known_face_encodings = []
    known_face_names = []
    for student in students_face_collection.find():
        known_face_encodings.append(np.array(student['face_encoding']))
        known_face_names.append(student['name'])
    return known_face_encodings, known_face_names

def generate_frames():
    video_capture = cv2.VideoCapture(0)
    known_face_encodings, known_face_names = load_known_faces()

    process_this_frame = True
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        if process_this_frame:
            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []
            for face_encoding, face_location in zip(face_encodings, face_locations):
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"

                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]

                    # Get current time
                    current_time = time.time()

                    # Check if enough time has passed since last capture
                    if name not in last_capture_time or (current_time - last_capture_time[name] > CAPTURE_COOLDOWN):
                        last_capture_time[name] = current_time

                        # Capture and save the face image
                        top, right, bottom, left = face_location
                        top *= 2
                        right *= 2
                        bottom *= 2
                        left *= 2
                        captured_face = frame[top:bottom, left:right]

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_name = f"{name}_{timestamp}.jpg"
                        file_path = os.path.join(captured_faces_dir, file_name)

                        # Save the captured face image
                        cv2.imwrite(file_path, captured_face)

                        # Prepare a message with the student's name and timestamp
                        message = f"Student: {name}\nDate: {datetime.now().strftime('%Y-%m-%d')}\nTime: {datetime.now().strftime('%H:%M:%S')}"

                        # Send the image and message to LINE Notify
                        send_line_notify(message, file_path)

                face_names.append(name)

        process_this_frame = not process_this_frame

        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 2
            right *= 2
            bottom *= 2
            left *= 2

            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.rectangle(frame, (left, bottom - 1), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 4), font, 0.6, (255, 255, 255), 1)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# Video stream route
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_recognized_faces')
def get_recognized_faces():
    recognized_faces = []  # Store recognized faces data

    return jsonify(recognized_faces)

###############################################################################################################

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

###############################################################################################################

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
    
###############################################################################################################

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

###############################################################################################################

@app.route('/student_login', methods=['POST', 'GET'])
def student_login():
    if request.method == 'POST':
        id = request.form['id']
        email = request.form['email']
        password = request.form['password']
        student = students_collection.find_one({'id': id, 'email': email, 'password': password})
        if student:
            session['student'] = {
                'id': student['id'],
                'name': student['name'],
                'email': student['email'],
                'image': student['image']
                # Add other fields as needed
            }
            return redirect(url_for('student_profile'))
        else:
            return redirect(url_for('student_login'))
    return render_template('student_login.html')

###############################################################################################################

@app.route('/student_profile')
def student_profile():
    student = session.get('student')
    if student:
        return render_template('student_profile.html', student=student)
    else:
        return redirect(url_for('student_login'))


###############################################################################################################

@app.route('/admin/dashboard')
def dashboard():
    if 'username' in session:
        students = students_collection.find()  # Retrieve all student documents from MongoDB
        return render_template("dashboard.html",students=students)
    else:
        return redirect(url_for('admin'))

###############################################################################################################
    
       
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

         # Retrieve the image from MongoDB
        student_record = students_collection.find_one({"id": id})
        if student_record and student_record.get("image"):
            # Decode the base64 image data
            image_data = base64.b64decode(student_record["image"])
            
            # Load the image into a PIL image object
            image = Image.open(BytesIO(image_data))
            
            # Convert the image to a format usable by face_recognition
            image = image.convert('RGB')
            image = face_recognition.load_image_file(BytesIO(image_data))
            
            # Detect the face locations and generate facial encoding
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if len(face_encodings) == 0:
                print(f"No faces found in the image.")
            else:
                # Use the first face encoding found
                face_encoding = face_encodings[0]
                
                # Prepare the data to be stored in MongoDB
                student_face_data = {
                    'name': name,
                    'face_encoding': face_encoding.tolist()  # Convert numpy array to a list
                }
                
                # Insert the student face data into MongoDB
                students_face_collection.insert_one(student_face_data)
                print(f"Stored {name}'s facial encoding in MongoDB.")
        
        
    return render_template("add_students.html")


###############################################################################################################

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

###############################################################################################################

if __name__ == "__main__":
    app.run(debug=True)
