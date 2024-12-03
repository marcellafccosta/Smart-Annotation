#database/auth.py

from flask import Blueprint, redirect, url_for, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from database.config import get_db
from database.user_crud import get_user_by_email, get_user_by_id

auth_bp = Blueprint('auth', __name__)
# Inicialize o LoginManager
login_manager = LoginManager()
login_manager.login_view = '/'

class User(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    db = next(get_db())
    user_db = get_user_by_id(db, int(user_id))
    if user_db:
        return User(user_db.id, user_db.name, user_db.email)
    return None

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = next(get_db())
        email = request.form["email"]
        password = request.form["password"]
        
        user_db = get_user_by_email(db, email)
        
        if user_db and user_db.password == password:
            user = User(user_db.id, user_db.name, user_db.email)
            login_user(user)
            return redirect("/profile")
        else:
            return "Invalid email or password."
    return redirect("/login")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")
