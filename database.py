import sqlite3


DATABASE_NAME = "chatlite.db"


# =========================================
# DATABASE CONNECTION
# =========================================

def connect_db():

    return sqlite3.connect(
        DATABASE_NAME
    )


# =========================================
# CREATE DATABASE
# =========================================

def create_database():

    connection = connect_db()
    cursor = connection.cursor()

    # =====================================
    # USERS
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL UNIQUE,

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # =====================================
    # MESSAGES
    # =====================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            message_id TEXT UNIQUE,

            sender TEXT NOT NULL,

            receiver TEXT NOT NULL,

            message TEXT NOT NULL,

            status TEXT NOT NULL
            DEFAULT 'sent',

            created_at TIMESTAMP
            DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # =====================================
    # INDEXES
    # =====================================

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_messages_sender_receiver

        ON messages (
            sender,
            receiver
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_messages_receiver_sender

        ON messages (
            receiver,
            sender
        )
        """
    )

    connection.commit()
    connection.close()


# =========================================
# CREATE USER
# =========================================

def create_user(
    username
):

    username = str(
        username or ""
    ).strip()

    if not username:

        return False

    connection = connect_db()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO users (
                username
            )

            VALUES (?)
            """,
            (
                username,
            )
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError:

        return False

    finally:

        connection.close()


# =========================================
# CHECK USER
# =========================================

def user_exists(
    username
):

    username = str(
        username or ""
    ).strip()

    if not username:

        return False

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id

        FROM users

        WHERE username = ?
        """,
        (
            username,
        )
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


# =========================================
# GET ALL USERS
# =========================================

def get_users():

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT username

        FROM users

        ORDER BY username ASC
        """
    )

    users = [
        row[0]
        for row in cursor.fetchall()
    ]

    connection.close()

    return users


# =========================================
# SAVE MESSAGE
# =========================================

def save_message(
    message_id,
    sender,
    receiver,
    message,
    status="sent"
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO messages (

            message_id,
            sender,
            receiver,
            message,
            status

        )

        VALUES (?, ?, ?, ?, ?)
        """,
        (
            message_id,
            sender,
            receiver,
            message,
            status
        )
    )

    connection.commit()

    connection.close()


# =========================================
# UPDATE MESSAGE STATUS
# =========================================

def update_message_status(
    message_id,
    status
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE messages

        SET status = ?

        WHERE message_id = ?
        """,
        (
            status,
            message_id
        )
    )

    connection.commit()

    connection.close()


# =========================================
# GET MESSAGE STATUS
# =========================================

def get_message_status(
    message_id
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT status

        FROM messages

        WHERE message_id = ?
        """,
        (
            message_id,
        )
    )

    result = cursor.fetchone()

    connection.close()

    if result is None:

        return None

    return result[0]


# =========================================
# GET CHAT HISTORY
# =========================================

def get_messages(
    username,
    other_user
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            message_id,
            sender,
            receiver,
            message,
            status,
            created_at

        FROM messages

        WHERE

            (
                sender = ?
                AND receiver = ?
            )

            OR

            (
                sender = ?
                AND receiver = ?
            )

        ORDER BY id ASC
        """,
        (
            username,
            other_user,
            other_user,
            username
        )
    )

    messages = cursor.fetchall()

    connection.close()

    return messages


# =========================================
# GET LAST MESSAGE
# =========================================

def get_last_message(
    username,
    other_user
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            message,
            created_at

        FROM messages

        WHERE

            (
                sender = ?
                AND receiver = ?
            )

            OR

            (
                sender = ?
                AND receiver = ?
            )

        ORDER BY id DESC

        LIMIT 1
        """,
        (
            username,
            other_user,
            other_user,
            username
        )
    )

    result = cursor.fetchone()

    connection.close()

    return result


# =========================================
# GET CHAT USERS
# =========================================

def get_chat_users(
    username
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT DISTINCT

            CASE

                WHEN sender = ?
                THEN receiver

                ELSE sender

            END AS other_user

        FROM messages

        WHERE

            sender = ?

            OR receiver = ?

        ORDER BY other_user ASC
        """,
        (
            username,
            username,
            username
        )
    )

    users = [
        row[0]
        for row in cursor.fetchall()
    ]

    connection.close()

    return users


# =========================================
# GET UNREAD COUNT
# =========================================

def get_unread_count(
    username,
    other_user
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)

        FROM messages

        WHERE

            sender = ?

            AND receiver = ?

            AND status != 'read'
        """,
        (
            other_user,
            username
        )
    )

    result = cursor.fetchone()

    connection.close()

    return result[0]


# =========================================
# MARK CHAT AS READ
# =========================================

def mark_chat_as_read(
    username,
    other_user
):

    connection = connect_db()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE messages

        SET status = 'read'

        WHERE

            sender = ?

            AND receiver = ?

            AND status != 'read'
        """,
        (
            other_user,
            username
        )
    )

    connection.commit()

    connection.close()