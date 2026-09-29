import asyncio
import json
import os

import websockets

from database import (
    create_database,
    create_user,
    user_exists,
    save_message,
    update_message_status,
    get_message_status,
    get_messages,
    get_chat_users,
    get_unread_count,
    mark_chat_as_read
)


# =========================================
# CONNECTED USERS
# =========================================

connected_users = {}


# =========================================
# SEND JSON
# =========================================

async def send_json(
    websocket,
    data
):

    try:

        await websocket.send(
            json.dumps(
                data,
                ensure_ascii=False
            )
        )

        return True

    except Exception:

        return False


# =========================================
# SEND TO USER
# =========================================

async def send_to_user(
    username,
    data
):

    websocket = connected_users.get(
        username
    )

    if websocket is None:

        return False

    return await send_json(
        websocket,
        data
    )


# =========================================
# LOGIN / CONNECT
# =========================================

async def login_user(
    websocket,
    username
):

    username = str(
        username or ""
    ).strip()

    if not username:

        await send_json(
            websocket,
            {
                "type": "login_failed",
                "message": "Username is required"
            }
        )

        return False

    if len(username) < 3:

        await send_json(
            websocket,
            {
                "type": "login_failed",
                "message": "Username must be at least 3 characters"
            }
        )

        return False

    if len(username) > 30:

        await send_json(
            websocket,
            {
                "type": "login_failed",
                "message": "Username is too long"
            }
        )

        return False

    if username in connected_users:

        await send_json(
            websocket,
            {
                "type": "login_failed",
                "message": "This username is already online"
            }
        )

        return False

    if not user_exists(
        username
    ):

        created = create_user(
            username
        )

        if not created:

            await send_json(
                websocket,
                {
                    "type": "login_failed",
                    "message": "Could not create user"
                }
            )

            return False

        print(
            f"[NEW USER] {username}"
        )

    connected_users[
        username
    ] = websocket

    await send_json(
        websocket,
        {
            "type": "login_success",
            "username": username
        }
    )

    print(
        f"[ONLINE] {username}"
    )

    await broadcast_user_status(
        username,
        True
    )

    return True


# =========================================
# BROADCAST USER STATUS
# =========================================

async def broadcast_user_status(
    username,
    online
):

    data = {
        "type": "user_status",
        "username": username,
        "online": online
    }

    for other_username, websocket in list(
        connected_users.items()
    ):

        if other_username == username:
            continue

        await send_json(
            websocket,
            data
        )


# =========================================
# LOAD CHAT HISTORY
# =========================================

async def handle_load_chat(
    websocket,
    username,
    other_user
):

    other_user = str(
        other_user or ""
    ).strip()

    if not other_user:
        return

    messages = get_messages(
        username,
        other_user
    )

    for message_data in messages:

        (
            message_id,
            sender,
            receiver,
            message,
            status,
            created_at
        ) = message_data

        await send_json(
            websocket,
            {
                "type": "history_message",
                "message_id": message_id,
                "from": sender,
                "to": receiver,
                "message": message,
                "status": status,
                "created_at": created_at
            }
        )

    mark_chat_as_read(
        username,
        other_user
    )

    await send_to_user(
        other_user,
        {
            "type": "messages_read",
            "by": username
        }
    )

    await send_json(
        websocket,
        {
            "type": "history_end"
        }
    )


# =========================================
# SEND NEW MESSAGE
# =========================================

async def handle_new_message(
    websocket,
    username,
    data
):

    receiver = str(
        data.get(
            "to",
            ""
        )
    ).strip()

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    message_id = str(
        data.get(
            "message_id",
            ""
        )
    ).strip()

    if not receiver:

        await send_json(
            websocket,
            {
                "type": "send_failed",
                "message_id": message_id,
                "message": "Receiver is required"
            }
        )

        return

    if not message:
        return

    if not message_id:

        await send_json(
            websocket,
            {
                "type": "send_failed",
                "message": "Message ID is required"
            }
        )

        return

    if len(message) > 5000:

        await send_json(
            websocket,
            {
                "type": "send_failed",
                "message_id": message_id,
                "message": "Message is too long"
            }
        )

        return

    if receiver == username:

        await send_json(
            websocket,
            {
                "type": "send_failed",
                "message_id": message_id,
                "message": "You cannot message yourself"
            }
        )

        return

    existing_status = get_message_status(
        message_id
    )

    if existing_status is not None:

        await send_json(
            websocket,
            {
                "type": "message_status",
                "message_id": message_id,
                "status": existing_status
            }
        )

        return

    if not user_exists(
        receiver
    ):

        await send_json(
            websocket,
            {
                "type": "send_failed",
                "message_id": message_id,
                "message": "User does not exist"
            }
        )

        return

    save_message(
        message_id,
        username,
        receiver,
        message,
        "sent"
    )

    receiver_online = (
        receiver in connected_users
    )

    if receiver_online:

        delivered = await send_to_user(
            receiver,
            {
                "type": "message",
                "message_id": message_id,
                "from": username,
                "to": receiver,
                "message": message,
                "status": "delivered"
            }
        )

        if delivered:

            update_message_status(
                message_id,
                "delivered"
            )

            await send_json(
                websocket,
                {
                    "type": "message_status",
                    "message_id": message_id,
                    "status": "delivered"
                }
            )

            print(
                f"[DELIVERED] "
                f"{username} -> "
                f"{receiver}: "
                f"{message}"
            )

            return

    await send_json(
        websocket,
        {
            "type": "message_status",
            "message_id": message_id,
            "status": "sent"
        }
    )

    print(
        f"[OFFLINE] "
        f"{username} -> "
        f"{receiver}: "
        f"{message}"
    )


