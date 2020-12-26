from flask import Flask
from flask import render_template
from flask import request, redirect, url_for
from flask import session, flash
from bcrypt import hashpw, gensalt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
from werkzeug.utils import secure_filename
import boto3

fle=open('db.properties')
property=fle.readlines()[2]
fle.close()

app = Flask(__name__)

UPLOAD_FOLDER = '/tmp/static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SECRET_KEY']='e5ac358c-f0bf-11e5-9e39-d3b532c10a28'
app.config["SQLALCHEMY_DATABASE_URI"] = property
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
db=SQLAlchemy(app)

s3= boto3.client("s3")
bucket_name = "mys3testmount"

#user info table for the db
class Users(db.Model):
	__tablename__="users_info"
	id=db.Column('id', db.Integer, primary_key=True)
	username=db.Column('username', db.String(20), unique=True)
	email = db.Column('email', db.String(30))
	password = db.Column('password', db.String(100))

	def __init__(self, username, email, password):
		self.username=username
		self.email=email
		self.password=password

# books info table
class Book(db.Model):
    __tablename__="books"
    book_id = db.Column('book_id', db.Integer, primary_key=True)
    title = db.Column('title', db.String(50))
    price = db.Column('price', db.Numeric(10,2))
    book_description = db.Column('book_description', db.String(200))
    author = db.Column('author', db.String(50))

    def __init__(self, title, price, book_description, author):
        self.title = title
        self.price = price
        self.book_description = book_description
        self.author = author

class Genre(db.Model):
    __tablename__="genres"
    id = db.Column('id', db.Integer, primary_key=True)
    book_id = db.Column('book_id', db.Integer)
    genre = db.Column('genre', db.String())
    
    def __init__(self, book_id, genre):
        self.book_id = book_id
        self.genre = genre


def convert(pas):
    pas=pas.encode()
    new_pas=hashpw(pas, gensalt())
    return new_pas

@app.route("/")
def index():
    return render_template("home.html")


@app.route("/login")
def login():
    return render_template("login.html")


#Validating a user for login
@app.route('/validate', methods=["POST"])
def validate():
    userName=request.form['username']
    session['user']=userName
    password=request.form['password']

    if userName=="" or password=="":
        flash("Required fields are missing..!")
        return render_template('login.html')
    pass1=Users.query.filter_by(username=userName).first()
    if pass1==None:
            return render_template('foff.html')
    else:
            password=password.encode('utf-8')
            db_pass=pass1.password.encode()
            if hashpw(password, db_pass)==db_pass:
                return redirect(url_for('explore'))
            else:
                flash("Invalid credentials...!")
                return render_template('login.html')


@app.route("/signup")
def signup():
    return render_template("signup.html")


#Sending data to the database 
@app.route('/register', methods=["POST"])
def register():
    username=request.form['username']
    email=request.form['email']
    password=request.form['password']

    session['user']=username

    new_pass=convert(password)
    if username=="" or email=="" or password=="":
        flash("Mandatory fields are missing")
        return render_template('signup.html')
    sign = Users(username=username, email=email, password=new_pass)
    try:
        db.session.add(sign)
        db.session.commit()
    except exc.IntegrityError:
        flash('Username already exists!!!')
        return render_template("signup.html")
    return redirect(url_for('explore'))

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/admin_validate', methods=["POST"])
def admin_validate():
    userName=request.form['username']
    password=request.form['password']

    admin_creds=open('admin.properties')
    for line in admin_creds:
        k,v  = line.split("=")
        k=k.strip(); v = v.strip()
        if k =="username":
            admin_username = v
        if k == "password":
            admin_password = v

    if admin_username == userName and admin_password == password:
        session['admin_user']=userName
        return redirect(url_for('addBook'))
    else:
        flash("Incorrect credentials")
        return render_template('admin.html')

@app.route("/add")
def addBook():
    
    if 'admin_user' not in session:
        return redirect(url_for('admin'))
    
    return render_template('add_book.html')
    
@app.route("/add_book", methods = ["POST"])
def add_book_to_db():
    name = request.form['bookname']
    cost = request.form['cost']
    descr = request.form['description']
    authr = request.form['author']
    genre = reque
    st.form.getlist('cb')
    img = request.files['file']

    print(genre)

    if name=="" or cost=="" or descr=="" or authr=="":
        flash("Mandatory fields are missing")
        return render_template('signup.html')
    img_name = img.filename
    exten = img_name.split(".")[1]
    if exten not in ALLOWED_EXTENSIONS:
        flash("Pic is not in allowed extensions...")
        return render_template('add_book.html')

    try:
        add_book = Book(title=name, price=cost, book_description=descr, author=authr)
        db.session.add(add_book)
        db.session.commit()
        id = add_book.book_id

        for i in genre:
            add_genre = Genre(book_id = id, genre = i)
            db.session.add(add_genre)
            db.session.commit()
            
    except exc.IntegrityError:
        flash('Some error occured. Contact your developer...')
        return render_template("add_book.html")
    
    if img:
        print(id)
        filename = str(id) + "." + exten
        tmp_loc = "/tmp/images/" + filename
        img.save(tmp_loc)
        index_file = "images/"+filename
        s3.upload_file(Bucket = bucket_name, Filename=tmp_loc, Key = index_file)
        print("Upload is successful")
    flash("Image was added successfully!")
    return render_template('add_book.html')

@app.route("/delete")
def delete():
    
    if 'admin_user' not in session:
        return redirect(url_for('admin'))

    data = Book.query.all()
    print(data)
    return render_template("delete.html", data=data)

@app.route("/delete_book")
def delete_book():
    flash("The book was deleted")
    return render_template("delete.html")


@app.route("/explore")
def explore():
    user=session.get('user')
    if not user:
        return redirect(url_for('login'))
    
    data = Book.query.all()
    return render_template('explore.html', data = data)

@app.route("/book/<book_iid>")
def single_book_page(book_iid):
    return "Details of the book are: " + book_iid


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/admin_logout")
def admin_logout():
    session.pop("admin_user", None)
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
