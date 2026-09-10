"""
=============================================
  Backup & Recovery routes
  GET  /backup
  POST /api/backup/create
  POST /api/backup/restore
  POST /api/backup/delete
=============================================
"""

import os
import subprocess
import gzip
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from config.database import get_db, DB_CONFIG
from routes.notify import push, ensure_table

backup_bp = Blueprint("backup", __name__)


def _ensure_backup_history_table(conn):
    """Create backup history table"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backup_history (
            id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id    INT UNSIGNED NOT NULL,
            action     ENUM('backup','restore','delete') NOT NULL,
            filename   VARCHAR(255) NOT NULL,
            file_size  DECIMAL(10,2),
            status     ENUM('success','failed') NOT NULL DEFAULT 'success',
            message    TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cursor.close()


def _log_action(user_id, action, filename, file_size=None, status='success', message=''):
    """Log backup action to database"""
    try:
        conn = get_db()
        _ensure_backup_history_table(conn)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO backup_history (user_id, action, filename, file_size, status, message) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, action, filename, file_size, status, message)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error logging action: {e}")


def _get_backups():
    """Get list of all backups"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    backups = []
    for file in sorted(os.listdir(backup_dir), reverse=True):
        if file.endswith('.sql.gz'):
            # Use forward slashes for cross-platform compatibility
            path = f"backups/{file}"
            full_path = os.path.join(backup_dir, file)
            size_bytes = os.path.getsize(full_path)
            size_kb = size_bytes / 1024
            backups.append({
                'filename': file,
                'path': path,
                'size': f"{size_kb:.2f} KB"
            })
    return backups
    return backups


