"""
=============================================
  Reset & Clear Data routes
  GET  /reset
  POST /api/reset/all-data
=============================================
"""

import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from config.database import get_db
from routes.notify import push, ensure_table

reset_bp = Blueprint("reset", __name__)


def _ensure_reset_history_table(conn):
    """Create reset history table"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reset_history (
            id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id    INT UNSIGNED NOT NULL,
            action     VARCHAR(50) NOT NULL,
            records_deleted INT UNSIGNED DEFAULT 0,
            status     ENUM('success','failed') NOT NULL DEFAULT 'success',
            message    TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cursor.close()


def _log_reset_action(user_id, action, records_deleted=0, status='success', message=''):
    """Log reset action to database"""
    try:
        conn = get_db()
        _ensure_reset_history_table(conn)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reset_history (user_id, action, records_deleted, status, message) "
            "VALUES (%s, %s, %s, %s, %s)",
            (user_id, action, records_deleted, status, message)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error logging reset action: {e}")


@reset_bp.route("/reset")
def reset_page():
    """Reset & Clear Data page"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    user_name = session.get("user_name", "User")

    try:
        conn = get_db()
        _ensure_reset_history_table(conn)
        cursor = conn.cursor(dictionary=True)
        
        # Get reset history
        cursor.execute(
            "SELECT * FROM reset_history WHERE user_id=%s ORDER BY created_at DESC LIMIT 20",
            (user_id,)
        )
        history = cursor.fetchall()
        
        # Get data counts
        cursor.execute("SELECT COUNT(*) as count FROM transactions WHERE user_id=%s", (user_id,))
        tx_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM budgets WHERE user_id=%s", (user_id,))
        budget_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM categories WHERE user_id=%s", (user_id,))
        cat_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM notifications WHERE user_id=%s", (user_id,))
        notif_count = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()

        return render_template("reset.html",
            user_name=user_name,
            history=history,
            tx_count=tx_count,
            budget_count=budget_count,
            cat_count=cat_count,
            notif_count=notif_count
        )
    except Exception as e:
        print(f"Error in reset_page: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", 500


@reset_bp.route("/api/reset/all-data", methods=["POST"])
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

        total_deleted = tx_count + budget_count + cat_count + notif_count + backup_count

        conn.commit()
        cursor.close()

        # Log the reset action
        _log_reset_action(
            user_id,
            "full_reset",
            total_deleted,
            "success",
            f"Deleted: {tx_count} transactions, {budget_count} budgets, {cat_count} categories, "
            f"{notif_count} notifications, {backup_count} backup records"
        )

        print(f"[RESET] User {user_id}: Deleted {tx_count} transactions, {budget_count} budgets, "
              f"{cat_count} categories, {notif_count} notifications, {backup_count} backup records")

        # Send notification
        try:
            ensure_table(conn)
            push(conn, user_id, "warning", "Data Reset Complete", 
                 f"All your data has been reset. {total_deleted} records were deleted.")
        except:
            pass

        conn.close()

        return jsonify({
            "success": True,
            "message": "All data has been reset successfully",
            "deleted": {
                "transactions": tx_count,
                "budgets": budget_count,
                "categories": cat_count,
                "notifications": notif_count,
                "backup_history": backup_count,
                "total": total_deleted
            }
        })

    except Exception as e:
        print(f"[ERROR] Reset failed for user {user_id}: {str(e)}")
        _log_reset_action(user_id, "full_reset", 0, "failed", str(e))
        return jsonify({
            "success": False,
            "message": f"Error resetting data: {str(e)}"
        }), 500
