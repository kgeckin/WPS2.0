"""
db_utils.py
-----------
Database utility functions for WhatsApp Phishing Awareness Simulator (WPS).
Provides secure MySQL connection, CRUD for all tables, error and action logging.
All SQL operations use parameterized queries.
"""

import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# --- Database Connection ---
def get_connection():
    """
    Returns a MySQL connection using credentials from .env.
    """
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            charset="utf8mb4"
        )
        return conn
    except Error:
        # Avoid recursive logging: log_error itself opens a DB connection.
        return None

# --- Error Logging ---
def log_error(error_message: str, stack_trace: str = "", component: str = "unknown"):
    """
    Logs an error to the error_logs table.
    """
    try:
        conn = get_connection()
        if not conn:
            return
        cursor = conn.cursor()
        sql = """
            INSERT INTO error_logs (error_message, stack_trace, component)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (error_message, stack_trace, component))
        conn.commit()
    except Exception as err:
        print(f"[FATAL LOG ERROR] {err}")
    finally:
        if conn:
            conn.close()

# --- Action Logging ---
def log_action(user: str, action_type: str, affected_table: str):
    """
    Logs a user/admin action (add/edit/delete) to the action_logs table.
    """
    try:
        conn = get_connection()
        if not conn:
            return
        cursor = conn.cursor()
        sql = """
            INSERT INTO action_logs (user, action_type, affected_table)
            VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (user, action_type, affected_table))
        conn.commit()
    except Exception as err:
        log_error("Action Log Error", str(err), "db_utils")
    finally:
        if conn:
            conn.close()

# --- USERS CRUD ---
def fetch_all_users(active_only=False):
    """
    Returns all users. If active_only=True, only active users are returned.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        if active_only:
            cursor.execute("SELECT * FROM users WHERE is_active=1")
        else:
            cursor.execute("SELECT * FROM users")
        return cursor.fetchall()
    except Error as e:
        log_error("Fetch Users Error", str(e), "db_utils")
        return []
    finally:
        conn.close()

def add_user(first_name, last_name, email, phone, company_name, is_active=True, log_user="system"):
    """
    Inserts a new user.
    """
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO users (first_name, last_name, email, phone, company_name, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (first_name, last_name, email, phone, company_name, int(is_active)))
        conn.commit()
        log_action(log_user, "add", "users")
        return True
    except Error as e:
        log_error("Add User Error", str(e), "db_utils")
        return False
    finally:
        conn.close()

def update_user(user_id, first_name, last_name, email, phone, company_name, is_active, log_user="system"):
    """
    Updates a user by user_id.
    """
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        sql = """
            UPDATE users SET first_name=%s, last_name=%s, email=%s, phone=%s, company_name=%s, is_active=%s
            WHERE user_id=%s
        """
        cursor.execute(sql, (first_name, last_name, email, phone, company_name, int(is_active), user_id))
        conn.commit()
        log_action(log_user, "edit", "users")
        return True
    except Error as e:
        log_error("Update User Error", str(e), "db_utils")
        return False
    finally:
        conn.close()

def delete_user(user_id, log_user="system"):
    """
    Deletes a user by user_id.
    """
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        sql = "DELETE FROM users WHERE user_id=%s"
        cursor.execute(sql, (user_id,))
        conn.commit()
        log_action(log_user, "delete", "users")
        return True
    except Error as e:
        log_error("Delete User Error", str(e), "db_utils")
        return False
    finally:
        conn.close()

# --- CAMPAIGNS CRUD ---
def fetch_all_campaigns():
    """
    Returns all campaigns.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM campaigns")
        return cursor.fetchall()
    except Error as e:
        log_error("Fetch Campaigns Error", str(e), "db_utils")
        return []
    finally:
        conn.close()

def fetch_campaign_status():
    """
    Returns deduplicated campaign status per (user_id, campaign_id).
    Requires the SQL view v_campaign_status.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT user_id, campaign_id, clicked, opened, compromised
            FROM v_campaign_status
        """)
        return cursor.fetchall()
    except Error as e:
        log_error("Fetch Campaign Status Error", str(e), "db_utils")
        return []
    finally:
        conn.close()

def add_campaign(message, encrypted_link, log_user="system"):
    """
    Inserts a new campaign.
    """
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO campaigns (message, encrypted_link) VALUES (%s, %s)"
        cursor.execute(sql, (message, encrypted_link))
        conn.commit()
        log_action(log_user, "add", "campaigns")
        return True
    except Error as e:
        log_error("Add Campaign Error", str(e), "db_utils")
        return False
    finally:
        conn.close()

