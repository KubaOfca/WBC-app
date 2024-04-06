from base64 import b64encode
from io import BytesIO

import pyotp
import qrcode
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from . import db
from .models import User

auth = Blueprint('auth', __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("auth.verify_mfa"))
        flash("Wrong password or email", category="error")
    return render_template("login.html")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if request.method == "POST":
        email = request.form.get("email")
        first_name = request.form.get("firstName")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        if len(email) < 4:
            flash("Wrong email", category="error")
        elif len(first_name) < 2:
            flash("Wrong name", category="error")
        elif password1 != password2:
            flash("Wrong password", category="error")
        else:
            password_hash = generate_password_hash(password1)
            new_user = User(
                email=email,
                first_name=first_name,
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
        user_id = session["user_id"]
        user = User.query.filter_by(id=user_id).first()
        secret_key = user.secret_key
        if secret_key:
            url = pyotp.totp.TOTP(secret_key).provisioning_uri(
                name=user.first_name, issuer_name="WBC_Scan")
            qrcode_handle = qrcode.QRCode(version=1, box_size=10, border=5)
            qrcode_handle.add_data(url)
            qrcode_img = qrcode_handle.make_image(fill_color='black', back_color='white')
            buffered = BytesIO()
            qrcode_img.save(buffered)
            qrcode_imgb64 = b64encode(buffered.getvalue()).decode("utf-8")
            return render_template("mfa_template.html", qr_image=qrcode_imgb64)
    return redirect(url_for("auth.sign_up"))


@auth.route("/verify_mfa", methods=["GET", "POST"])
def verify_mfa():
    if "user_id" in session.keys():
        user_id = session["user_id"]
        user = User.query.filter_by(id=user_id).first()
        secret_key = user.secret_key
        if request.method == "POST":
            mfa_key = request.form.get("mfa")
            totp = pyotp.TOTP(secret_key)
            if totp.verify(mfa_key):
                flash("Successful Login!", category="success")
                login_user(user, remember=True)
                return redirect(url_for("views.home"))
    return render_template("verify-mfa.html")
