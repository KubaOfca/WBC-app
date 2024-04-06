from flask import Blueprint, render_template
from flask_login import login_required, current_user

views = Blueprint('views', __name__)


@views.route('/')
@login_required
def home():
    user_name = current_user.first_name
    return render_template("home.html", user_name=user_name)
