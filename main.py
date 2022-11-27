from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap
from wtforms import StringField, IntegerField, SubmitField, HiddenField
from wtforms.validators import DataRequired, NumberRange, URL
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor, CKEditorField
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterUser, LoginUser, UserComment
from flask_gravatar import Gravatar
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Table, Column, Integer, ForeignKey
from functools import wraps
import requests
import smtplib
import os
from dotenv import load_dotenv
import datetime


# PREPARE ENV
load_dotenv()

SMTP_GMAIL = os.getenv("SMTP_GMAIL")

GMAIL_EMAIL1 = os.getenv("GMAIL_EMAIL1")
GMAIL_PASSWORD1 = os.getenv("GMAIL_PASSWORD1")

GMAIL_EMAIL2 = os.getenv("GMAIL_EMAIL2")
GMAIL_PASSWORD2 = os.getenv("GMAIL_PASSWORD2")


# PREPARE APP
app = Flask(__name__)
app.app_context().push()
db = SQLAlchemy(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
bootstrap = Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)


# LOGIN MANAGER
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# ADMIN MANAGER
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function



# POSTS MODEL
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


# USERS MODEL
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship('Comment', back_populates="author")


# COMMENTS MODEL
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    date = db.Column(db.String(250), nullable=False)

with app.app_context():
    db.create_all()


# GRAVATAR SETTINGS
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# NAVIGATION

@app.route("/")
def home():
    entries = db.session.query(BlogPost).all()

    return render_template("index.html", page="home", entries=entries, head="reg", logged_in=current_user.is_authenticated)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterUser()
    if request.method == "POST":
        email = request.form['email']
        if User.query.filter_by(email=email).first():
            flash("You have already made an account. Please login.")
            return redirect(url_for('login'))
        user = User()
        user.name = request.form['name']
        user.email = email
        user.password = generate_password_hash(request.form['password'], method='pbkdf2:sha256', salt_length=8)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('home'))

    return render_template("register.html", form=form, page="about", head="reg", logged_in=current_user.is_authenticated)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginUser()
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        try:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('home'))
            else:
                print("Wrong Password")
                error = "Incorrect Password"
                return render_template("login.html", form=form, page="about", head="reg", logged_in=current_user.is_authenticated, error=error)
        except AttributeError:
            print("Wrong Email")
            error = "That email is not in our database."
            return render_template("login.html", form=form, page="about", head="reg", logged_in=current_user.is_authenticated, error=error)

    return render_template("login.html", form=form, page="about", head="reg", logged_in=current_user.is_authenticated)



@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/about")
def about():
    return render_template("about.html", page="about", head="reg", logged_in=current_user.is_authenticated)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "GET":
        return render_template("contact.html", page="contact", head="reg", logged_in=current_user.is_authenticated)
    elif request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        message = request.form["message"]
        with smtplib.SMTP(SMTP_GMAIL) as connection:
            connection.starttls()
            connection.login(user=GMAIL_EMAIL1, password=GMAIL_PASSWORD1)
            connection.sendmail(
                from_addr=GMAIL_EMAIL1,
                to_addrs=GMAIL_EMAIL2,
                msg= f"Subject:💫 Western Star Message!\n\nFrom: {name}\nEmail: {email}\nPhone:"
                     f" {phone}\n\n{message}".encode('utf-8')
            )
        print(name, email, phone, message)
        return render_template("contact.html", page="contact", head="sent", logged_in=current_user.is_authenticated)


@app.route('/post/<num>', methods=["GET", "POST"])
def post(num):

    form = UserComment()
    post_selected = BlogPost.query.get(int(num))
    comments = Comment.query.filter_by(parent_post=post_selected).all()
    print(comments)
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You must log in to comment.")
            return redirect(url_for('login'))
        now = datetime.datetime.now()
        date_time_string = now.strftime("%B %d, %Y")
        new_comment = Comment(
            text=form.comment.data,
            author=current_user,
            parent_post=post_selected,
            date=date_time_string
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(f'/post/{num}')

    return render_template("post.html", form=form, page="post", this_entry=post_selected, comments=comments,
                           head="reg", logged_in=current_user.is_authenticated)



# POST MANAGEMENT

@app.route('/new-post', methods=["GET", "POST"])
@admin_only
def new_post():
    form = CreatePostForm()
    if request.method == "POST":
        now = datetime.datetime.now()
        date_time_string = now.strftime("%B %d, %Y")
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            date=date_time_string,
            body=form.body.data,
            author=current_user,
            img_url=form.img_url.data
        )
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for('home'))

    return render_template("make-post.html", form=form, page=contact, head="reg", page_version="New Post", logged_in=current_user.is_authenticated)


@app.route('/edit-post/<num>', methods=["GET", "POST"])
@admin_only
def edit_post(num):
    post = BlogPost.query.get(int(num))
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if request.method == "POST":
        post.title=edit_form.title.data
        post.subtitle=edit_form.subtitle.data
        post.body=edit_form.body.data
        post.author=current_user
        post.img_url=edit_form.img_url.data
        db.session.commit()
        return render_template("post.html", page="post", this_entry=post, head="reg", logged_in=current_user.is_authenticated)

    return render_template("make-post.html", form=edit_form, page=contact, head="reg", page_version="Edit Post", logged_in=current_user.is_authenticated)


@app.route("/delete")
@admin_only
def delete():
    post_id = request.args.get('id')
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for("home"))




if __name__ == "__main__":
    app.run(debug=True)
