import re
from base64 import b64encode
from io import BytesIO

import pyotp
import qrcode
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from . import db
from .models import User

EMAIL_VALIDATOR_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'

auth = Blueprint('auth', __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        password = request.form.get("password")
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("auth.verify_mfa"))
        flash("Wrong password or email", category="error")
    return render_template("login.html")


@auth.route("/verify_mfa", methods=["GET", "POST"])
def verify_mfa():
    if "user_id" in session.keys():
        user = User.query.filter_by(id=session["user_id"]).first()
        secret_key = user.secret_key
        if request.method == "POST":
            mfa_key = request.form.get("mfa")
            totp = pyotp.TOTP(secret_key)
            if totp.verify(mfa_key):
                login_user(user, remember=True)
                flash("Successful Login!", category="success")
                return redirect(url_for("views.home"))
            else:
                flash("Wrong MFA code", category="error")
    return render_template("verify-mfa.html")


@auth.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("firstName")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if re.match(EMAIL_VALIDATOR_REGEX, email):
            flash("Email address is not valid", category="error")
        elif name is None:
            flash("Name cannot be empty", category="error")
        elif len(password1) < 8:
            flash("Password should be at least 8 characters long", category="error")
        elif password1 != password2:
            flash("Passwords do not match", category="error")
        else:
            password_hash = generate_password_hash(password1)
            new_user = User(
                email=email,
                name=name,
                password=password_hash,
                secret_key=pyotp.random_base32(),
            )
            db.session.add(new_user)
            db.session.commit()
            session["user_id"] = new_user.id
            flash("Account created!", category="success")
            return redirect(url_for("auth.mfa_setup"))
    return render_template("signup.html")


@auth.route("/mfa_setup")
def mfa_setup():
    if "user_id" in session.keys():
        user = User.query.filter_by(id=session["user_id"]).first()
        secret_key = user.secret_key
        if secret_key:
            url = pyotp.totp.TOTP(secret_key).provisioning_uri(
                name=user.name, issuer_name="WBC_Scan")
            return render_template("mfa_setup.html", qr_image=_get_qr_code_to_setup_mfa(url))
    return redirect(url_for("auth.sign_up"))


def _get_qr_code_to_setup_mfa(url: str):
    qrcode_handle = qrcode.QRCode(version=1, box_size=10, border=5)
    qrcode_handle.add_data(url)
    qrcode_img = qrcode_handle.make_image(fill_color='black', back_color='white')
    buffered = BytesIO()
    qrcode_img.save(buffered)
    qrcode_imgb64 = b64encode(buffered.getvalue()).decode("utf-8")
    return qrcode_imgb64


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Successful Logout!", category="success")
    return redirect(url_for("auth.login"))
