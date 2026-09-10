"""
=============================================
  Notifications routes
  GET  /notifications
  POST /api/notifications/mark-read
  POST /api/notifications/dismiss
  POST /api/notifications/mark-all-read
  POST /api/notifications/clear-all
=============================================
"""

from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from config.database import get_db

notifications_bp = Blueprint("notifications", __name__)


def _ensure_table():
    """Create notifications table if it doesn't exist."""
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id    INT UNSIGNED NOT NULL,
            type       ENUM('info','success','warning','error') NOT NULL DEFAULT 'info',
            title      VARCHAR(150) NOT NULL,
            message    TEXT NOT NULL,
            is_read    TINYINT(1)   NOT NULL DEFAULT 0,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cursor.close()
    conn.close()


# ── Page ──────────────────────────────────────
@notifications_bp.route("/notifications")
def notifications_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    _ensure_table()
    user_id   = session["user_id"]
    user_name = session.get("user_name", "User")

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,)
    )
    notifications = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("notifications.html",
                           notifications=notifications,
                           user_name=user_name)


# ── Mark single as read ───────────────────────
@notifications_bp.route("/api/notifications/mark-read", methods=["POST"])
def mark_read():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    notif_id = request.form.get("id")
    user_id  = session["user_id"]

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read=1 WHERE id=%s AND user_id=%s",
        (notif_id, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})


# ── Dismiss (delete) single ───────────────────
@notifications_bp.route("/api/notifications/dismiss", methods=["POST"])
def dismiss():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    notif_id = request.form.get("id")
    user_id  = session["user_id"]

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM notifications WHERE id=%s AND user_id=%s",
        (notif_id, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})


# ── Mark all as read ──────────────────────────
@notifications_bp.route("/api/notifications/mark-all-read", methods=["POST"])
def mark_all_read():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read=1 WHERE user_id=%s",
        (session["user_id"],)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})


# ── Clear all ─────────────────────────────────
@notifications_bp.route("/api/notifications/clear-all", methods=["POST"])
def clear_all():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM notifications WHERE user_id=%s",
        (session["user_id"],)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})
