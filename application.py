import os

from flask import Flask, session, render_template, request, redirect, url_for, logging, flash, json, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash

import requests

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config['SECRET_KEY'] = 'chulito es el mas lindo'
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
app_permanent_session_lifetime = timedelta(hours=24)
Session(app)


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def home():
    if "user" in session:
        username = session["user"]
        return render_template('search.html', username=username)
    return render_template("home.html" )


@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        username=request.form.get("nm")
        password=request.form.get("psw")
        email=request.form.get("em")
        
        usernamedata=db.execute("SELECT username FROM users WHERE username=:username OR email=:email",{"username":username, "email":email}).fetchone()
        if usernamedata==None:
                hashed_password = generate_password_hash(request.form.get("psw"))
                db.execute("INSERT INTO users(email,username,password) VALUES(:email,:username,:password)",
                    {"email":email,"username":username,"password":hashed_password})
                db.commit()
                flash("You are registered and can now login","success")
                return redirect(url_for('login'))
        else:
            flash("user already existed, please select a diferent one")
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form.get("nm")
        u=db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()


        if  check_password_hash(u.password, request.form.get("psw")):
            flash("You are now logged in!!","success")
            session["user"] = username
            return redirect(url_for('user')) 
        else:
            flash("incorrect password","danger")
            return redirect(url_for('register'))
    return render_template("register.html")

@app.route("/user", methods=["GET","POST"])
def user():
    if "user" in session:
        username = session["user"]
    
        if request.method=="POST":
            search = request.form.get("search")

            if db.execute("SELECT * FROM books WHERE year LIKE :search OR isbn LIKE :search OR title LIKE :search OR author LIKE :search " , {"search": f"%{search}%"}).rowcount == 0:    
                flash("Book not found, try another search") 
                return render_template("search.html", username=username ) 

            books = db.execute("SELECT * FROM books WHERE year LIKE :search OR isbn LIKE :search OR title LIKE :search OR author LIKE :search " , {"search": f"%{search}%"}).fetchall()
            return render_template("search.html", books=books, username=username )
        return render_template("search.html", username=username ) 
    
    return redirect(url_for('register'))


    
@app.route("/search/<string:isbn>",  methods=["GET","POST"])
def book(isbn):

    book_id,=db.execute("SELECT id FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    username=session["user"]
    book= db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    reviews = db.execute("SELECT * FROM reviews JOIN users ON reviews.user_id = users.id WHERE book_id = :book_id", {"book_id": book_id}).fetchall()
    user_id, = db.execute("SELECT id from users WHERE username = :username", {"username": username}).fetchone()

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "BHiBlFbwdoHJlsrtgfUXA", "isbns": isbn})
    if res.status_code != 200:
        raise Exception("ERROR: API request unsuccessful.")

    average =res.json()["books"][0]["average_rating"]
    rating =res.json()["books"][0]["work_ratings_count"]

    if request.method=="POST":
        if not request.form.get("score"):
            flash("You must complete all fields")

        else:
            if db.execute("SELECT user_id FROM reviews WHERE book_id =:book_id AND user_id =:user_id", {"user_id": user_id, "book_id": book_id}).rowcount==0: #check if the user already comment
                score=int(request.form.get("score"))
                opinion=request.form.get("opinion")
                
                db.execute("INSERT INTO reviews(score, opinion, book_id, user_id) VALUES(:score, :opinion, :book_id, :user_id)",{"score":score, "opinion":opinion, "book_id":book_id, "user_id":user_id})
                db.commit()        
                reviews = db.execute("SELECT * FROM reviews JOIN users ON reviews.user_id = users.id WHERE book_id = :book_id", {"book_id": book_id}).fetchall()
                return render_template("book.html", book=book , reviews=reviews, username=username, average=average, rating=rating )
            else:
                flash("You have already comment this book")   
                return render_template("book.html", book=book , reviews=reviews, username=username )
    return render_template("book.html", book=book , reviews=reviews, username=username, average=average, rating=rating)    

@app.route("/logout/")
def logout():
    session.pop("user", None)
    return render_template("home.html")

@app.route("/api/search/<string:isbn>",  methods=["GET"])
def api(isbn): 
    book_id,=db.execute("SELECT id FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    b = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    count = db.execute("SELECT COUNT(*) FROM reviews WHERE book_id = :book_id", {"book_id": book_id}).scalar()
    average = db.execute("SELECT AVG(score) FROM reviews WHERE book_id = :book_id", {"book_id": book_id}).scalar()
    aver= int(average)


    if book_id is None:
        return jsonify({"error": "That book is not in our database"}), 404
    else:   
        return jsonify({
        "title": b.title,
        "author": b.author,
        "year": b.year,
        "isbn": b.isbn,
        "review_count": count,
        "average_score": aver
        })