def update_campaign(campaign_id, message, encrypted_link, log_user="system"):
    """
    Updates a campaign by campaign_id.
    """
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        sql = """
            UPDATE campaigns SET message=%s, encrypted_link=%s WHERE campaign_id=%s
        """
        cursor.execute(sql, (message, encrypted_link, campaign_id))
        conn.commit()
        log_action(log_user, "edit", "campaigns")
        return True
    except Error as e:
        log_error("Update Campaign Error", str(e), "db_utils")
        return False
    finally:
        conn.close()

def delete_campaign(campaign_id, log_user="system"):
    """
    Deletes a campaign by campaign_id.
    """
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        sql = "DELETE FROM campaigns WHERE campaign_id=%s"
        cursor.execute(sql, (campaign_id,))
        conn.commit()
        log_action(log_user, "delete", "campaigns")
        return True
    except Error as e:
        log_error("Delete Campaign Error", str(e), "db_utils")
        return False
    finally:
        conn.close()

# --- CAMPAIGN_TRACKING CRUD ---
def log_campaign_tracking(user_id, campaign_id, clicked=False, opened=False, compromised=False):
    """
    Upsert campaign tracking: OR the flags on existing row, else INSERT a new row.
    """
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE campaign_tracking
               SET clicked = (clicked OR %s),
                   opened  = (opened  OR %s),
                   compromised = (compromised OR %s)
             WHERE user_id=%s AND campaign_id=%s
        """, (int(clicked), int(opened), int(compromised), user_id, campaign_id))
        if cur.rowcount == 0:
            cur.execute("""
                INSERT INTO campaign_tracking (user_id, campaign_id, clicked, opened, compromised)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, campaign_id, int(clicked), int(opened), int(compromised)))
        conn.commit()
        return True
    except Error as e:
        log_error("Campaign Tracking Upsert Error", str(e), "db_utils")
        return False
    finally:
        conn.close()

def log_error(error_message: str, stack_trace: str = "", component: str = "app") -> bool:
    """Insert an error row into error_logs."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO error_logs (error_message, stack_trace, occurred_at, component)
            VALUES (%s, %s, NOW(), %s)
        """, (error_message, stack_trace, component))
        conn.commit()
        return True
    except Error:
        return False
    finally:
        conn.close()

def fetch_campaign_tracking():
    """
    Returns all campaign tracking logs.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM campaign_tracking")
        return cursor.fetchall()
    except Error as e:
        log_error("Fetch Campaign Tracking Error", str(e), "db_utils")
        return []
    finally:
        conn.close()

# --- IMPORT_LOGS CRUD ---
def log_import(file_name, imported_by, total_rows, success_count, error_count):
    """
    Logs details about a bulk import (CSV/XLSX).
    """
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO import_logs (file_name, imported_by, total_rows, success_count, error_count)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (file_name, imported_by, total_rows, success_count, error_count))
        conn.commit()
        return True
    except Error as e:
        log_error("Log Import Error", str(e), "db_utils")
        return False
    finally:
        conn.close()

def fetch_import_logs():
    """
    Returns all import logs.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM import_logs ORDER BY import_time DESC")
        return cursor.fetchall()
    except Error as e:
        log_error("Fetch Import Logs Error", str(e), "db_utils")
        return []
    finally:
        conn.close()

# --- ERROR_LOGS / ACTION_LOGS / LOGIN_ATTEMPTS FETCH ---
def fetch_error_logs():
    """
    Returns all error logs.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM error_logs ORDER BY occurred_at DESC")
        return cursor.fetchall()
    except Error as e:
        log_error("Fetch Error Logs Error", str(e), "db_utils")
        return []
    finally:
        conn.close()

def fetch_action_logs():
    """
    Returns all action logs.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM action_logs ORDER BY timestamp DESC")
        return cursor.fetchall()
    except Error as e:
        log_error("Fetch Action Logs Error", str(e), "db_utils")
        return []
    finally:
        conn.close()

def log_login_attempt(user_id, campaign_id, *_ignored_legacy_fields):
    """Record exercise metadata only. Legacy credential arguments are discarded."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO login_attempts (user_id, campaign_id) VALUES (%s, %s)",
            (int(user_id), int(campaign_id)),
        )
        conn.commit()
        return True
    except Error:
        return False
    finally:
        conn.close()

def fetch_login_attempts():
    """
    Returns all login attempts.
    """
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT attempt_id, user_id, campaign_id, timestamp FROM login_attempts ORDER BY timestamp DESC")
        return cursor.fetchall()
    except Error as e:
        log_error("Fetch Login Attempts Error", str(e), "db_utils")
        return []
    finally:
        conn.close()
