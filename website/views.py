import base64
from datetime import datetime

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from . import db
from .models import Project, Image

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
    images = Image.query.filter_by(project_id=project_id)
    images_png = []
    for image in images:
        images_png.append(base64.b64encode(image.image).decode('ascii'))
    return render_template("project.html", project_id=project_id, images=list(zip(images, images_png)))


@views.route("/upload_images/<int:project_id>", methods=["POST"])
def upload_images(project_id):
    if "images[]" not in request.files:
        print("t")
        flash("No file part", category="error")
        return redirect(url_for("views.project_page", project_id=project_id))

    images = request.files.getlist("images[]")
    for image in images:
        if image.filename == "":
            flash("No selected file", category="error")
            continue
        if image and allowed_file(image.filename):
            new_image = Image(project_id=project_id, name=image.filename, image=image.read(), date=datetime.now())
            db.session.add(new_image)
            db.session.commit()
        else:
            flash("Invalid file format", category="error")

    flash("Images uploaded successfully", category="success")

    return redirect(url_for("views.project_page", project_id=project_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}


@views.route("/delete_image/<int:image_id>")
def delete_image(image_id):
    image_to_delete = Image.query.filter_by(id=image_id).first()
    project_id = image_to_delete.project_id
    if image_to_delete:
        db.session.delete(image_to_delete)
        db.session.commit()
        flash("Image successfully deleted", category="success")
    return redirect(url_for("views.project_page", project_id=project_id))
