import json
import math
import os
from datetime import datetime

import pandas as pd
import plotly
import plotly.express as px
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from ultralytics import YOLO

from . import socket, db
from .models import Image, Stats, MlModels, Batch
from .utils import load_img_as_np_array, get_annotated_image_from_prediction, \
    get_prediction_stats, add_batch_to_db

project_views = Blueprint('project_views', __name__)
IMAGE_TABLE_MAX_ROWS_DISPLAY = 10
RUN_TAB = 1
STATS_TAB = 2
IMAGE_TAB = 3


@project_views.route("/project", methods=["GET", "POST"])
def project():
    if request.method == "POST":
        batch = Batch.query.filter_by(project_id=session["project_id"],
                                      name=request.form.get("batch-select")).first()
        session["batch_id"] = batch.id if batch is not None else -1
        session["batch_name"] = batch.name if batch is not None else "none"
    project_id = request.args.get("project_id", type=int)
    page = request.args.get("page", type=int)
    tab = request.args.get("tab", type=int)
    if project_id is not None:
        session["project_id"] = project_id
    if page is not None:
        if page < 1:
            session["image_page"] = 1
        elif "last_page" in session and page > session["last_page"]:
            session["image_page"] = session["last_page"]
        else:
            session["image_page"] = page
    if tab is not None:
        session["tab"] = tab

    return render_template("project.html", images=get_project_images(), stats=stats(), batches=get_batches())


def get_project_images():
    images = Image.query.filter_by(project_id=session["project_id"],
                                   batch_id=session["batch_id"] if "batch_id" in session else -1)
    print(session["batch_id"] if "batch_id" in session else 10)
    first_image_on_page = IMAGE_TABLE_MAX_ROWS_DISPLAY * (session["image_page"] - 1)
    last_image_on_page = first_image_on_page + IMAGE_TABLE_MAX_ROWS_DISPLAY
    session["total_rows"] = images.count()
    session["last_page"] = max(math.ceil(images.count() / IMAGE_TABLE_MAX_ROWS_DISPLAY), 1)
    return images[first_image_on_page:last_image_on_page]


@project_views.route("/stats")
def stats():
    images = Image.query.filter_by(project_id=session["project_id"])
    stats = Stats.query.filter(Stats.image_id.in_([image.id for image in images]))
    df = pd.read_sql(stats.statement, db.engine)
    fig1 = px.bar(df, x="class_name", y="count", title="WBC class counts")
    graph1JSON = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
    return graph1JSON


def get_batches():
    batches = Batch.query.filter_by(project_id=session["project_id"])
    return batches


@project_views.route("/create_batch", methods=["POST"])
def create_batch():
    if request.method == "POST":
        add_batch_to_db(session["project_id"], batch_name=request.form.get("new-batch-name"))
        flash("Batch created!", category="success")
    return redirect(url_for("project_views.project", tab=3))


@project_views.route("/run", methods=["POST"])
async def run():
    model = YOLO(MlModels.query.first().model)
    images_to_run = Image.query.filter_by(project_id=session["project_id"])
    n_images_to_run = images_to_run.count()
    if not n_images_to_run:
        flash("No images to run model", category="error")
        return redirect(url_for("project_views.project", tab=RUN_TAB))
    progress_bar_step_size = 100 / n_images_to_run
    progress_bar_step = 0
    for image in images_to_run:
        img_array = load_img_as_np_array(image.image)
        prediction = model.predict(img_array, stream=False, save=False, verbose=False)
        progress_bar_step += progress_bar_step_size
        socket.emit("update progress", int(math.ceil(progress_bar_step)))
        annotated_image = get_annotated_image_from_prediction(prediction)
        annotated_image.save(os.path.join(
            "website",
            "static",
            f"annotated_{image.name}",
        ))
        image.annotated_image = f"annotated_{image.name}"
        db.session.commit()
        prediction_stats = get_prediction_stats(prediction)
        existing_stats = db.session.query(Stats).filter(Stats.image_id == image.id)
        if existing_stats is not None:
            existing_stats.delete()
            db.session.commit()
        for key, value in prediction_stats.items():
            new_stats = Stats(image_id=image.id, class_name=key, count=value)
            db.session.add(new_stats)
            db.session.commit()
    flash("Model successfully run", category="success")
    db.session.close()
    return redirect(url_for("project_views.project", tab=STATS_TAB))


@project_views.route("/upload_images", methods=["POST"])
async def upload_images():
    if "images[]" not in request.files:
        flash("No file part", category="error")
        return redirect(url_for("project_views.project"))

    images = request.files.getlist("images[]")
    progress_bar_step_size = 100 / len(images)
    progress_bar_step = 0
    for image in images:
        if image.filename == "":
            flash("No selected file", category="error")
            continue
        if image and allowed_file(image.filename):
            new_image = Image(
                project_id=session["project_id"],
                batch_id=session["batch_id"],
                name=image.filename,
                image=image.filename,
                date=datetime.now(),
            )
            image.save(
                os.path.join(
                    "website",
                    "static",
                    image.filename,
                )
            )
            db.session.add(new_image)
            db.session.commit()
            progress_bar_step += progress_bar_step_size
            socket.emit("update upload progress", int(math.ceil(progress_bar_step)))
        else:
            flash("Invalid file format", category="error")

    flash("Images uploaded successfully", category="success")
    return redirect(url_for("project_views.project", tab=IMAGE_TAB))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'bmp'}


@project_views.route("/delete_image/")
def delete_image():
    image_id = request.args.get("image_id", type=int)
    image_to_delete = Image.query.filter_by(id=image_id).first()
    if image_to_delete:
        db.session.delete(image_to_delete)
        db.session.commit()
        flash("Image successfully deleted", category="success")
    return redirect(url_for("project_views.project", tab=IMAGE_TAB))
