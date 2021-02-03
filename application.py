from flask import Flask
from flask import render_template
from flask import request, redirect, url_for, jsonify
from flask import session, flash
from bcrypt import hashpw, gensalt
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
from sqlalchemy import exc
from werkzeug.utils import secure_filename
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
import boto3
import json
from datetime import datetime
import jwt

#read properties 
fle=open('properties.txt')
for i in fle.readlines():
    property,value = i.split("=") 
    if property.strip() == "db_name":
        DB_NAME = value.strip()
    if property.strip() == "region":
        REGION = value.strip()
    if property.strip()=="secret_name":
        SECRET_NAME = value.strip()
    if property.strip() == "s3_bucketname":
        S3_BUCKET = value.strip()
    if property.strip() == "cloufront_url":
        CLOUDFRONT_URL = value.strip()
    if property.strip() == "queue_url":
        QUEUE_URL = value.strip()

fle.close()

def get_secret(secret_name):

    region_name = "ap-south-1"
    client = boto3.client(
        service_name='secretsmanager',
        region_name=region_name, 
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except:
        print("ERROR")
    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
    else:
        decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])

    return secret

# clients
s3 = boto3.client("s3", region_name = REGION)
sqs = boto3.client("sqs", region_name = REGION)

application = Flask(__name__)
cors = CORS(application)
application.config['CORS_HEADERS'] = 'Content-Type'

UPLOAD_FOLDER = '/tmp/static/uploads'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
application.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

application.config['SECRET_KEY']='e5ac358c-f0bf-11e5-9e39-d3b532c10a28'


secret = get_secret(SECRET_NAME)
secret = json.loads(secret)
DB_STRING = "mysql+mysqlconnector://" + secret["username"] + ":" + secret["password"] + "@" + secret["host"] + "/" + DB_NAME
application.config["SQLALCHEMY_DATABASE_URI"] = DB_STRING
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db=SQLAlchemy(application)


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


class Orders(db.Model):
    __tablename__="orders"
    id = db.Column('id', db.Integer, primary_key=True)
    book_id = db.Column('book_id', db.Integer)
    username = db.Column('username', db.String(50))
    order_time = db.Column('ordered_time', db.DateTime, default=db.func.current_timestamp())
    address = db.Column('address', db.String(150))
    pin_code = db.Column('pincode', db.String(6))
    phone = db.Column('phone', db.String(15))
    cx_name = db.Column('cx_name', db.String(30))
    quantity = db.Column('quantity', db.Integer)
    price = db.Column('total_price', db.Integer)
    order_status = db.Column('order_status', db.String(20), default = "order received")
    
    def __init(self, book_id, username, address, phone, cx_name, pin_code):
        self.book_id = book_id
        self.username = username
        self.address = address
        self.phone = phone
        self.cx_name = cx_name
        self.quantity = quantity
        self.price = price
        self.pin_code = pin_code



@application.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*" # <- You can change "*" for a domain for example "http://localhost"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Accept, Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization"
    return response


@application.route("/app/get_books")
@cross_origin()
def get_books():
    response = []
    book_iid = request.args.get('book_id')
    if book_iid:
        data = Book.query.filter_by(book_id = book_iid)
    else:
        data = Book.query.all()
    for i in data:
       response.append({"book_id": i.book_id, "title": i.title, "book_description": i.book_description, "price": i.price, "author": i.author, "image": str(i.book_id)+".jpg"})
    print(response)
    return jsonify(response)


@application.route("/app/get_orders", methods=["POST"])
@cross_origin()
def get_orders():
    print("request data is ", request.data)
    user_name = json.loads(request.data.decode("ascii"))["username"]
    print("username is ", user_name)
    response = []
    data = Orders.query.filter_by(username = user_name)
    for i in data:
        response.append({"id": i.id,"book_id": i.book_id,"username": i.username, "ordered_time": i.order_time, "address": i.address, "phone": i.phone, "cx_name": i.cx_name, "quantity": i.quantity, "total_price": i.price, "order_status": i.order_status})
    print("response is ",response)
    return jsonify(response)


@application.route("/make_order/<book_iid>", methods=["POST"])
@cross_origin()
def make_order(book_iid):
    book_info = Book.query.filter_by(book_id = book_iid)
    data = request.get_json()
    username = data['userAttributes'].get("username")

    cx_name = data['name']
    address = data['address']
    phone = data['phone']
    quantity = data['quantity']
    pin_code = data["pincode"]
    if address=="" or phone=="" or quantity=="" or cx_name=="" :
        flash("Mandatory fields are missing")
        return render_template('order.html', data = book_info)
    tot_price = float(book_info[0].price) * int(quantity)

    try:
        ma_order = Orders(book_id = book_iid, address = address, cx_name = cx_name, phone = phone, username = username, quantity = quantity, price = tot_price, pin_code=pin_code)
        db.session.add(ma_order)
        db.session.commit()
        flash('Your order was done successfully')
    except exc.IntegrityError:
        flash('Some error occured. Contact support...')

        #Sending message to the queue
    email = data["userAttributes"]["attributes"]["email"]
    order_id = ma_order.id
    message_body = {"email": email, "order_id": order_id, "name": cx_name, "book_name": book_info[0].title, "total_price": tot_price}
    try:
        response = sqs.send_message(QueueUrl = QUEUE_URL, MessageBody=json.dumps(message_body), MessageAttributes = {'purpose': {'DataType': 'String','StringValue': 'order'}})
    except:
        return {"status": "failed"}
    return {"status": "succede"}


################
#  Admin code  #
################

@application.route('/admin')
def admin():
    return render_template('admin.html')


@application.route('/admin_validate', methods=["POST"])
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


@application.route("/add")
def addBook():
    
    if 'admin_user' not in session:
        return redirect(url_for('admin'))
    
    return render_template('add_book.html')


@application.route("/add_book", methods = ["POST"])
def add_book_to_db():
    name = request.form['bookname']
    cost = request.form['cost']
    descr = request.form['description']
    authr = request.form['author']
    genre = request.form.getlist('cb')
    img = request.files['file']


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
        filename = str(id) + "." + exten
        tmp_loc = "/tmp/" + filename
        img.save(tmp_loc)
        index_file = "images/"+filename
        s3.upload_file(Bucket = S3_BUCKET, Filename=tmp_loc, Key = index_file)
    flash("Image was added successfully!")
    return render_template('add_book.html')


@application.route("/delete")
def delete():
    
    if 'admin_user' not in session:
        return redirect(url_for('admin'))

    data = Book.query.all()
    return render_template("delete.html", data=data)


@application.route("/delete_book/<book_iid>")
def delete_book(book_iid):
    if 'admin_user' not in session:
        return redirect(url_for('admin'))

    book_tilte = Book.query.filter_by(book_id=book_iid).delete()
    db.session.commit()

    flash("The book "+ book_tilte + " was deleted")
    return render_template("delete.html")


@application.route("/admin_logout")
def admin_logout():
    session.pop("admin_user", None)
    return redirect(url_for("admin"))


if __name__ == "__main__":
    application.run(host="0.0.0.0")