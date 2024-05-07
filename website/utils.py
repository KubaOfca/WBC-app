from datetime import datetime

from flask_login import current_user

from website import db
from website.models import Project


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
