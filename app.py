#to start server and connect pages...for connectivity
from flask import Flask, render_template, request, redirect, url_for, flash,session
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from utils import generate_ebook, generate_text_from_audio

# database logic
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.now)

    def __str__(self):
        return f'{self.username}({self.id})'

class AudioUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    audio_name = db.Column(db.String(80), nullable=False)
    audio_file = db.Column(db.String(120), nullable=False)
    author_name = db.Column(db.String(120), nullable=True)
    is_converted = db.Column(db.Boolean, default=False)
    created_on = db.Column(db.DateTime, default=datetime.now)

    def __str__(self):
        return f'{self.audio_name}({self.id})'
# end of database logic
# flask app logic
def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///p2e.sqlite'
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.secret_key = 'supersecretkeythatnooneknows'
    db.init_app(app)
    return app

app = create_app()

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def create_login_session(user: User):
    session['id'] = user.id
    session['username'] = user.username
    session['email'] = user.email
    session['is_logged_in'] = True

def destroy_login_session():
    if 'is_logged_in' in session:
        session.clear()

'''
to create the project database, open terminal
- type python and press enter
- type
    from app import app, db
    with app.app_context():
        db.create_all()
- enter twice to confirm
'''

@app.route('/')
def index():
    # flash('Welcome to Podcast to Ebook', 'info')
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login',  methods=['GET','POST'])
def login():
    errors = {}
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        print("LOGGING IN",email, password)
        if password and email:
            if len(email) < 11 or '@' not in email:
                errors['email'] = 'Email is Invalid'
            if len(errors) == 0:
                user = User.query.filter_by(email=email).first()
                if user is not None:
                    print("user account found", user)
                    if user.password == password:
                        create_login_session(user)
                        flash('Login Successful', "success")
                        return redirect('/')
                    else:
                        errors['password'] = 'Password is invalid'
                else:
                    errors['email']= 'Account does not exists'
        else:
            errors['email'] = 'Please fill valid details'
            errors['password'] = 'Please fill valid details'
    return render_template('login.html', errors = errors)

@app.route('/register', methods=['GET','POST'])
def register():
    errors = []
    if request.method == 'POST': # if form was submitted
        username = request.form.get('username')
        email = request.form.get('email')
        pwd = request.form.get('password')
        cpwd = request.form.get('confirmpass')
        print(username, email, pwd, cpwd)
        if username and email and pwd and cpwd:
            if len(username)<2:
                errors.append("Username is too small")
            if len(email) < 11 or '@' not in email:
                errors.append("Email is invalid")
            if len(pwd) < 6:
                errors.append("Password should be 6 or more chars")
            if pwd != cpwd:
                errors.append("passwords do not match")
            if len(errors) == 0:
                user = User(username=username, email=email, password=pwd)
                db.session.add(user)
                db.session.commit()
                flash('user account created','success')
                return redirect('/login')
        else:
            errors.append('Fill all the fields')
            flash('user account could not be created','warning')
    return render_template('register.html', error_list=errors)

@app.route('/logout')
def logout():
    destroy_login_session()
    flash('You are logged out','success')
    return redirect('/')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'is_logged_in' not in session:
        flash('You need to login first', 'warning')
        return redirect('/login')

    if request.method == 'POST':
        audio_name = request.form.get('audio_name')
        author_name = request.form.get('author_name')
        audio_file = request.files.get('audio_file')

        if not audio_name or not author_name or not audio_file:
            flash('Please fill all the fields', 'warning')
            return render_template('upload.html')  # Stay on the upload page

        # Save the file and add it to the database
        filename = secure_filename(audio_file.filename)
        audio_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        audio = AudioUpload(audio_name=audio_name, author_name=author_name, audio_file=filename)
        db.session.add(audio)
        db.session.commit()

        flash('Audio file uploaded successfully', 'success')
        return redirect(url_for('convert'))  # Redirect to the list page after success

    return render_template('upload.html')


@app.route('/list', methods=['GET','POST'])
def convert():
    if 'is_logged_in' not in session:
        flash('You need to login first', 'warning')
        return redirect('/login')
    audio_files = AudioUpload.query.all()
    return render_template('list.html', audio_files=audio_files)

@app.route('/preview', methods=['POST'])
def preview_pdf():
    # Fetch form data
    id = request.form.get('id')
    author_name = request.form.get('author_name')
    edited_text = request.form.get('text')
    audio = AudioUpload.query.get(id)

    # Generate a temporary preview PDF
    preview_path = generate_ebook(
        edited_text,
        audio.audio_file,
        author_name=author_name,
        is_preview=True
    )

    # Serve the preview PDF
    return redirect(f"/static/previews/{os.path.basename(preview_path)}")


@app.route('/confirm', methods=['POST'])
def confirm_pdf():
    # Fetch form data
    id = request.form.get('id')
    author_name = request.form.get('author_name')
    edited_text = request.form.get('text')
    audio = AudioUpload.query.get(id)

    # Generate and save the final PDF
    final_path = generate_ebook(
        edited_text,
        audio.audio_file,
        author_name=author_name,
        is_preview=False
    )

    # Update database and mark audio as converted
    audio.is_converted = True
    db.session.commit()

    # Serve the final PDF
    flash("Your eBook has been created successfully!", "success")
    return redirect(f"/static/output/{os.path.basename(final_path)}")

@app.route('/convert/<int:id>', methods=['GET', 'POST'])
def convert_audio(id):
    audio = AudioUpload.query.get(id)

    if request.method == 'POST':
        # Get the edited text from the form
        edited_text = request.form.get('text')
        author_name = audio.author_name  # Fetch the author's name from the database

        # Generate the PDF with the edited text
        file_path = generate_ebook(edited_text, audio.audio_file, author_name=author_name)

        # Mark the audio as converted and save changes
        audio.is_converted = True
        db.session.commit()

        # Store the PDF file path in the session
        session['pdf_file'] = file_path
        flash('Your eBook has been created successfully!', 'success')
        return redirect('/ebooks')

    # Generate the transcription for the first time
    content = generate_text_from_audio(f"static/uploads/{audio.audio_file}")
    return render_template('confirm_ebook_text.html', audio=audio, content=content, id=id)

@app.route('/delete/<int:id>', methods=['GET','POST'])
def delete_audio(id):
    audio = AudioUpload.query.get(id)
    try:
        os.remove("/"+os.path.join(app.config['UPLOAD_FOLDER'], audio.audio_file))
    except:
        pass
    db.session.delete(audio)
    db.session.commit()
    # delete the file from the folder
    flash('Audio file deleted successfully', 'success')
    return redirect('/list')

@app.route('/ebooks', methods=['GET','POST'])
def ebooks():
    audio_files = AudioUpload.query.filter_by(is_converted=True).all()
    return render_template('ebooks.html', audio_files=audio_files, file=session.get('pdf_file'))

@app.route('/results', methods=['GET','POST'])
def result():
    return render_template('results.html')

if __name__ == '__main__':
    # create database tables
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)