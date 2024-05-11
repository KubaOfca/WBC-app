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


@home_views.route("/delete_project/", methods=["GET", "POST"])
def delete_project():
    if request.method == "POST":
        projects_id_to_delete = list(map(int, request.form.getlist("project-checkbox")))
        if not projects_id_to_delete:
            flash("No projects selected", category="error")
        else:
            db.session.query(Project).filter(Project.id.in_(projects_id_to_delete),
                                             Project.user_id == current_user.id).delete()
            db.session.commit()
            flash("Project successfully deleted", category="success")
    return redirect(url_for("home_views.home"))
