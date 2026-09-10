"""
=============================================
  API routes — /api/transaction + /api/budget
  Handles add / edit / delete + notifications
=============================================
"""

from flask import Blueprint, request, jsonify, session
from config.database import get_db
from routes.notify import push, ensure_table

api_bp = Blueprint("api", __name__)

VALID_TYPES = {"income", "expense"}


def _ensure_budget_tables(conn):
    """Create budgets table if missing. Uses a fresh connection for notifications."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id         INT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
            user_id    INT UNSIGNED  NOT NULL,
            category   VARCHAR(80)   NOT NULL,
            amount     DECIMAL(12,2) NOT NULL,
            month      DATE          NOT NULL,
            created_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_user_cat_month (user_id, category, month),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cursor.close()
    # Ensure notifications table using a SEPARATE connection to avoid state pollution
    try:
        conn2 = get_db()
        ensure_table(conn2)
        conn2.close()
    except Exception:
        pass


def _push_notification(conn, user_id, ntype, title, message):
    """Push notification using a fresh connection to avoid polluting the main conn."""
    try:
        conn2 = get_db()
        push(conn2, user_id, ntype, title, message)
        conn2.close()
    except Exception:
        pass


def _check_budget_after_transaction(conn, user_id, category, month_str):
    """After adding an expense, check if any budget is hit and notify."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.amount,
               COALESCE(SUM(t.amount), 0) AS spent
        FROM budgets b
        LEFT JOIN transactions t
               ON t.user_id  = b.user_id
              AND t.category = b.category
              AND t.type     = 'expense'
              AND DATE_FORMAT(t.date,'%%Y-%%m') = DATE_FORMAT(b.month,'%%Y-%%m')
        WHERE b.user_id  = %s
          AND b.category = %s
          AND DATE_FORMAT(b.month,'%%Y-%%m') = %s
        GROUP BY b.id
        LIMIT 1
    """, (user_id, category, month_str))
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return

    budget = float(row["amount"])
    spent  = float(row["spent"])
    pct    = (spent / budget * 100) if budget else 0

    if spent > budget:
        push(conn, user_id, "error",
             f"Budget Exceeded: {category}",
             f"You've spent \u20b9{spent:,.2f} against your \u20b9{budget:,.2f} budget "
             f"for {category}. Overspent by \u20b9{spent - budget:,.2f}.")
    elif pct >= 80:
        push(conn, user_id, "warning",
             f"Budget Warning: {category}",
             f"You've used {pct:.1f}% of your \u20b9{budget:,.2f} budget for {category}. "
             f"Only \u20b9{budget - spent:,.2f} remaining.")


@api_bp.route("/transaction", methods=["POST"])
def transaction():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    user_id = session["user_id"]
    action  = request.form.get("action", "")

    conn = get_db()
    ensure_table(conn)

    # ── ADD ───────────────────────────────────
    if action == "add":
        try:
            amount = float(request.form.get("amount", 0))
        except ValueError:
            conn.close()
            return jsonify({"success": False, "message": "Invalid amount."})

        tx_type     = request.form.get("type",        "").strip()
        category    = request.form.get("category",    "").strip()
        date        = request.form.get("date",        "").strip()
        description = request.form.get("description", "").strip()

        if amount <= 0 or tx_type not in VALID_TYPES or not category or not date:
            conn.close()
            return jsonify({"success": False, "message": "Invalid input."})

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (user_id, type, category, amount, date, description) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (user_id, tx_type, category, amount, date, description or None)
        )
        conn.commit()
        cursor.close()

        # Notification: transaction added
        sign = "+" if tx_type == "income" else "-"
        push(conn, user_id, "success" if tx_type == "income" else "info",
             f"{tx_type.capitalize()} Added: {category}",
             f"{sign}\u20b9{amount:,.2f} recorded under {category} on {date}."
             + (f" Note: {description}" if description else ""))

        # Check budget if expense
        if tx_type == "expense":
            month_str = date[:7]  # YYYY-MM
            _check_budget_after_transaction(conn, user_id, category, month_str)

        conn.close()
        return jsonify({"success": True, "message": "Added."})

    # ── EDIT ──────────────────────────────────
    elif action == "edit":
        try:
            tx_id  = int(request.form.get("tx_id", 0))
            amount = float(request.form.get("amount", 0))
        except ValueError:
            conn.close()
            return jsonify({"success": False, "message": "Invalid data."})

        tx_type     = request.form.get("type",        "").strip()
        category    = request.form.get("category",    "").strip()
        date        = request.form.get("date",        "").strip()
        description = request.form.get("description", "").strip()

        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transactions SET type=%s, category=%s, amount=%s, date=%s, description=%s "
            "WHERE id=%s AND user_id=%s",
            (tx_type, category, amount, date, description or None, tx_id, user_id)
        )
        conn.commit()
        ok = cursor.rowcount > 0
        cursor.close()

        if ok:
            push(conn, user_id, "info",
                 f"Transaction Updated: {category}",
                 f"Transaction updated to \u20b9{amount:,.2f} ({tx_type}) on {date}.")
            if tx_type == "expense":
                _check_budget_after_transaction(conn, user_id, category, date[:7])

        conn.close()
        return jsonify({"success": ok, "message": "Updated." if ok else "Nothing updated."})

    # ── DELETE ────────────────────────────────
    elif action == "delete":
        try:
            tx_id = int(request.form.get("tx_id", 0))
        except ValueError:
            conn.close()
            return jsonify({"success": False, "message": "Invalid ID."})

        # Fetch details before deleting for notification
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT type, category, amount, date FROM transactions WHERE id=%s AND user_id=%s",
            (tx_id, user_id)
        )
        tx = cursor.fetchone()
        cursor.close()

        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM transactions WHERE id=%s AND user_id=%s",
            (tx_id, user_id)
        )
        conn.commit()
        ok = cursor.rowcount > 0
        cursor.close()

        if ok and tx:
            push(conn, user_id, "info",
                 f"Transaction Deleted: {tx['category']}",
                 f"\u20b9{float(tx['amount']):,.2f} {tx['type']} entry from {tx['date']} "
                 f"under {tx['category']} was deleted.")

        conn.close()
        return jsonify({"success": ok, "message": "Deleted." if ok else "Not found."})

    conn.close()
    return jsonify({"success": False, "message": "Unknown action."})


# ===== BUDGET API ROUTES =====

# ── Add Budget ────────────────────────────────
@api_bp.route("/budget/add", methods=["POST"])
def add_budget():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    category = request.form.get("category", "").strip()
    month    = request.form.get("month",    "").strip()
    try:
        amount = float(request.form.get("amount", 0))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid amount."})

    if not category or not month or amount <= 0:
        return jsonify({"success": False, "message": "All fields are required."})

    month_date = month + "-01"
    conn = get_db()
    _ensure_budget_tables(conn)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO budgets (user_id, category, amount, month) VALUES (%s,%s,%s,%s)",
            (session["user_id"], category, amount, month_date)
        )
        conn.commit()
        new_id = cursor.lastrowid
    except Exception:
        cursor.close(); conn.close()
        return jsonify({"success": False, "message": "Budget for this category/month already exists."})

    # Push a success notification
    _push_notification(conn, session["user_id"], "success",
        f"Budget Set: {category}",
        f"Monthly budget of ₹{amount:,.2f} set for {category} ({month}).")

    cursor.close(); conn.close()
    return jsonify({"success": True, "id": new_id})


# ── Edit Budget ───────────────────────────────
@api_bp.route("/budget/edit", methods=["POST"])
def edit_budget():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        b_id   = int(request.form.get("id", 0))
        amount = float(request.form.get("amount", 0))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid data."})

    category = request.form.get("category", "").strip()
    month    = request.form.get("month",    "").strip()
    month_date = month + "-01"

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE budgets SET category=%s, amount=%s, month=%s WHERE id=%s AND user_id=%s",
        (category, amount, month_date, b_id, session["user_id"])
    )
    conn.commit()
    ok = cursor.rowcount > 0
    cursor.close(); conn.close()
    return jsonify({"success": ok, "message": "Updated." if ok else "Not found."})


# ── Delete Budget ─────────────────────────────
@api_bp.route("/budget/delete", methods=["POST"])
def delete_budget():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        b_id = int(request.form.get("id", 0))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid ID."})

    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM budgets WHERE id=%s AND user_id=%s",
        (b_id, session["user_id"])
    )
    conn.commit()
    ok = cursor.rowcount > 0
    cursor.close(); conn.close()
    return jsonify({"success": ok})


# ===== RESET ALL DATA =====

@api_bp.route("/reset-all-data", methods=["POST"])
def reset_all_data():
    """Reset all user data - transactions, budgets, categories, notifications"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    user_id = session["user_id"]

    try:
        conn = get_db()
        cursor = conn.cursor()

        # Delete all user data in order (respecting foreign keys)
        # 1. Delete transactions
        cursor.execute("DELETE FROM transactions WHERE user_id = %s", (user_id,))
        tx_count = cursor.rowcount

        # 2. Delete budgets
        cursor.execute("DELETE FROM budgets WHERE user_id = %s", (user_id,))
        budget_count = cursor.rowcount

        # 3. Delete categories
        cursor.execute("DELETE FROM categories WHERE user_id = %s", (user_id,))
        cat_count = cursor.rowcount

        # 4. Delete notifications
        cursor.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
        notif_count = cursor.rowcount

        # 5. Delete backup history
        cursor.execute("DELETE FROM backup_history WHERE user_id = %s", (user_id,))
        backup_count = cursor.rowcount

        conn.commit()
        cursor.close()
        conn.close()

        print(f"[RESET] User {user_id}: Deleted {tx_count} transactions, {budget_count} budgets, "
              f"{cat_count} categories, {notif_count} notifications, {backup_count} backup records")

        return jsonify({
            "success": True,
            "message": "All data has been reset successfully",
            "deleted": {
                "transactions": tx_count,
                "budgets": budget_count,
                "categories": cat_count,
                "notifications": notif_count,
                "backup_history": backup_count
            }
        })

    except Exception as e:
        print(f"[ERROR] Reset failed for user {user_id}: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error resetting data: {str(e)}"
        }), 500
