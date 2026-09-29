from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle


class ChatBubble(BoxLayout):

    def __init__(self, sender, message, is_me=False, **kwargs):

        super().__init__(**kwargs)

        self.orientation = "vertical"
        self.size_hint_y = None
        self.padding = (12, 8)
        self.spacing = 4

        # اسم المرسل
        sender_label = Label(
            text="You" if is_me else sender,
            color=(0.1, 0.1, 0.1, 1),
            bold=True,
            size_hint_y=None,
            height=22,
            halign="left",
            valign="middle"
        )

        # نص الرسالة
        message_label = Label(
            text=message,
            color=(0, 0, 0, 1),
            size_hint_y=None,
            halign="left",
            valign="top"
        )

        message_label.text_size = (None, None)

        message_label.bind(
            texture_size=lambda instance, size:
            setattr(instance, "height", size[1])
        )

        self.add_widget(sender_label)
        self.add_widget(message_label)

        with self.canvas.before:

            if is_me:
                Color(0.75, 0.90, 0.75, 1)
            else:
                Color(0.90, 0.90, 0.90, 1)

            self.background = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[12]
            )

        self.bind(
            pos=self.update_background,
            size=self.update_background
        )

        self.bind(
            minimum_height=self.update_height
        )

    def update_height(self, instance, value):

        self.height = self.minimum_height

    def update_background(self, instance, value):

        self.background.pos = self.pos
        self.background.size = self.size