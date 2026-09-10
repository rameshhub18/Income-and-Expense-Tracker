"""
=============================================
  Auth routes — /register  /login  /logout
=============================================
"""

import re
import bcrypt
from flask import (Blueprint, render_template, request,
                   redirect, url_for, session, flash)
from config.database import get_db
from routes.notify import push, ensure_table

auth_bp = Blueprint("auth", __name__)


# ── Landing page ──────────────────────────────
@auth_bp.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("index.html")


# ── Register ──────────────────────────────────
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))

    errors  = []
    success = ""
    old     = {"full_name": "", "email": ""}

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email     = request.form.get("email",     "").strip()
        password  = request.form.get("password",  "")
        confirm   = request.form.get("confirm",   "")

        # Validation
        if len(full_name) < 2:
            errors.append("Full name must be at least 2 characters.")
        elif not re.match(r"^[a-zA-Z\s\-']+$", full_name):
            errors.append("Full name can only contain letters, spaces, hyphens, and apostrophes. Numbers are not allowed.")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            errors.append("Please enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if not errors:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (email,))
            if cursor.fetchone():
                errors.append("An account with this email already exists.")
            else:
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                cursor.execute(
                    "INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)",
                    (full_name, email, hashed)
                )
                conn.commit()
                new_user_id = cursor.lastrowid
                success = "Account created! You can now log in."
                old = {"full_name": "", "email": ""}

                # Welcome notification
                ensure_table(conn)
                push(conn, new_user_id, "success",
                     "Welcome to Dhan Flow!",
                     f"Hi {full_name}! Your account was created successfully. "
                     "Start by adding your first transaction or setting a budget goal.")

            cursor.close()
            conn.close()

        if errors:
            old = {"full_name": full_name, "email": email}

    return render_template("register.html",
                           errors=errors, success=success, old=old)


# ── Login ─────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))

    error     = ""
    old_email = ""

    if request.method == "POST":
        email    = request.form.get("email",    "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            error = "Please fill in all fields."
        elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            error = "Invalid email address."
        else:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, full_name, password FROM users WHERE email = %s LIMIT 1",
                (email,)
            )
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
                session.clear()
                session["user_id"]   = user["id"]
                session["user_name"] = user["full_name"]

                # Login notification
                from datetime import datetime
                conn2 = get_db()
                ensure_table(conn2)
                push(conn2, user["id"], "info",
                     "New Login",
                     f"You logged in on {datetime.now().strftime('%b %d, %Y at %I:%M %p')}.")
                conn2.close()

                return redirect(url_for("dashboard.dashboard"))
            else:
                error = "Incorrect email or password."

        old_email = email

    return render_template("login.html", error=error, old_email=old_email)


# ── Logout ────────────────────────────────────
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
