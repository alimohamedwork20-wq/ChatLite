id="c1k7vs"
import asyncio
import json
import threading
import uuid

import websockets

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from chat_bubble import ChatBubble


# =========================================
# SERVER
# =========================================

SERVER_URL = "ws://hat-ite-c03a3e.subhub.tr"


class ChatLiteApp(App):

    # =====================================
    # BUILD
    # =====================================

    def build(self):

        self.title = "ChatLite"

        self.websocket = None
        self.loop = None

        self.username = ""

        self.connected = False
        self.connecting = False

        self.current_chat = ""

        # =================================
        # CHATS
        # =================================

        self.chats = {}

        # =================================
        # MESSAGE STATES
        # =================================

        self.message_states = {}

        # =================================
        # READ MESSAGES
        # =================================

        self.read_message_ids = set()

        # =================================
        # ROOT
        # =================================

        self.root_layout = BoxLayout(
            orientation="vertical"
        )

        self.show_login_screen()

        return self.root_layout

    # =========================================
    # LOGIN SCREEN
    # =========================================

    def show_login_screen(self):

        self.root_layout.clear_widgets()

        screen = BoxLayout(
            orientation="vertical",
            padding=30,
            spacing=15
        )

        screen.add_widget(
            Widget()
        )

        title = Label(
            text="ChatLite",
            font_size=34,
            size_hint_y=None,
            height=60
        )

        subtitle = Label(
            text="Simple and private messaging",
            font_size=16,
            size_hint_y=None,
            height=35
        )

        self.username_input = TextInput(
            hint_text="Username",
            multiline=False,
            size_hint_y=None,
            height=50,
            padding=(15, 15)
        )

        self.username_input.bind(
            on_text_validate=self.start_connection
        )

        self.connect_button = Button(
            text="Connect",
            size_hint_y=None,
            height=50
        )

        self.connect_button.bind(
            on_press=self.start_connection
        )

        self.login_status = Label(
            text="",
            size_hint_y=None,
            height=40
        )

        screen.add_widget(
            title
        )

        screen.add_widget(
            subtitle
        )

        screen.add_widget(
            self.username_input
        )

        screen.add_widget(
            self.connect_button
        )

        screen.add_widget(
            self.login_status
        )

        screen.add_widget(
            Widget()
        )

        self.root_layout.add_widget(
            screen
        )

    # =========================================
    # CHATS SCREEN
    # =========================================

    def show_chats_screen(self):

        self.root_layout.clear_widgets()

        main = BoxLayout(
            orientation="vertical",
            padding=10,
            spacing=10
        )

        # =====================================
        # HEADER
        # =====================================

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=55
        )

        title = Label(
            text="Chats",
            font_size=25,
            halign="left",
            valign="middle"
        )

        title.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        user_label = Label(
            text=self.username,
            size_hint_x=None,
            width=120,
            halign="right",
            valign="middle"
        )

        user_label.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        header.add_widget(
            title
        )

        header.add_widget(
            user_label
        )

        # =====================================
        # SEARCH
        # =====================================

        self.chat_search = TextInput(
            hint_text="Search chats...",
            multiline=False,
            size_hint_y=None,
            height=45,
            padding=(12, 12)
        )

        self.chat_search.bind(
            text=self.refresh_chat_list
        )

        # =====================================
        # CHAT LIST
        # =====================================

        self.chat_scroll = ScrollView()

        self.chat_list = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=8
        )

        self.chat_list.bind(
            minimum_height=
            self.chat_list.setter(
                "height"
            )
        )

        self.chat_scroll.add_widget(
            self.chat_list
        )

        # =====================================
        # NEW CHAT
        # =====================================

        new_chat_button = Button(
            text="New Chat",
            size_hint_y=None,
            height=50
        )

        new_chat_button.bind(
            on_press=self.show_chat_selection
        )

        main.add_widget(
            header
        )

        main.add_widget(
            self.chat_search
        )

        main.add_widget(
            self.chat_scroll
        )

        main.add_widget(
            new_chat_button
        )

        self.root_layout.add_widget(
            main
        )

        self.refresh_chat_list()

        # =====================================
        # GET CHATS FROM SERVER
        # =====================================

        Clock.schedule_once(
            lambda dt:
            self.request_chat_list(),
            0.2
        )

    # =========================================
    # REQUEST CHAT LIST
    # =========================================

    def request_chat_list(self):

        if self.websocket is None:
            return

        if self.loop is None:
            return

        data = {
            "type": "get_chats"
        }

        try:

            asyncio.run_coroutine_threadsafe(
                self.websocket.send(
                    json.dumps(data)
                ),
                self.loop
            )

        except Exception as e:

            print(
                "Chat list error:",
                e
            )

    # =========================================
    # REFRESH CHAT LIST
    # =========================================

    def refresh_chat_list(
        self,
        *args
    ):

        if not hasattr(
            self,
            "chat_list"
        ):

            return

        self.chat_list.clear_widgets()

        search = ""

        if hasattr(
            self,
            "chat_search"
        ):

            search = (
                self.chat_search.text
                .strip()
                .lower()
            )

        names = list(
            self.chats.keys()
        )

        names.sort(
            key=lambda name:
            self.chats[name].get(
                "last_time",
                ""
            ),
            reverse=True
        )

        for name in names:

            if search:

                if search not in name.lower():

                    continue

            info = self.chats[name]

            last_message = info.get(
                "last_message",
                ""
            )

            online = info.get(
                "online",
                False
            )

            unread = info.get(
                "unread",
                0
            )

            status = (
                "Online"
                if online
                else "Offline"
            )

            if unread > 0:

                unread_text = (
                    f"  ({unread})"
                )

            else:

                unread_text = ""

            button = Button(
                text=(
                    f"{name}  •  {status}"
                    f"\n{last_message}"
                    f"{unread_text}"
                ),
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=70
            )

            button.bind(
                on_press=lambda instance,
                username=name:
                self.open_chat(username)
            )

            self.chat_list.add_widget(
                button
            )

        if not self.chat_list.children:

            empty = Label(
                text="No chats yet",
                size_hint_y=None,
                height=60
            )

            self.chat_list.add_widget(
                empty
            )

    # =========================================
    # CHAT SELECTION
    # =========================================

    def show_chat_selection(
        self,
        instance=None
    ):

        self.root_layout.clear_widgets()

        screen = BoxLayout(
            orientation="vertical",
            padding=20,
            spacing=12
        )

        title = Label(
            text="Who do you want to chat with?",
            font_size=22,
            size_hint_y=None,
            height=60
        )

        self.chat_user_input = TextInput(
            hint_text="Enter username",
            multiline=False,
            size_hint_y=None,
            height=50,
            padding=(12, 12)
        )

        self.chat_user_input.bind(
            on_text_validate=self.open_selected_chat
        )

        open_button = Button(
            text="Open Chat",
            size_hint_y=None,
            height=50
        )

        open_button.bind(
            on_press=self.open_selected_chat
        )

        back_button = Button(
            text="Back",
            size_hint_y=None,
            height=50
        )

        back_button.bind(
            on_press=lambda instance:
            self.show_chats_screen()
        )

        screen.add_widget(
            Widget()
        )

        screen.add_widget(
            title
        )

        screen.add_widget(
            self.chat_user_input
        )

        screen.add_widget(
            open_button
        )

        screen.add_widget(
            back_button
        )

        screen.add_widget(
            Widget()
        )

        self.root_layout.add_widget(
            screen
        )

    # =========================================
    # OPEN SELECTED CHAT
    # =========================================

    def open_selected_chat(
        self,
        instance=None
    ):

        username = (
            self.chat_user_input.text.strip()
        )

        if not username:

            return

        if username == self.username:

            return

        self.open_chat(
            username
        )

    # =========================================
    # OPEN CHAT
    # =========================================

    def open_chat(
        self,
        username
    ):

        username = username.strip()

        if not username:

            return

        if username == self.username:

            return

        self.current_chat = username

        if username not in self.chats:

            self.chats[username] = {
                "last_message": "",
                "last_time": "",
                "online": False,
                "unread": 0
            }

        self.chats[
            username
        ]["unread"] = 0

        self.show_chat_screen()

    # =========================================
    # CHAT SCREEN
    # =========================================

    def show_chat_screen(self):

        self.root_layout.clear_widgets()

        main = BoxLayout(
            orientation="vertical"
        )

        # =====================================
        # HEADER
        # =====================================

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=60,
            padding=(5, 5),
            spacing=8
        )

        back_button = Button(
            text="<",
            size_hint_x=None,
            width=45
        )

        back_button.bind(
            on_press=lambda instance:
            self.show_chats_screen()
        )

        title_box = BoxLayout(
            orientation="vertical"
        )

        title = Label(
            text=self.current_chat,
            font_size=20,
            halign="left",
            valign="middle"
        )

        title.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        online = self.chats.get(
            self.current_chat,
            {}
        ).get(
            "online",
            False
        )

        status = Label(
            text=(
                "Online"
                if online
                else "Offline"
            ),
            font_size=12,
            halign="left",
            valign="middle"
        )

        status.bind(
            size=lambda instance, value:
            setattr(
                instance,
                "text_size",
                value
            )
        )

        self.chat_status_label = status

        title_box.add_widget(
            title
        )

        title_box.add_widget(
            status
        )

        header.add_widget(
            back_button
        )

        header.add_widget(
            title_box
        )

        # =====================================
        # MESSAGES
        # =====================================

        self.scroll_view = ScrollView()

        self.messages_layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=8,
            padding=8
        )

        self.messages_layout.bind(
            minimum_height=
            self.messages_layout.setter(
                "height"
            )
        )

        self.scroll_view.add_widget(
            self.messages_layout
        )

        # =====================================
        # MESSAGE INPUT
        # =====================================

        message_area = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=60,
            padding=(5, 5),
            spacing=8
        )

        self.message_input = TextInput(
            hint_text="Type a message...",
            multiline=False,
            padding=(12, 12)
        )

        self.message_input.bind(
            on_text_validate=self.send_message
        )

        self.send_button = Button(
            text="Send",
            size_hint_x=None,
            width=85
        )

        self.send_button.bind(
            on_press=self.send_message
        )

        message_area.add_widget(
            self.message_input
        )

        message_area.add_widget(
            self.send_button
        )

        main.add_widget(
            header
        )

        main.add_widget(
            self.scroll_view
        )

        main.add_widget(
            message_area
        )

        self.root_layout.add_widget(
            main
        )

        # =====================================
        # LOAD HISTORY
        # =====================================

        Clock.schedule_once(
            lambda dt:
            self.load_chat_history(
                self.current_chat
            ),
            0.2
        )

    # =========================================
    # NETWORK THREAD
    # =========================================

    def network_thread(self):

        self.loop = asyncio.new_event_loop()

        asyncio.set_event_loop(
            self.loop
        )

        try:

            self.loop.run_until_complete(
                self.connect_to_server()
            )

        except Exception as e:

            print(
                "Network thread error:",
                e
            )

        finally:

            try:

                self.loop.close()

            except Exception:

                pass

    # =========================================
    # START CONNECTION
    # =========================================

    def start_connection(
        self,
        instance=None
    ):

        if self.connecting:

            return

        if self.websocket is not None:

            return

        username = (
            self.username_input.text.strip()
        )

        if not username:

            self.login_status.text = (
                "Enter a username"
            )

            return

        if len(username) < 3:

            self.login_status.text = (
                "Username must be at least 3 characters"
            )

            return

        self.username = username

        self.connecting = True

        self.login_status.text = (
            "Connecting..."
        )

        self.connect_button.disabled = True

        thread = threading.Thread(
            target=self.network_thread,
            daemon=True
        )

        thread.start()

    # =========================================
    # CONNECT TO SERVER
    # =========================================

    async def connect_to_server(self):

        try:

            self.websocket = (
                await websockets.connect(
                    SERVER_URL,
                    ping_interval=20,
                    ping_timeout=20
                )
            )

            await self.websocket.send(
                json.dumps(
                    {
                        "type": "login",
                        "username": self.username
                    }
                )
            )

            self.connected = True
            self.connecting = False

            while True:

                raw_data = (
                    await self.websocket.recv()
                )

                data = json.loads(
                    raw_data
                )

                Clock.schedule_once(
                    lambda dt, d=data:
                    self.handle_server_message(d)
                )

        except Exception as e:

            print(
                "Network error:",
                e
            )

            self.websocket = None
            self.connected = False
            self.connecting = False

            Clock.schedule_once(
                lambda dt:
                self.connection_lost()
            )

    # =========================================
    # CONNECTION LOST
    # =========================================

    def connection_lost(self):

        if hasattr(
            self,
            "connect_button"
        ):

            self.connect_button.disabled = False

        if hasattr(
            self,
            "login_status"
        ):

            self.login_status.text = (
                "Connection lost"
            )

    # =========================================
    # HANDLE SERVER MESSAGE
    # =========================================

    def handle_server_message(
        self,
        data
    ):

        message_type = data.get(
            "type"
        )

        # =====================================
        # LOGIN SUCCESS
        # =====================================

        if message_type == "login_success":

            self.connected = True
            self.connecting = False

            self.show_chats_screen()

        # =====================================
        # LOGIN FAILED
        # =====================================

        elif message_type == "login_failed":

            self.connected = False
            self.connecting = False
            self.websocket = None

            if hasattr(
                self,
                "connect_button"
            ):

                self.connect_button.disabled = False

            if hasattr(
                self,
                "login_status"
            ):

                self.login_status.text = data.get(
                    "message",
                    "Login failed"
                )

        # =====================================
        # NEW MESSAGE
        # =====================================

        elif message_type == "message":

            sender = data.get(
                "from",
                ""
            )

            receiver = data.get(
                "to",
                ""
            )

            message = data.get(
                "message",
                ""
            )

            message_id = data.get(
                "message_id",
                ""
            )

            status = data.get(
                "status",
                "delivered"
            )

            # =================================
            # UPDATE CHAT INFO
            # =================================

            if sender not in self.chats:

                self.chats[sender] = {
                    "last_message": "",
                    "last_time": "",
                    "online": True,
                    "unread": 0
                }

            self.chats[
                sender
            ]["last_message"] = message

            self.chats[
                sender
            ]["online"] = True

            # =================================
            # CURRENT CHAT
            # =================================

            if (
                self.current_chat == sender
            ):

                self.add_message(
                    sender,
                    message,
                    False,
                    message_id,
                    status
                )

                Clock.schedule_once(
                    self.scroll_to_bottom,
                    0.1
                )

                # Mark as read

                self.send_mark_read(
                    sender
                )

            else:

                self.chats[
                    sender
                ]["unread"] = (
                    self.chats[
                        sender
                    ].get(
                        "unread",
                        0
                    ) + 1
                )

            self.refresh_chat_list()

        # =====================================
        # HISTORY
        # =====================================

        elif message_type == "history_message":

            sender = data.get(
                "from",
                ""
            )

            receiver = data.get(
                "to",
                ""
            )

            message = data.get(
                "message",
                ""
            )

            message_id = data.get(
                "message_id",
                ""
            )

            status = data.get(
                "status",
                "sent"
            )

            if not self.current_chat:

                return

            if (
                sender != self.current_chat
                and receiver != self.current_chat
            ):

                return

            is_me = (
                sender == self.username
            )

            self.add_message(
                sender,
                message,
                is_me,
                message_id,
                status
            )

        elif message_type == "history_end":

            Clock.schedule_once(
                self.scroll_to_bottom,
                0.1
            )

        # =====================================
        # MESSAGE STATUS
        # =====================================

        elif message_type == "message_status":

            message_id = data.get(
                "message_id"
            )

            status = data.get(
                "status",
                "sent"
            )

            self.message_states[
                message_id
            ] = status

            self.update_message_status_ui(
                message_id,
                status
            )

        # =====================================
        # MESSAGES READ
        # =====================================

        elif message_type == "messages_read":

            self.mark_messages_as_read()

        # =====================================
        # USER STATUS
        # =====================================

        elif message_type == "user_status":

            username = data.get(
                "username",
                ""
            )

            online = data.get(
                "online",
                False
            )

            if username not in self.chats:

                self.chats[username] = {
                    "last_message": "",
                    "last_time": "",
                    "online": online,
                    "unread": 0
                }

            else:

                self.chats[
                    username
                ]["online"] = online

            # Current chat header

            if (
                username == self.current_chat
                and hasattr(
                    self,
                    "chat_status_label"
                )
            ):

                self.chat_status_label.text = (
                    "Online"
                    if online
                    else "Offline"
                )

            self.refresh_chat_list()

        # =====================================
        # CHAT LIST
        # =====================================

        elif message_type == "chat_list":

            chats = data.get(
                "chats",
                []
            )

            for chat in chats:

                username = chat.get(
                    "username",
                    ""
                )

                if not username:

                    continue

                self.chats[username] = {
                    "last_message":
                    self.chats.get(
                        username,
                        {}
                    ).get(
                        "last_message",
                        ""
                    ),

                    "last_time":
                    self.chats.get(
                        username,
                        {}
                    ).get(
                        "last_time",
                        ""
                    ),

                    "online":
                    chat.get(
                        "online",
                        False
                    ),

                    "unread":
                    chat.get(
                        "unread",
                        0
                    )
                }

            self.refresh_chat_list()

        # =====================================
        # SEND FAILED
        # =====================================

        elif message_type == "send_failed":

            print(
                "Send failed:",
                data.get(
                    "message",
                    "Unknown error"
                )
            )

        # =====================================
        # ERROR
        # =====================================

        elif message_type == "error":

            print(
                "Server error:",
                data.get(
                    "message",
                    "Unknown error"
                )
            )

    # =========================================
    # ADD MESSAGE
    # =========================================

    def add_message(
        self,
        sender,
        message,
        is_me,
        message_id="",
        status="sent"
    ):

        # =====================================
        # PREVENT DUPLICATES IN UI
        # =====================================

        if message_id:

            for child in self.messages_layout.children:

                if getattr(
                    child,
                    "message_id",
                    ""
                ) == message_id:

                    return

        bubble = ChatBubble(
            sender,
            message,
            is_me=is_me
        )

        # =====================================
        # STATUS LABEL
        # =====================================

        if is_me:

            status_label = Label(
                text=self.get_status_text(
                    status
                ),
                color=(0, 0, 0, 1),
                font_size=10,
                size_hint_y=None,
                height=18,
                halign="right",
                valign="middle"
            )

            status_label.bind(
                size=lambda instance, value:
                setattr(
                    instance,
                    "text_size",
                    value
                )
            )

            bubble.add_widget(
                status_label
            )

            bubble.status_label = (
                status_label
            )

        # =====================================
        # ROW
        # =====================================

        row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            spacing=8,
            padding=(5, 3)
        )

        if is_me:

            row.add_widget(
                Widget(
                    size_hint_x=0.25
                )
            )

            row.add_widget(
                bubble
            )

        else:

            row.add_widget(
                bubble
            )

            row.add_widget(
                Widget(
                    size_hint_x=0.25
                )
            )

        # =====================================
        # MESSAGE ID
        # =====================================

        row.message_id = message_id

        row.message_status = status

        # =====================================
        # HEIGHT
        # =====================================

        def update_height(
            instance,
            value
        ):

            row.height = (
                bubble.height + 6
            )

        bubble.bind(
            height=update_height
        )

        row.height = (
            bubble.height + 6
        )

        self.messages_layout.add_widget(
            row
        )

        if message_id:

            self.message_states[
                message_id
            ] = status

    # =========================================
    # STATUS TEXT
    # =========================================

    def get_status_text(
        self,
        status
    ):

        if status == "read":

            return "Read"

        if status == "delivered":

            return "Delivered"

        return "Sent"

    # =========================================
    # UPDATE MESSAGE STATUS UI
    # =========================================

    def update_message_status_ui(
        self,
        message_id,
        status
    ):

        if not hasattr(
            self,
            "messages_layout"
        ):

            return

        for row in self.messages_layout.children:

            if getattr(
                row,
                "message_id",
                ""
            ) == message_id:

                row.message_status = status

                bubble = (
                    row.children[0]
                )

                if hasattr(
                    bubble,
                    "status_label"
                ):

                    bubble.status_label.text = (
                        self.get_status_text(
                            status
                        )
                    )

                return

    # =========================================
    # MARK ALL MY MESSAGES AS READ
    # =========================================

    def mark_messages_as_read(self):

        if not hasattr(
            self,
            "messages_layout"
        ):

            return

        for row in self.messages_layout.children:

            if getattr(
                row,
                "message_status",
                ""
            ) in (
                "sent",
                "delivered"
            ):

                row.message_status = "read"

                bubble = row.children[0]

                if hasattr(
                    bubble,
                    "status_label"
                ):

                    bubble.status_label.text = "Read"

    # =========================================
    # LOAD HISTORY
    # =========================================

    def load_chat_history(
        self,
        username
    ):

        if self.websocket is None:

            return

        if self.loop is None:

            return

        self.messages_layout.clear_widgets()

        data = {
            "type": "load_chat",
            "with": username
        }

        try:

            asyncio.run_coroutine_threadsafe(
                self.websocket.send(
                    json.dumps(
                        data,
                        ensure_ascii=False
                    )
                ),
                self.loop
            )

        except Exception as e:

            print(
                "History error:",
                e
            )

    # =========================================
    # MARK READ
    # =========================================

    def send_mark_read(
        self,
        username
    ):

        if self.websocket is None:

            return

        if self.loop is None:

            return

        data = {
            "type": "mark_read",
            "with": username
        }

        try:

            asyncio.run_coroutine_threadsafe(
                self.websocket.send(
                    json.dumps(data),
                    ),
                self.loop
            )

        except Exception as e:

            print(
                "Read error:",
                e
            )

    # =========================================
    # SEND MESSAGE
    # =========================================

    def send_message(
        self,
        instance=None
    ):

        if self.websocket is None:

            return

        if self.loop is None:

            return

        if not self.connected:

            return

        if not self.current_chat:

            return

        message = (
            self.message_input.text.strip()
        )

        if not message:

            return

        # =====================================
        # MESSAGE ID
        # =====================================

        message_id = str(
            uuid.uuid4()
        )

        data = {
            "type": "message",
            "to": self.current_chat,
            "message": message,
            "message_id": message_id
        }

        try:

            future = (
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(
                        json.dumps(
                            data,
                            ensure_ascii=False
                        )
                    ),
                    self.loop
                )
            )

            future.result(
                timeout=5
            )

            # =================================
            # ADD TO UI IMMEDIATELY
            # =================================

            self.add_message(
                self.username,
                message,
                True,
                message_id,
                "sent"
            )

            # =================================
            # UPDATE CHAT
            # =================================

            if self.current_chat not in self.chats:

                self.chats[
                    self.current_chat
                ] = {
                    "last_message": "",
                    "last_time": "",
                    "online": False,
                    "unread": 0
                }

            self.chats[
                self.current_chat
            ]["last_message"] = message

            # =================================
            # CLEAR INPUT
            # =================================

            self.message_input.text = ""

            self.refresh_chat_list()

            Clock.schedule_once(
                self.scroll_to_bottom,
                0.1
            )

        except Exception as e:

            print(
                "Send failed:",
                e
            )

    # =========================================
    # SCROLL TO BOTTOM
    # =========================================

    def scroll_to_bottom(
        self,
        dt
    ):

        if hasattr(
            self,
            "scroll_view"
        ):

            self.scroll_view.scroll_y = 0


# =========================================
# RUN APP
# =========================================

if __name__ == "__main__":

    ChatLiteApp().run()