# =========================================
# MARK CHAT AS READ
# =========================================

async def handle_mark_read(
    websocket,
    username,
    other_user
):

    other_user = str(
        other_user or ""
    ).strip()

    if not other_user:
        return

    mark_chat_as_read(
        username,
        other_user
    )

    await send_to_user(
        other_user,
        {
            "type": "messages_read",
            "by": username
        }
    )


# =========================================
# GET CHAT LIST
# =========================================

async def handle_get_chats(
    websocket,
    username
):

    users = get_chat_users(
        username
    )

    chats = []

    for other_user in users:

        unread_count = get_unread_count(
            username,
            other_user
        )

        chats.append(
            {
                "username": other_user,
                "online": (
                    other_user
                    in connected_users
                ),
                "unread": unread_count
            }
        )

    await send_json(
        websocket,
        {
            "type": "chat_list",
            "chats": chats
        }
    )


# =========================================
# HANDLE CLIENT
# =========================================

async def handle_client(
    websocket
):

    username = None

    try:

        raw_data = await websocket.recv()

        try:

            data = json.loads(
                raw_data
            )

        except json.JSONDecodeError:

            await send_json(
                websocket,
                {
                    "type": "error",
                    "message": "Invalid JSON"
                }
            )

            return

        if data.get("type") != "login":

            await send_json(
                websocket,
                {
                    "type": "error",
                    "message": "Login required"
                }
            )

            return

        username = str(
            data.get(
                "username",
                ""
            )
        ).strip()

        logged_in = await login_user(
            websocket,
            username
        )

        if not logged_in:
            return

        async for raw_data in websocket:

            try:

                data = json.loads(
                    raw_data
                )

            except json.JSONDecodeError:

                await send_json(
                    websocket,
                    {
                        "type": "error",
                        "message": "Invalid JSON"
                    }
                )

                continue

            request_type = data.get(
                "type"
            )

            if request_type == "load_chat":

                await handle_load_chat(
                    websocket,
                    username,
                    data.get("with")
                )

            elif request_type == "message":

                await handle_new_message(
                    websocket,
                    username,
                    data
                )

            elif request_type == "mark_read":

                await handle_mark_read(
                    websocket,
                    username,
                    data.get("with")
                )

            elif request_type == "get_chats":

                await handle_get_chats(
                    websocket,
                    username
                )

            elif request_type == "ping":

                await send_json(
                    websocket,
                    {
                        "type": "pong"
                    }
                )

            else:

                await send_json(
                    websocket,
                    {
                        "type": "error",
                        "message": "Unknown request"
                    }
                )

    except websockets.exceptions.ConnectionClosed:
        pass

    except Exception as e:

        print(
            f"[ERROR] {e}"
        )

    finally:

        if (
            username
            and connected_users.get(
                username
            ) == websocket
        ):

            del connected_users[
                username
            ]

            print(
                f"[OFFLINE] {username}"
            )

            await broadcast_user_status(
                username,
                False
            )


# =========================================
# SERVER MAIN
# =========================================

async def main():

    create_database()

    port = int(
        os.environ.get(
            "PORT",
            "8765"
        )
    )

    print(
        "========================================"
    )

    print(
        "           ChatLite Server"
    )

    print(
        "========================================"
    )

    print(
        "Database ready"
    )

    print(
        f"Server started on port {port}"
    )

    print(
        "Waiting for connections..."
    )

    print(
        "Username-only mode"
    )

    print(
        "========================================"
    )

    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        port,
        ping_interval=20,
        ping_timeout=20,
        max_size=1024 * 1024
    ):

        await asyncio.Future()


# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\nServer stopped."
        )