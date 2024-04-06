from datetime import datetime

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from . import db
from .models import Project

views = Blueprint('views', __name__)


@views.route('/', methods=["GET", "POST"])
@login_required
def home():
    user_name = current_user.first_name
    active_projects = Project.query.filter_by(user_id=current_user.id)
    if request.method == "POST":
        project_name = request.form.get("project-name")
        new_project = Project(
            user_id=current_user.id,
            name=project_name,
            date=datetime.now()
        )
        db.session.add(new_project)
        db.session.commit()
        flash("Project created!", category="success")
        return redirect(url_for("views.home"))  # redirect to close POST when refresh
    return render_template("home.html", user_name=user_name, projects=active_projects)


@views.route("/delete_project/<int:project_id>")
def delete_project(project_id):
    project_to_delete = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if project_to_delete:
        db.session.delete(project_to_delete)
        db.session.commit()
        flash("Project successfully deleted", category="success")
    return redirect(url_for("views.home"))


@views.route("/project_page/<int:project_id>")
def project_page(project_id):
    return render_template("project.html")
