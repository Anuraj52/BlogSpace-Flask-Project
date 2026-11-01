
import os
from datetime import datetime

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager, UserMixin, current_user, login_required,
    login_user, logout_user
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import EmailField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "info"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    posts = db.relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = db.relationship("Comment", back_populates="author", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)

    posts = db.relationship("Post", back_populates="category")


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)

    author = db.relationship("User", back_populates="posts")
    category = db.relationship("Category", back_populates="posts")
    comments = db.relationship("Comment", back_populates="post", cascade="all, delete-orphan")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)

    author = db.relationship("User", back_populates="comments")
    post = db.relationship("Post", back_populates="comments")


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=40)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")]
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    submit = SubmitField("Create account")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError("That username is already taken.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("That email is already registered.")


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class PostForm(FlaskForm):
    title = StringField("Post title", validators=[DataRequired(), Length(max=160)])
    category = StringField("Category", validators=[DataRequired(), Length(max=60)])
    content = TextAreaField("Content", validators=[DataRequired(), Length(min=10)])
    submit = SubmitField("Publish post")


class CommentForm(FlaskForm):
    content = TextAreaField("Write a comment", validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField("Add comment")


class EmptyForm(FlaskForm):
    submit = SubmitField("Confirm")


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    database_url = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(app.instance_path, "blogspace.db")
    )

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-secret-key"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        POSTS_PER_PAGE=5,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Automatically create database tables
    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_forms():
        return {"logout_form": EmptyForm()}

    @app.route("/")
    def index():
        search = request.args.get("q", "").strip()
        category_id = request.args.get("category", type=int)
        page = request.args.get("page", 1, type=int)

        query = Post.query

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                db.or_(Post.title.ilike(pattern), Post.content.ilike(pattern))
            )

        if category_id:
            query = query.filter(Post.category_id == category_id)

        pagination = query.order_by(Post.created_at.desc()).paginate(
            page=page,
            per_page=app.config["POSTS_PER_PAGE"],
            error_out=False
        )

        categories = Category.query.order_by(Category.name.asc()).all()

        return render_template(
            "index.html",
            pagination=pagination,
            posts=pagination.items,
            categories=categories,
            q=search,
            selected_category=category_id
        )

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        form = RegisterForm()

        if form.validate_on_submit():
            user = User(
                username=form.username.data.strip(),
                email=form.email.data.strip().lower()
            )
            user.set_password(form.password.data)

            db.session.add(user)
            db.session.commit()

            login_user(user)
            flash("Your account has been created.", "success")

            return redirect(url_for("index"))

        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        form = LoginForm()

        if form.validate_on_submit():
            user = User.query.filter_by(
                email=form.email.data.strip().lower()
            ).first()

            if user and user.check_password(form.password.data):
                login_user(user)
                flash("Welcome back!", "success")

                next_page = request.args.get("next")

                if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                    return redirect(next_page)

                return redirect(url_for("index"))

            flash("Email or password is incorrect.", "error")

        return render_template("login.html", form=form)

    @app.post("/logout")
    @login_required
    def logout():
        form = EmptyForm()

        if form.validate_on_submit():
            logout_user()
            flash("You have been logged out.", "info")

        return redirect(url_for("index"))

    @app.route("/post/new", methods=["GET", "POST"])
    @login_required
    def new_post():
        form = PostForm()

        if form.validate_on_submit():
            category_name = form.category.data.strip()

            category = Category.query.filter(
                db.func.lower(Category.name) == category_name.lower()
            ).first()

            if category is None:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.flush()

            post = Post(
                title=form.title.data.strip(),
                content=form.content.data.strip(),
                category=category,
                author=current_user
            )

            db.session.add(post)
            db.session.commit()

            flash("Your post has been published.", "success")

            return redirect(url_for("post_detail", post_id=post.id))

        return render_template("post_form.html", form=form, post=None)

    @app.route("/post/<int:post_id>")
    def post_detail(post_id):
        post = db.get_or_404(Post, post_id)
        form = CommentForm()
        delete_form = EmptyForm()

        return render_template(
            "post_detail.html",
            post=post,
            form=form,
            delete_form=delete_form
        )

    @app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_post(post_id):
        post = db.get_or_404(Post, post_id)

        if post.user_id != current_user.id:
            abort(403)

        form = PostForm(obj=post)

        if request.method == "GET":
            form.category.data = post.category.name

        if form.validate_on_submit():
            category_name = form.category.data.strip()

            category = Category.query.filter(
                db.func.lower(Category.name) == category_name.lower()
            ).first()

            if category is None:
                category = Category(name=category_name)
                db.session.add(category)
                db.session.flush()

            post.title = form.title.data.strip()
            post.content = form.content.data.strip()
            post.category = category

            db.session.commit()

            flash("Your post has been updated.", "success")

            return redirect(url_for("post_detail", post_id=post.id))

        return render_template("post_form.html", form=form, post=post)

    @app.post("/post/<int:post_id>/delete")
    @login_required
    def delete_post(post_id):
        post = db.get_or_404(Post, post_id)

        if post.user_id != current_user.id:
            abort(403)

        form = EmptyForm()

        if form.validate_on_submit():
            db.session.delete(post)
            db.session.commit()
            flash("Post deleted.", "info")

        return redirect(url_for("index"))

    @app.post("/post/<int:post_id>/comment")
    @login_required
    def add_comment(post_id):
        post = db.get_or_404(Post, post_id)
        form = CommentForm()

        if form.validate_on_submit():
            comment = Comment(
                content=form.content.data.strip(),
                author=current_user,
                post=post
            )

            db.session.add(comment)
            db.session.commit()

            flash("Your comment has been added.", "success")
        else:
            flash("Please enter a valid comment.", "error")

        return redirect(url_for("post_detail", post_id=post.id))

    @app.route("/user/<int:user_id>")
    def profile(user_id):
        user = db.get_or_404(User, user_id)
        page = request.args.get("page", 1, type=int)

        pagination = Post.query.filter_by(
            user_id=user.id
        ).order_by(Post.created_at.desc()).paginate(
            page=page,
            per_page=app.config["POSTS_PER_PAGE"],
            error_out=False
        )

        return render_template(
            "profile.html",
            profile_user=user,
            posts=pagination.items,
            pagination=pagination
        )

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "error.html",
            code=403,
            message="You do not have permission to do that."
        ), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "error.html",
            code=404,
            message="The page you requested was not found."
        ), 404

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
