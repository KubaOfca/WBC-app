import base64
import math
from datetime import datetime
from io import BytesIO

import numpy as np
from PIL import Image as PILImage
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from ultralytics import YOLO

from . import db, socket
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
    page = request.args.get("page", 1, type=int)
    tab = request.args.get("tab", 1, type=int)
    print(tab)
    page_len = 10
    start = (page - 1) * page_len
    end = page * page_len

    images = Image.query.filter_by(project_id=project_id)
    images_len = images.count()
    last_page_number = math.ceil(images_len / page_len)
    images_png = []
    for image in images[start:end]:
        images_png.append(base64.b64encode(image.image).decode('ascii'))
    images_full_info = list(zip(images[start:end], images_png))

    return render_template("project.html", project_id=project_id, images=images_full_info, page=page,
                           last_page_number=last_page_number, images_len=images_len, tab=tab)


@views.route("/upload_images/<int:project_id>", methods=["POST"])
def upload_images(project_id):
    tab = request.args.get("tab", 1, type=int)
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

    return redirect(url_for("views.project_page", project_id=project_id, tab=tab))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'bmp'}


@views.route("/delete_image/<int:image_id>")
def delete_image(image_id):
    tab = request.args.get("tab", 1, type=int)
    image_to_delete = Image.query.filter_by(id=image_id).first()
    project_id = image_to_delete.project_id
    if image_to_delete:
        db.session.delete(image_to_delete)
        db.session.commit()
        flash("Image successfully deleted", category="success")
    return redirect(url_for("views.project_page", project_id=project_id, tab=tab))


@views.route("/run/<int:project_id>", methods=["POST"])
async def run_model(project_id):
    model = YOLO(r"C:\Users\Jakub Lechowski\Desktop\master-thesis\code\best.pt")
    images_to_run = Image.query.filter_by(project_id=project_id)
    n_images = images_to_run.count()
    step = 100 / n_images
    progress = 0
    for image in images_to_run:
        image_byte = image.image
        img_pil = PILImage.open(BytesIO(image_byte))
        img_np = np.array(img_pil)
        prediction = model.predict(img_np, stream=False, save=False, verbose=False)
        progress += step
        socket.emit("update progress", int(math.ceil(progress)))
        pill_result = PILImage.fromarray(prediction[0].plot()[..., ::-1])
        buff = BytesIO()
        pill_result.save(buff, format="PNG")
        buff.seek(0)
        encoded = base64.b64encode(buff.read()).decode("utf-8")
        image_bytes = base64.b64decode(encoded)
        image.image = image_bytes
        db.session.commit()
    flash("Model successfully run", category="success")
    db.session.close()
    return redirect(url_for("views.project_page", project_id=project_id, tab=1))


@views.route("/show_image/<int:image_id>")
def show_image(image_id):
    img = Image.query.filter_by(id=image_id).first()
    file_type = img.name.split(".")[-1]
    return Response(img.image, mimetype=file_type)
