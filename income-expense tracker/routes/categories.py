"""
=============================================
  Categories routes
  GET  /categories
  POST /api/categories/add
  POST /api/categories/edit
  POST /api/categories/delete
=============================================
"""

from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from config.database import get_db
from routes.notify import push, ensure_table

categories_bp = Blueprint("categories", __name__)

ICONS = [
    "ri-money-dollar-circle-line", "ri-shopping-cart-2-line", "ri-car-line",
    "ri-home-line", "ri-heart-pulse-line", "ri-gamepad-line", "ri-plane-line",
    "ri-restaurant-line", "ri-book-line", "ri-shirt-line", "ri-wifi-line",
    "ri-lightbulb-line", "ri-gift-line", "ri-briefcase-line", "ri-bank-line",
    "ri-pie-chart-line", "ri-bar-chart-line", "ri-wallet-3-line",
]

COLORS = [
    "#2563eb", "#10b981", "#f59e0b", "#ef4444", "#6366f1",
    "#14b8a6", "#f97316", "#8b5cf6", "#ec4899", "#06b6d4",
]


def _ensure_cat_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id    INT UNSIGNED NOT NULL,
            name       VARCHAR(80)  NOT NULL,
            type       ENUM('income','expense','both') NOT NULL DEFAULT 'both',
            icon       VARCHAR(80)  NOT NULL DEFAULT 'ri-price-tag-3-line',
            color      VARCHAR(20)  NOT NULL DEFAULT '#2563eb',
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_user_cat (user_id, name),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cursor.close()


def _seed_defaults(user_id, conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS c FROM categories WHERE user_id=%s", (user_id,))
    if cursor.fetchone()[0] == 0:
        defaults = [
            (user_id, "Salary",        "income",  "ri-money-dollar-circle-line", "#10b981"),
            (user_id, "Freelance",     "income",  "ri-briefcase-line",           "#2563eb"),
            (user_id, "Food",          "expense", "ri-restaurant-line",          "#f59e0b"),
            (user_id, "Transport",     "expense", "ri-car-line",                 "#6366f1"),
            (user_id, "Shopping",      "expense", "ri-shopping-cart-2-line",     "#ec4899"),
            (user_id, "Bills",         "expense", "ri-lightbulb-line",           "#ef4444"),
            (user_id, "Health",        "expense", "ri-heart-pulse-line",         "#14b8a6"),
            (user_id, "Entertainment", "expense", "ri-gamepad-line",             "#f97316"),
            (user_id, "Other",         "both",    "ri-price-tag-3-line",         "#8b5cf6"),
        ]
        cursor.executemany(
            "INSERT IGNORE INTO categories (user_id,name,type,icon,color) VALUES (%s,%s,%s,%s,%s)",
            defaults
        )
        conn.commit()
    cursor.close()


# ── Page ──────────────────────────────────────
@categories_bp.route("/categories")
def categories_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id   = session["user_id"]
    user_name = session.get("user_name", "User")

    conn = get_db()
    _ensure_cat_table(conn)
    ensure_table(conn)
    _seed_defaults(user_id, conn)

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.*,
               COUNT(t.id)               AS tx_count,
               COALESCE(SUM(t.amount),0) AS tx_total
        FROM categories c
        LEFT JOIN transactions t ON t.category = c.name AND t.user_id = c.user_id
        WHERE c.user_id = %s
        GROUP BY c.id
        ORDER BY c.name
    """, (user_id,))
    categories = cursor.fetchall()

    income_cats  = [c for c in categories if c["type"] in ("income", "both")]
    expense_cats = [c for c in categories if c["type"] in ("expense", "both")]

    cursor.close()
    conn.close()

    return render_template("categories.html",
        user_name    = user_name,
        categories   = categories,
        income_cats  = income_cats,
        expense_cats = expense_cats,
        icons        = ICONS,
        colors       = COLORS,
    )


# ── Add ───────────────────────────────────────
@categories_bp.route("/api/categories/add", methods=["POST"])
def add_category():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    name  = request.form.get("name",  "").strip()
    ctype = request.form.get("type",  "both").strip()
    icon  = request.form.get("icon",  "ri-price-tag-3-line").strip()
    color = request.form.get("color", "#2563eb").strip()

    if not name:
        return jsonify({"success": False, "message": "Name is required."})

    conn = get_db()
    _ensure_cat_table(conn)
    ensure_table(conn)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO categories (user_id,name,type,icon,color) VALUES (%s,%s,%s,%s,%s)",
            (session["user_id"], name, ctype, icon, color)
        )
        conn.commit()
        new_id = cursor.lastrowid
    except Exception:
        cursor.close(); conn.close()
        return jsonify({"success": False, "message": "Category already exists."})

    cursor.close()
    push(conn, session["user_id"], "success",
         f"Category Created: {name}",
         f"New {ctype} category '{name}' was added to your account.")
    conn.close()
    return jsonify({"success": True, "id": new_id})


# ── Edit ──────────────────────────────────────
@categories_bp.route("/api/categories/edit", methods=["POST"])
def edit_category():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        cat_id = int(request.form.get("id", 0))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid ID."})

    name  = request.form.get("name",  "").strip()
    ctype = request.form.get("type",  "both").strip()
    icon  = request.form.get("icon",  "ri-price-tag-3-line").strip()
    color = request.form.get("color", "#2563eb").strip()

    conn   = get_db()
    ensure_table(conn)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE categories SET name=%s, type=%s, icon=%s, color=%s WHERE id=%s AND user_id=%s",
        (name, ctype, icon, color, cat_id, session["user_id"])
    )
    conn.commit()
    ok = cursor.rowcount > 0
    cursor.close()

    if ok:
        push(conn, session["user_id"], "info",
             f"Category Updated: {name}",
             f"Category '{name}' was updated to type '{ctype}'.")
    conn.close()
    return jsonify({"success": ok})


# ── Delete ────────────────────────────────────
@categories_bp.route("/api/categories/delete", methods=["POST"])
def delete_category():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        cat_id = int(request.form.get("id", 0))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid ID."})

    conn   = get_db()
    ensure_table(conn)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT name FROM categories WHERE id=%s AND user_id=%s",
        (cat_id, session["user_id"])
    )
    cat = cursor.fetchone()
    cursor.close()

    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM categories WHERE id=%s AND user_id=%s",
        (cat_id, session["user_id"])
    )
    conn.commit()
    ok = cursor.rowcount > 0
    cursor.close()

    if ok and cat:
        push(conn, session["user_id"], "warning",
             f"Category Deleted: {cat['name']}",
             f"Category '{cat['name']}' was removed. Existing transactions are unaffected.")
    conn.close()
    return jsonify({"success": ok})
