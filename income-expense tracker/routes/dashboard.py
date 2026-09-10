"""
=============================================
  Dashboard route — /dashboard
=============================================
"""

from flask import Blueprint, render_template, redirect, url_for, session
from config.database import get_db
from routes.notify import ensure_table

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id   = session["user_id"]
    user_name = session.get("user_name", "User")

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # Summary totals
    cursor.execute(
        "SELECT COALESCE(SUM(amount),0) AS total FROM transactions WHERE user_id=%s AND type='income'",
        (user_id,)
    )
    total_income = float(cursor.fetchone()["total"])

    cursor.execute(
        "SELECT COALESCE(SUM(amount),0) AS total FROM transactions WHERE user_id=%s AND type='expense'",
        (user_id,)
    )
    total_expense = float(cursor.fetchone()["total"])

    balance = total_income - total_expense

    # Budget - check if any category is exceeded this month
    cursor.execute("""
        SELECT b.category, b.amount,
               COALESCE(SUM(t.amount), 0) AS spent
        FROM budgets b
        LEFT JOIN transactions t
               ON t.user_id  = b.user_id
              AND t.category = b.category
              AND t.type     = 'expense'
              AND DATE_FORMAT(t.date, '%%Y-%%m') = DATE_FORMAT(CURDATE(), '%%Y-%%m')
        WHERE b.user_id = %s AND DATE_FORMAT(b.month, '%%Y-%%m') = DATE_FORMAT(CURDATE(), '%%Y-%%m')
        GROUP BY b.id
    """, (user_id,))
    budget_rows = cursor.fetchall()
    
    total_budget = 0
    budget_exceeded = False
    
    print(f"[DEBUG] Budget rows for user {user_id}: {len(budget_rows)}")
    for row in budget_rows:
        amount = float(row["amount"])
        spent = float(row["spent"])
        total_budget += amount
        print(f"[DEBUG] Category: {row['category']}, Budget: {amount}, Spent: {spent}, Exceeded: {spent > amount}")
        if spent > amount:
            budget_exceeded = True
    
    print(f"[DEBUG] Total Budget: {total_budget}, Budget Exceeded: {budget_exceeded}")

    # Recent transactions (last 10)
    cursor.execute(
        "SELECT * FROM transactions WHERE user_id=%s ORDER BY date DESC LIMIT 10",
        (user_id,)
    )
    transactions = cursor.fetchall()

    # Monthly chart data (last 6 months)
    cursor.execute("""
        SELECT DATE_FORMAT(date,'%%b %%Y') AS month,
               SUM(CASE WHEN type='income'  THEN amount ELSE 0 END) AS income,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
        FROM transactions
        WHERE user_id=%s AND date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(date,'%%Y-%%m')
        ORDER BY MIN(date)
    """, (user_id,))
    monthly_data = [
        {"month": r["month"], "income": float(r["income"]), "expense": float(r["expense"])}
        for r in cursor.fetchall()
    ]

    # Expense by category (pie chart)
    cursor.execute("""
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE user_id=%s AND type='expense'
        GROUP BY category ORDER BY total DESC LIMIT 6
    """, (user_id,))
    cat_data = [
        {"category": r["category"], "total": float(r["total"])}
        for r in cursor.fetchall()
    ]

    # Get user's custom categories
    from routes.categories import _ensure_cat_table, _seed_defaults
    _ensure_cat_table(conn)
    _seed_defaults(user_id, conn)
    
    cursor.execute("""
        SELECT name, type FROM categories WHERE user_id=%s ORDER BY name
    """, (user_id,))
    user_categories = cursor.fetchall()

    cursor.close()
    conn.close()

    # Unread notification count for navbar badge
    conn2  = get_db()
    ensure_table(conn2)
    cur2   = conn2.cursor(dictionary=True)
    cur2.execute(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id=%s AND is_read=0",
        (user_id,)
    )
    unread_count = cur2.fetchone()["cnt"]
    cur2.close()
    conn2.close()

    return render_template("dashboard.html",
        user_name     = user_name,
        total_income  = total_income,
        total_expense = total_expense,
        balance       = balance,
        total_budget  = total_budget,
        budget_exceeded = budget_exceeded,
        transactions  = transactions,
        monthly_data  = monthly_data,
        cat_data      = cat_data,
        user_categories = user_categories,
        unread_count  = unread_count,
    )
