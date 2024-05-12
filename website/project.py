import csv
import json
import math
import os
import shutil
import tempfile
from datetime import datetime

import pandas as pd
import plotly
import plotly.express as px
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, send_file
from ultralytics import YOLO

from . import socket, db
from .models import Image, Stats, MlModels, Batch
from .utils import load_img_as_np_array, get_annotated_image_from_prediction, \
    get_prediction_stats, add_batch_to_db, get_unique_wbc_class_names

project_views = Blueprint('project_views', __name__)
IMAGE_TABLE_MAX_ROWS_DISPLAY = 10
RUN_TAB = 1
STATS_TAB = 2
IMAGE_TAB = 3
BAR = "Bar"
PIE = "Pie"


@project_views.route("/project", methods=["GET", "POST"])
def project():
    if request.method == "POST":
        batch = Batch.query.filter_by(project_id=session["project_id"],
                                      name=request.form.get("batch-select")).first()
        session["batch_id"] = batch.id if batch is not None else -1
        session["batch_name"] = batch.name if batch is not None else "none"
        session["batch_stats"] = list(map(int, request.form.getlist("batch-stats-select")))
        session["plot_type"] = request.form.get("plot-type-select")
        session["wbc_class_names"] = request.form.getlist("wbc-class-select")
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

    return render_template("project.html", images=get_project_images(), stats=stats(), batches=get_batches(),
                           mlmodels=get_ml_models(), wbc_class_names=get_unique_wbc_class_names())


def get_project_images():
    images = Image.query.filter_by(project_id=session["project_id"],
                                   batch_id=session["batch_id"] if "batch_id" in session else -1)
    first_image_on_page = IMAGE_TABLE_MAX_ROWS_DISPLAY * (session["image_page"] - 1)
    last_image_on_page = first_image_on_page + IMAGE_TABLE_MAX_ROWS_DISPLAY
    session["total_rows"] = images.count()
    session["last_page"] = max(math.ceil(images.count() / IMAGE_TABLE_MAX_ROWS_DISPLAY), 1)
    return images[first_image_on_page:last_image_on_page]


def stats():
    if "batch_stats" in session and "plot_type" in session:
        images = db.session.query(Image).filter(Image.batch_id.in_(session["batch_stats"]),
                                                Image.project_id == session["project_id"])
        stats_query = (
            db
            .session
            .query(
                Stats.id,
                Stats.image_id,
                Stats.class_name,
                Image.batch_id,
                Batch.name.label("batch_name")
            )
            .join(
                Image,
                Stats.image_id == Image.id
            )
            .join(
                Batch,
                Image.batch_id == Batch.id
            )
            .filter(
                Stats.image_id.in_([image.id for image in images])
            )
            .filter(
                Stats.class_name.in_([x.lower() for x in session["wbc_class_names"]])
            )
        )
        df = pd.read_sql(stats_query.statement, db.engine)
        df['count'] = df.groupby(["class_name", "batch_name"])['id'].transform('count')
        df_for_plot = df.groupby(["class_name", "batch_name"]).agg({"count": "sum"}).reset_index()
        if session["plot_type"] == BAR:
            fig = px.bar(
                df_for_plot,
                x="class_name",
                y="count",
                color='batch_name',
                barmode='group',
                title="WBC class counts",
                template="plotly",
                text_auto=True
            )
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            return graphJSON
        elif session["plot_type"] == PIE:
            fig = px.pie(
                df_for_plot,
                values="count",
                names="class_name",
                facet_col='batch_name',
                facet_col_wrap=3,
                title="WBC class counts",
                template="plotly",
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            return graphJSON
    return None


def get_batches():
    batches = Batch.query.filter_by(project_id=session["project_id"])
    return batches


def get_ml_models():
    ml_models = MlModels.query.all()
    return ml_models


@project_views.route("/create_batch", methods=["POST"])
def create_batch():
    if request.method == "POST":
        add_batch_to_db(session["project_id"], batch_name=request.form.get("new-batch-name"))
        flash("Batch created!", category="success")
    return redirect(url_for("project_views.project", tab=3))


@project_views.route("/run", methods=["POST"])
async def run():
    if request.method == "POST":
        model = YOLO(MlModels.query.filter_by(name=request.form.get("model-select")).first().model)
        batch_ids = list(map(int, request.form.getlist("batch-run-select")))
        images_to_run = db.session.query(Image).filter(Image.batch_id.in_(batch_ids),
                                                       Image.project_id == session["project_id"])
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
            for class_id, class_name, box_coords in prediction_stats:
                new_stats = Stats(image_id=image.id, class_id=class_id, class_name=class_name, box_coords=box_coords)
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


@project_views.route("/delete_image", methods=["GET", "POST"])
def delete_image():
    if request.method == "POST":
        image_id_to_delete = list(map(int, request.form.getlist("images-checkbox")))
        if not image_id_to_delete:
            flash("No images selected", category="error")
        else:
            db.session.query(Image).filter(Image.id.in_(image_id_to_delete)).delete()
            db.session.commit()
            flash("Images successfully deleted", category="success")
    return redirect(url_for("project_views.project", tab=IMAGE_TAB))


@project_views.route("/delete_batch", methods=["GET", "POST"])
def delete_batch():
    if request.method == "POST":
        db.session.query(Batch).filter(Batch.id == session["batch_id"]).delete()
        db.session.commit()
        flash("Batch successfully deleted", category="success")
    return redirect(url_for("project_views.project", tab=IMAGE_TAB))


@project_views.route("/export", methods=["GET", "POST"])
def export():
    with tempfile.TemporaryDirectory() as tmp_dir:
        batch_ids = list(map(int, request.form.getlist("batch-export-select")))
        export_query = (
            db
            .session
            .query(
                Stats.id,
                Stats.class_id,
                Stats.box_coords,
                Stats.image_id,
                Image.image,
                Image.name,
                Image.batch_id
            )
            .join(
                Image,
                Stats.image_id == Image.id
            )
            .filter(
                Image.batch_id.in_(batch_ids)
            )
        )
        df = pd.read_sql(export_query.statement, db.engine)
        with open(os.path.join(tmp_dir, "classes.txt"), "a") as classes_file:
            model_names = YOLO(MlModels.query.filter_by(name="best.pt").first().model).names
            for names in model_names.values():
                classes_file.write(f"{names}\n")
        os.mkdir(os.path.join(tmp_dir, "images"))
        os.mkdir(os.path.join(tmp_dir, "labels"))
        for image_path, data in df.groupby("image"):
            shutil.copy(os.path.join("website", "static", image_path), os.path.join(tmp_dir, "images", image_path))
            data[["class_id", "box_coords"]].to_csv(
                os.path.join(tmp_dir, "labels", f"{os.path.splitext(image_path)[0]}.txt"), header=False,
                index=False, sep=" ", doublequote=False, escapechar=' ', quoting=csv.QUOTE_NONE)
        shutil.make_archive(tmp_dir, "zip", tmp_dir)
        return send_file(f"{tmp_dir}.zip", as_attachment=True, download_name="results.zip")
