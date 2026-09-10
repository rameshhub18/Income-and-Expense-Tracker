"""
=============================================
  Reports route
  GET  /reports
  GET  /api/reports/data   (JSON for charts)
  GET  /api/reports/export (CSV download)
=============================================
"""

import csv
import io
from datetime import date, timedelta
from flask import (Blueprint, render_template, redirect, url_for,
                   session, jsonify, request, Response)
from config.database import get_db

reports_bp = Blueprint("reports", __name__)


def _date_range(period, custom_from=None, custom_to=None):
    today = date.today()
    if period == "7d":
        return today - timedelta(days=6), today
    elif period == "30d":
        return today - timedelta(days=29), today
    elif period == "90d":
        return today - timedelta(days=89), today
    elif period == "12m":
        return date(today.year - 1, today.month, 1), today
    elif period == "ytd":
        return date(today.year, 1, 1), today
    elif period == "custom" and custom_from and custom_to:
        return date.fromisoformat(custom_from), date.fromisoformat(custom_to)
    # default: current month
    return date(today.year, today.month, 1), today


# ── Page ──────────────────────────────────────
@reports_bp.route("/reports")
def reports_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id   = session["user_id"]
    user_name = session.get("user_name", "User")

    period      = request.args.get("period", "30d")
    custom_from = request.args.get("from", "")
    custom_to   = request.args.get("to",   "")
    date_from, date_to = _date_range(period, custom_from, custom_to)

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # ── Summary totals ────────────────────────
    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='income'  THEN amount END), 0) AS income,
            COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0) AS expense,
            COUNT(*) AS tx_count
        FROM transactions
        WHERE user_id=%s AND date BETWEEN %s AND %s
    """, (user_id, date_from, date_to))
    totals = cursor.fetchone()
    total_income  = float(totals["income"])
    total_expense = float(totals["expense"])
    net_savings   = total_income - total_expense
    tx_count      = totals["tx_count"]
    savings_rate  = round((net_savings / total_income * 100), 1) if total_income else 0

    # ── Daily trend (income vs expense) ──────
    cursor.execute("""
        SELECT date, type, SUM(amount) AS total
        FROM transactions
        WHERE user_id=%s AND date BETWEEN %s AND %s
        GROUP BY date, type
        ORDER BY date
    """, (user_id, date_from, date_to))
    daily_rows = cursor.fetchall()

    # ── Expense by category ───────────────────
    cursor.execute("""
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE user_id=%s AND type='expense' AND date BETWEEN %s AND %s
        GROUP BY category ORDER BY total DESC
    """, (user_id, date_from, date_to))
    expense_by_cat = [{"category": r["category"], "total": float(r["total"])}
                      for r in cursor.fetchall()]

    # ── Income by category ────────────────────
    cursor.execute("""
        SELECT category, SUM(amount) AS total
        FROM transactions
        WHERE user_id=%s AND type='income' AND date BETWEEN %s AND %s
        GROUP BY category ORDER BY total DESC
    """, (user_id, date_from, date_to))
    income_by_cat = [{"category": r["category"], "total": float(r["total"])}
                     for r in cursor.fetchall()]

    # ── Monthly summary (last 12 months) ──────
    cursor.execute("""
        SELECT DATE_FORMAT(date,'%%b %%Y') AS month,
               DATE_FORMAT(date,'%%Y-%%m') AS sort_key,
               SUM(CASE WHEN type='income'  THEN amount ELSE 0 END) AS income,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
        FROM transactions
        WHERE user_id=%s AND date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(date,'%%Y-%%m')
        ORDER BY sort_key
    """, (user_id,))
    monthly = [{"month": r["month"],
                "income":  float(r["income"]),
                "expense": float(r["expense"])}
               for r in cursor.fetchall()]

    # ── Top 5 transactions ────────────────────
    cursor.execute("""
        SELECT * FROM transactions
        WHERE user_id=%s AND date BETWEEN %s AND %s
        ORDER BY amount DESC LIMIT 5
    """, (user_id, date_from, date_to))
    top_tx = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("reports.html",
        user_name      = user_name,
        period         = period,
        custom_from    = custom_from,
        custom_to      = custom_to,
        date_from      = date_from,
        date_to        = date_to,
        total_income   = total_income,
        total_expense  = total_expense,
        net_savings    = net_savings,
        tx_count       = tx_count,
        savings_rate   = savings_rate,
        expense_by_cat = expense_by_cat,
        income_by_cat  = income_by_cat,
        monthly        = monthly,
        daily_rows     = daily_rows,
        top_tx         = top_tx,
    )


# ── CSV Export ────────────────────────────────
@reports_bp.route("/api/reports/export")
def export_csv():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id     = session["user_id"]
    period      = request.args.get("period", "30d")
    custom_from = request.args.get("from", "")
    custom_to   = request.args.get("to",   "")
    date_from, date_to = _date_range(period, custom_from, custom_to)

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # ── Get summary totals ────────────────────
    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='income'  THEN amount END), 0) AS income,
            COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0) AS expense
        FROM transactions
        WHERE user_id=%s AND date BETWEEN %s AND %s
    """, (user_id, date_from, date_to))
    totals = cursor.fetchone()
    total_income  = float(totals["income"])
    total_expense = float(totals["expense"])
    balance_remaining = total_income - total_expense
    
    cursor.execute("""
        SELECT date, type, category, amount, description
        FROM transactions
        WHERE user_id=%s AND date BETWEEN %s AND %s
        ORDER BY date DESC
    """, (user_id, date_from, date_to))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # ── Write summary section ─────────────────
    writer.writerow(["Report Summary"])
    writer.writerow(["Period", f"{date_from} to {date_to}"])
    writer.writerow([])
    writer.writerow(["Total Income", f"{total_income:.2f}"])
    writer.writerow(["Total Expense", f"{total_expense:.2f}"])
    writer.writerow(["Balance Remaining", f"{balance_remaining:.2f}"])
    writer.writerow([])
    writer.writerow([])
    
    # ── Write transaction details ─────────────
    writer.writerow(["Date", "Type", "Category", "Amount", "Description"])
    for r in rows:
        writer.writerow([r["date"], r["type"], r["category"],
                         f"{float(r['amount']):.2f}", r["description"] or ""])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{date_from}_{date_to}.csv"}
    )
