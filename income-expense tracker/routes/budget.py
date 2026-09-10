"""
=============================================
  Budget routes
  GET  /budget
  POST /api/budget/add
  POST /api/budget/edit
  POST /api/budget/delete
=============================================
"""

from datetime import date
from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from config.database import get_db
from routes.notify import push, ensure_table as ensure_notif_table

budget_bp = Blueprint("budget", __name__)


def _ensure_tables(conn):
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
        ensure_notif_table(conn2)
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


def _get_categories(conn, user_id):
    """Return category names from categories table + distinct transaction categories."""
    cursor = conn.cursor(dictionary=True)
    # Try categories table first
    try:
        cursor.execute(
            "SELECT name FROM categories WHERE user_id=%s ORDER BY name", (user_id,)
        )
        cats = [r["name"] for r in cursor.fetchall()]
    except Exception:
        cats = []

    # Also pull from transactions
    try:
        cursor.execute(
            "SELECT DISTINCT category FROM transactions WHERE user_id=%s AND type='expense' ORDER BY category",
            (user_id,)
        )
        tx_cats = [r["category"] for r in cursor.fetchall()]
        for c in tx_cats:
            if c not in cats:
                cats.append(c)
    except Exception:
        pass

    cursor.close()

    # Fallback defaults
    if not cats:
        cats = ["Salary","Freelance","Food","Transport","Shopping",
                "Bills","Health","Entertainment","Other"]
    return sorted(cats)


# ── Page ──────────────────────────────────────
@budget_bp.route("/budget")
def budget_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id   = session["user_id"]
    user_name = session.get("user_name", "User")

    month_str = request.args.get("month", date.today().strftime("%Y-%m"))
    try:
        year, mon = int(month_str[:4]), int(month_str[5:7])
    except Exception:
        year, mon = date.today().year, date.today().month

    conn = get_db()
    _ensure_tables(conn)
    cursor = conn.cursor(dictionary=True)

    # Budgets with actual spending joined - DEBUG VERSION
    cursor.execute("""
        SELECT b.*,
               COALESCE(SUM(t.amount), 0) AS spent
        FROM budgets b
        LEFT JOIN transactions t
               ON t.user_id  = b.user_id
              AND t.category = b.category
              AND t.type     = 'expense'
              AND DATE_FORMAT(t.date, '%%Y-%%m') = DATE_FORMAT(b.month, '%%Y-%%m')
        WHERE b.user_id = %s
        GROUP BY b.id
        ORDER BY b.category
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()

    budgets = []
    notifications_to_push = []   # collect first, push after

    for b in rows:
        amount    = float(b["amount"])
        spent     = float(b["spent"])
        remaining = amount - spent
        pct       = min(round((spent / amount * 100), 1) if amount else 0, 100)
        real_pct  = round((spent / amount * 100), 1) if amount else 0

        if spent > amount:
            status = "exceeded"
            notifications_to_push.append(("error",
                f"Budget Exceeded: {b['category']}",
                f"You've spent \u20b9{spent:,.2f} against a budget of \u20b9{amount:,.2f} "
                f"for {b['category']} this month. Overspent by \u20b9{abs(remaining):,.2f}."))
        elif pct >= 80:
            status = "warning"
            notifications_to_push.append(("warning",
                f"Budget Warning: {b['category']}",
                f"You've used {real_pct}% of your \u20b9{amount:,.2f} budget for "
                f"{b['category']}. Only \u20b9{remaining:,.2f} remaining."))
        else:
            status = "ok"

        budgets.append({
            **b,
            "amount":    amount,
            "spent":     spent,
            "remaining": remaining,
            "pct":       pct,
            "real_pct":  real_pct,
            "status":    status,
        })

    total_budget    = sum(b["amount"]    for b in budgets)
    total_spent     = sum(b["spent"]     for b in budgets)
    total_remaining = total_budget - total_spent
    overall_pct     = min(round((total_spent / total_budget * 100), 1) if total_budget else 0, 100)

    if total_budget > 0 and total_spent > total_budget:
        notifications_to_push.append(("error",
            "Overall Monthly Budget Exceeded",
            f"Total spending \u20b9{total_spent:,.2f} has exceeded your monthly budget of "
            f"\u20b9{total_budget:,.2f}."))

    # Push all notifications now (after data is fully collected)
    for ntype, title, message in notifications_to_push:
        _push_notification(conn, user_id, ntype, title, message)

    # Get categories using a FRESH connection to avoid state pollution
    conn2 = get_db()
    categories = _get_categories(conn2, user_id)
    conn2.close()

    # Build month list
    months = []
    for i in range(-11, 4):
        m = mon + i
        y = year
        while m < 1:  m += 12; y -= 1
        while m > 12: m -= 12; y += 1
        months.append({
            "value": f"{y:04d}-{m:02d}",
            "label": date(y, m, 1).strftime("%B %Y")
        })

    conn.close()

    import sys
    print(f"[BUDGET DEBUG] Rendering with {len(budgets)} budgets for user {user_id}", file=sys.stderr)

    return render_template("budget.html",
        user_name       = user_name,
        budgets         = budgets,
        total_budget    = total_budget,
        total_spent     = total_spent,
        total_remaining = total_remaining,
        overall_pct     = overall_pct,
        categories      = categories,
        selected_month  = month_str,
        months          = months,
    )