@backup_bp.route("/backup")
def backup_page():
    """Backup & Recovery page"""
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    user_name = session.get("user_name", "User")

    try:
        backups = _get_backups()

        # Get history
        conn = get_db()
        _ensure_backup_history_table(conn)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM backup_history WHERE user_id=%s ORDER BY created_at DESC LIMIT 20",
            (user_id,)
        )
        history = cursor.fetchall()
        cursor.close()
        conn.close()

        return render_template("backup.html",
            user_name=user_name,
            backups=backups,
            history=history
        )
    except Exception as e:
        print(f"Error in backup_page: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", 500


@backup_bp.route("/api/backup/create", methods=["POST"])
def create_backup():
    """Create database backup"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/finance_tracker_backup_{timestamp}.sql"

        # Find mysqldump
        mysqldump_paths = [
            "mysqldump",
            "C:\\xampp\\mysql\\bin\\mysqldump.exe",
            "/usr/bin/mysqldump",
            "/usr/local/bin/mysqldump"
        ]

        mysqldump_cmd = None
        for path in mysqldump_paths:
            try:
                result = subprocess.run(f"{path} --version", shell=True, capture_output=True, timeout=2)
                if result.returncode == 0:
                    mysqldump_cmd = path
                    break
            except:
                pass

        if not mysqldump_cmd:
            _log_action(session["user_id"], "backup", "unknown", None, "failed", "mysqldump not found")
            return jsonify({"success": False, "message": "mysqldump not found"})

        # Create backup using Python subprocess instead of shell redirection
        try:
            backup_file_path = backup_file.replace("/", os.sep)  # Convert to OS-specific path
            with open(backup_file_path, 'w') as f:
                cmd_args = [mysqldump_cmd, '-h', 'localhost', '-u', 'root']
                # Add password if it's not empty
                if 'password' in DB_CONFIG and DB_CONFIG['password']:
                    cmd_args.append('-p' + DB_CONFIG['password'])
                cmd_args.append('finance_tracker')
                result = subprocess.run(
                    cmd_args,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60
                )
                f.flush()  # Ensure all data is written
            
            if result.returncode != 0:
                if os.path.exists(backup_file_path):
                    os.remove(backup_file_path)
                error_msg = result.stderr if result.stderr else "Unknown error"
                print(f"Mysqldump error: {error_msg}")
                _log_action(session["user_id"], "backup", "unknown", None, "failed", error_msg)
                return jsonify({"success": False, "message": f"Backup failed: {error_msg}"})
        except Exception as e:
            if os.path.exists(backup_file_path):
                os.remove(backup_file_path)
            print(f"Backup exception: {str(e)}")
            _log_action(session["user_id"], "backup", "unknown", None, "failed", str(e))
            return jsonify({"success": False, "message": f"Backup error: {str(e)}"})

        if os.path.exists(backup_file_path) and os.path.getsize(backup_file_path) > 0:
            # Compress
            compressed = f"{backup_file_path}.gz"
            print(f"Compressing: {backup_file_path} -> {compressed}")
            with open(backup_file_path, 'rb') as f_in:
                with gzip.open(compressed, 'wb') as f_out:
                    f_out.writelines(f_in)
            os.remove(backup_file_path)

            filename = os.path.basename(compressed)
            file_size_kb = os.path.getsize(compressed) / 1024
            print(f"Backup completed: {filename}, Size: {file_size_kb:.2f} KB")

            _log_action(session["user_id"], "backup", filename, file_size_kb, "success", "Backup created")

            # Notification
            conn = get_db()
            ensure_table(conn)
            push(conn, session["user_id"], "success", "Backup Created", f"Backup: {filename}")
            conn.close()

            return jsonify({"success": True, "message": "Backup created successfully"})
        else:
            if os.path.exists(backup_file_path):
                actual_size = os.path.getsize(backup_file_path)
                print(f"Backup file size: {actual_size} bytes")
                os.remove(backup_file_path)
            error_msg = f"Backup file is empty or not created"
            print(f"Backup error: {error_msg}")
            _log_action(session["user_id"], "backup", "unknown", None, "failed", error_msg)
            return jsonify({"success": False, "message": error_msg})

    except Exception as e:
        _log_action(session["user_id"], "backup", "unknown", None, "failed", str(e))
        return jsonify({"success": False, "message": str(e)})


@backup_bp.route("/api/backup/restore", methods=["POST"])
def restore_backup():
    """Restore from backup"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    backup_file = request.form.get("backup_file", "").strip()
    # Normalize path to use forward slashes
    backup_file = backup_file.replace("\\", "/")
    print(f"Restore request for: {backup_file}")

    if not backup_file:
        print("No backup_file provided")
        _log_action(session["user_id"], "restore", "unknown", None, "failed", "No file specified")
        return jsonify({"success": False, "message": "No backup file specified"})
    
    if not os.path.exists(backup_file):
        print(f"File not found: {backup_file}")
        _log_action(session["user_id"], "restore", backup_file, None, "failed", "File not found")
        return jsonify({"success": False, "message": f"Backup file not found: {backup_file}"})

    try:
        filename = os.path.basename(backup_file)
        temp_file = backup_file.replace(".gz", ".tmp.sql")

        # Decompress
        print(f"Decompressing: {backup_file}")
        with gzip.open(backup_file, 'rb') as f_in:
            with open(temp_file, 'wb') as f_out:
                f_out.writelines(f_in)

        # Find mysql
        mysql_paths = [
            "mysql",
            "C:\\xampp\\mysql\\bin\\mysql.exe",
            "/usr/bin/mysql",
            "/usr/local/bin/mysql"
        ]

        mysql_cmd = None
        for path in mysql_paths:
            try:
                result = subprocess.run(f"{path} --version", shell=True, capture_output=True, timeout=2)
                if result.returncode == 0:
                    mysql_cmd = path
                    print(f"Found mysql at: {path}")
                    break
            except:
                pass

        if not mysql_cmd:
            os.remove(temp_file)
            print("mysql not found")
            _log_action(session["user_id"], "restore", filename, None, "failed", "mysql not found")
            return jsonify({"success": False, "message": "mysql not found"})

        # Restore using shell redirection with proper encoding
        try:
            print(f"Restoring database from: {temp_file}")
            
            # Build command with password if it exists
            cmd_parts = [mysql_cmd, '-h', 'localhost', '-u', 'root']
            # Add password if it's not empty
            if 'password' in DB_CONFIG and DB_CONFIG['password']:
                cmd_parts.append('-p' + DB_CONFIG['password'])
            cmd_parts.append('finance_tracker')
            
            # Use shell redirection to avoid encoding issues
            # This is more reliable for SQL files with special characters
            cmd_str = ' '.join(cmd_parts) + f' < "{temp_file}"'
            
            print(f"Executing: {cmd_str}")
            result = subprocess.run(
                cmd_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300
            )
            
            if result.returncode != 0:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                error_msg = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
                print(f"Restore error: {error_msg}")
                _log_action(session["user_id"], "restore", filename, None, "failed", error_msg)
                return jsonify({"success": False, "message": f"Restore failed: {error_msg}"})
            
            print(f"Restore completed successfully")
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            print(f"Restore exception: {str(e)}")
            _log_action(session["user_id"], "restore", filename, None, "failed", str(e))
            return jsonify({"success": False, "message": f"Restore error: {str(e)}"})
        
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        file_size_kb = os.path.getsize(backup_file) / 1024
        _log_action(session["user_id"], "restore", filename, file_size_kb, "success", "Database restored")

        conn = get_db()
        ensure_table(conn)
        push(conn, session["user_id"], "warning", "Database Restored", f"Restored from: {filename}")
        conn.close()

        return jsonify({"success": True, "message": "Database restored successfully"})
    except Exception as e:
        print(f"Restore exception: {str(e)}")
        _log_action(session["user_id"], "restore", backup_file, None, "failed", str(e))
        return jsonify({"success": False, "message": str(e)})


@backup_bp.route("/api/backup/delete", methods=["POST"])
def delete_backup():
    """Delete backup file"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    backup_file = request.form.get("backup_file", "").strip()
    # Normalize path to use forward slashes
    backup_file = backup_file.replace("\\", "/")
    print(f"Delete request for: {backup_file}")

    if not backup_file:
        print("No backup_file provided")
        _log_action(session["user_id"], "delete", "unknown", None, "failed", "No file specified")
        return jsonify({"success": False, "message": "No backup file specified"})
    
    if not os.path.exists(backup_file):
        print(f"File not found: {backup_file}")
        _log_action(session["user_id"], "delete", backup_file, None, "failed", "File not found")
        return jsonify({"success": False, "message": f"Backup file not found: {backup_file}"})

    try:
        filename = os.path.basename(backup_file)
        file_size_kb = os.path.getsize(backup_file) / 1024
        
        print(f"Deleting file: {backup_file}")
        os.remove(backup_file)
        print(f"File deleted successfully")
        
        _log_action(session["user_id"], "delete", filename, file_size_kb, "success", "Backup deleted")

        conn = get_db()
        ensure_table(conn)
        push(conn, session["user_id"], "info", "Backup Deleted", f"Deleted: {filename}")
        conn.close()

        return jsonify({"success": True, "message": "Backup deleted successfully"})

    except Exception as e:
        print(f"Delete error: {str(e)}")
        _log_action(session["user_id"], "delete", backup_file, None, "failed", str(e))
        return jsonify({"success": False, "message": f"Delete error: {str(e)}"})


@backup_bp.route("/api/backup/clear-history", methods=["POST"])
def clear_history():
    """Clear all backup history for the user"""
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        user_id = session["user_id"]
        conn = get_db()
        cursor = conn.cursor()
        
        # Delete all history records for this user
        cursor.execute(
            "DELETE FROM backup_history WHERE user_id = %s",
            (user_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"History cleared for user {user_id}")
        
        # Log this action
        _log_action(user_id, "backup", "history_cleared", None, "success", "Backup history cleared")
        
        # Send notification
        conn = get_db()
        ensure_table(conn)
        push(conn, user_id, "info", "History Cleared", "All backup history has been cleared")
        conn.close()
        
        return jsonify({"success": True, "message": "History cleared successfully"})
    
    except Exception as e:
        print(f"Clear history error: {str(e)}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"})
