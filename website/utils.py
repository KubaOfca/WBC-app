import os
from datetime import datetime
from typing import List

import numpy as np
from PIL import Image as PILImage
from flask_login import current_user

from website import db
from website.models import Project, Batch, Stats


def get_user_projects():
    return Project.query.filter_by(user_id=current_user.id)


def add_project_to_db(user_id: int, project_name: str) -> None:
    new_project = Project(
        user_id=user_id,
        name=project_name,
        date=datetime.now()
    )
    db.session.add(new_project)
    db.session.commit()


def add_batch_to_db(project_id: int, batch_name: str):
    new_batch = Batch(
        project_id=project_id,
        name=batch_name,
    )
    db.session.add(new_batch)
    db.session.commit()


def load_img_as_np_array(image_path: str) -> np.array:
    return np.array(PILImage.open(os.path.join("website", "static", image_path)))


def get_annotated_image_from_prediction(prediction) -> PILImage.Image:
    return PILImage.fromarray(prediction[0].plot()[..., ::-1])


def get_prediction_stats(prediction):
    classes_id_to_names_map = prediction[0].names
    prediction_class_ids = prediction[0].boxes.cls
    stats: List = []
    for n, prediction_class_id in enumerate(prediction_class_ids):
        class_name = classes_id_to_names_map[int(prediction_class_id)].replace(" ", "_").lower()
        box_coords_tensor = prediction[0].boxes.xywhn[n]
        box_coords_str = " ".join([str(float(x)) for x in box_coords_tensor])
        stats.append([int(prediction_class_id), class_name, box_coords_str])
    return stats


def get_unique_wbc_class_names():
    return [x[0].capitalize() for x in db.session.query(Stats.class_name).distinct()]
