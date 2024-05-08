from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_required, current_user

from . import db
from .models import Project
from .utils import get_user_projects, add_project_to_db

home_views = Blueprint('home_views', __name__)
IMAGE_TABLE_MAX_ROWS_DISPLAY = 10
RUN_TAB = 1
STATS_TAB = 2
IMAGE_TAB = 3


@home_views.route('/', methods=["GET", "POST"])
@login_required
def home():
    session["user_name"] = current_user.name
    if request.method == "POST":
        add_project_to_db(user_id=current_user.id, project_name=request.form.get("new-project-name"))
        flash("Project created!", category="success")
        return redirect(url_for("home_views.home"))  # redirect in order to close POST form (e.g. when refresh)
    return render_template("home.html", user_projects=get_user_projects())


@home_views.route("/delete_project/")
def delete_project():
    project_id = request.args.get("project_id", type=int)
    project_to_delete = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if project_to_delete:
        db.session.delete(project_to_delete)
        db.session.commit()
        flash("Project successfully deleted", category="success")
    return redirect(url_for("home_views.home"))
