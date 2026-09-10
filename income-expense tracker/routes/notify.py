"""
=============================================
  Shared notification helper
  Used by all routes to push notifications
=============================================
"""

from config.database import get_db


def push(conn, user_id: int, ntype: str, title: str, message: str):
    """
    Insert a notification. Skips duplicates with the same title
    created today to avoid spam.
    ntype: 'info' | 'success' | 'warning' | 'error'
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id FROM notifications
            WHERE user_id=%s AND title=%s AND DATE(created_at)=CURDATE()
            LIMIT 1
        """, (user_id, title))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO notifications (user_id, type, title, message) VALUES (%s,%s,%s,%s)",
                (user_id, ntype, title, message)
            )
            conn.commit()
    except Exception:
        pass  # Never crash the main action because of a notification failure
    finally:
        cursor.close()


def ensure_table(conn):
    """Create notifications table if missing."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id    INT UNSIGNED NOT NULL,
            type       ENUM('info','success','warning','error') NOT NULL DEFAULT 'info',
            title      VARCHAR(150) NOT NULL,
            message    TEXT         NOT NULL,
            is_read    TINYINT(1)   NOT NULL DEFAULT 0,
            created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit()
    cursor.close()
