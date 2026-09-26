import sys, math, random
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QColor, QPainter, QRadialGradient, QPen, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QTextEdit, QPushButton, QScrollArea, QSizePolicy, QSplitter
)


class VoiceOrb(QWidget):
    """Orb fluide. Pour l'instant le niveau audio est simulé."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(360, 360)
        self.mode = "idle"
        self.dark_mode = True
        self.t = 0.0
        self.level = 0.0
        self.target = 0.0
        self.particles = [
            [random.random() * math.tau,
             random.uniform(105, 210),
             random.uniform(.0008, .003),
             random.random() * math.tau]
            for _ in range(75)
        ]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def set_theme(self, dark):
        self.dark_mode = dark
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    def tick(self):
        self.t += 0.035
        if self.mode == "idle":
            self.target = 0.07 + .025 * math.sin(self.t * 1.2)
        elif self.mode == "listening":
            self.target = .24 + .12 * math.sin(self.t * 2.0) + .06 * math.sin(self.t * 5.0)
        else:  # speaking / thinking
            self.target = .30 + .16 * math.sin(self.t * 1.8) + .09 * math.sin(self.t * 4.6)
        self.target = max(.025, min(1.0, self.target))
        self.level += (self.target - self.level) * .13
        for p in self.particles:
            p[0] += p[2]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        c = QPointF(w / 2, h / 2 - 5)
        p.fillRect(self.rect(), QColor("#090b12") if self.dark_mode else QColor("#f7f8fa"))

        # ambiance
        bg = QRadialGradient(c, min(w, h) * .65)
        bg.setColorAt(0, QColor(33, 42, 78, 75))
        bg.setColorAt(.55, QColor(15, 21, 38, 35))
        bg.setColorAt(1, QColor(9, 11, 18, 0))
        p.setBrush(bg); p.setPen(Qt.NoPen)
        p.drawEllipse(c, min(w, h) * .62, min(w, h) * .62)

        pulse = self.level

        # particles
        for angle, dist, speed, phase in self.particles:
            d = dist + math.sin(self.t * 2 + phase) * pulse * 30
            x = c.x() + math.cos(angle) * d
            y = c.y() + math.sin(angle) * d
            r = 1.0 + pulse * 1.5
            p.setBrush(QColor(125, 180, 255, int(35 + pulse * 120)))
            p.drawEllipse(QPointF(x, y), r, r)

        # organic rings
        for ring in range(5, 0, -1):
            radius = 65 + ring * 18 + pulse * ring * 18
            pen = QPen(QColor(105, 170, 255, max(8, 45 - ring * 6 + int(pulse * 25))))
            pen.setWidthF(1.0 if ring > 2 else 1.5)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            pts = []
            for i in range(110):
                a = math.tau * i / 110
                wave = math.sin(a * 4 + self.t * 2.0) * pulse * 7
                wave += math.sin(a * 8 - self.t * 3.0) * pulse * 3
                r = radius + wave
                pts.append(QPointF(c.x() + math.cos(a) * r, c.y() + math.sin(a) * r))
            for i in range(len(pts) - 1):
                p.drawLine(pts[i], pts[i + 1])
            p.drawLine(pts[-1], pts[0])

        # halo
        radius = 62 + pulse * 20
        halo = QRadialGradient(c, radius * 2.7)
        halo.setColorAt(0, QColor(80, 155, 255, 125))
        halo.setColorAt(.28, QColor(80, 130, 255, 65))
        halo.setColorAt(.7, QColor(70, 100, 240, 15))
        halo.setColorAt(1, QColor(70, 100, 240, 0))
        p.setBrush(halo); p.setPen(Qt.NoPen)
        p.drawEllipse(c, radius * 2.7, radius * 2.7)

        # orb
        g = QRadialGradient(QPointF(c.x() - radius*.3, c.y() - radius*.35), radius * 1.45)
        g.setColorAt(0, QColor("#eefaff"))
        g.setColorAt(.17, QColor("#a9dcff"))
        g.setColorAt(.43, QColor("#5b9cff"))
        g.setColorAt(.75, QColor("#3b52bd"))
        g.setColorAt(1, QColor("#171d62"))
        p.setBrush(g); p.setPen(Qt.NoPen)
        p.drawEllipse(c, radius, radius)

        # highlight
        hg = QRadialGradient(QPointF(c.x()-radius*.25, c.y()-radius*.3), radius*.5)
        hg.setColorAt(0, QColor(255,255,255,185)); hg.setColorAt(.4, QColor(255,255,255,45)); hg.setColorAt(1, QColor(255,255,255,0))
        p.setBrush(hg)
        p.drawEllipse(QPointF(c.x()-radius*.2, c.y()-radius*.25), radius*.4, radius*.28)


class MessageWidget(QFrame):
    """Bulle de conversation pouvant afficher du Markdown ou du texte brut."""
    def __init__(self, content, role="assistant", markdown=True, parent=None):
        super().__init__(parent)
        self.setObjectName("message")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(5)

        label = QLabel("Vous" if role == "user" else "Assistant")
        label.setObjectName("role")
        layout.addWidget(label)

        if markdown:
            viewer = QTextEdit()
            viewer.setReadOnly(True)
            viewer.setFrameStyle(QFrame.NoFrame)
            viewer.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            viewer.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            viewer.setMarkdown(content)
            viewer.document().setDocumentMargin(0)
            viewer.document().adjustSize()
            viewer.setFixedHeight(max(34, int(viewer.document().size().height()) + 8))
        else:
            viewer = QLabel(content)
            viewer.setWordWrap(True)
            viewer.setTextInteractionFlags(Qt.TextSelectableByMouse)
            viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        viewer.setObjectName("content")
        layout.addWidget(viewer)

        if role == "user":
            self.setStyleSheet("QFrame#message { background:#20242d; border-radius:16px; }")
        else:
            self.setStyleSheet("QFrame#message { background:transparent; border-radius:16px; }")


class ChatPanel(QFrame):
    def __init__(self, orb):
        super().__init__()
        self.orb = orb
        self.setObjectName("chatPanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 14, 18, 12)
        title = QLabel("Assistant")
        title.setObjectName("title")
        subtitle = QLabel("Conversation")
        subtitle.setObjectName("subtitle")
        textcol = QVBoxLayout(); textcol.setSpacing(1)
        textcol.addWidget(title); textcol.addWidget(subtitle)
        hl.addLayout(textcol); hl.addStretch()

        self.theme_btn = QPushButton("☼")
        self.theme_btn.setObjectName("headerButton")
        self.theme_btn.setFixedSize(34, 34)
        self.theme_btn.setToolTip("Mode clair / sombre")
        self.theme_btn.clicked.connect(self.toggle_theme_requested)
        hl.addWidget(self.theme_btn)

        self.toggle_btn = QPushButton("×")
        self.toggle_btn.setObjectName("headerButton")
        self.toggle_btn.setFixedSize(34, 34)
        self.toggle_btn.setToolTip("Fermer le panneau")
        self.toggle_btn.clicked.connect(self.toggle_panel_requested)
        hl.addWidget(self.toggle_btn)

        root.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setObjectName("scroll")

        self.messages = QWidget()
        self.messages.setObjectName("messages")
        self.msg_layout = QVBoxLayout(self.messages)
        self.msg_layout.setContentsMargins(22, 18, 22, 18)
        self.msg_layout.setSpacing(14)
        self.msg_layout.addStretch()
        self.scroll.setWidget(self.messages)
        root.addWidget(self.scroll, 1)

        composer = QFrame()
        composer.setObjectName("composerArea")
        cl = QHBoxLayout(composer)
        cl.setContentsMargins(16, 12, 16, 16)
        cl.setSpacing(10)
        self.input = QTextEdit()
        self.input.setObjectName("input")
        self.input.setPlaceholderText("Écrivez un message…")
        self.input.setFixedHeight(58)
        self.input.installEventFilter(self)
        self.send = QPushButton("➤")
        self.send.setObjectName("send")
        self.send.setFixedSize(48, 48)
        self.send.clicked.connect(self.send_message)
        cl.addWidget(self.input, 1); cl.addWidget(self.send)
        root.addWidget(composer)

        self.add_message("Bonjour ! Je suis prêt.\n\nTu peux me parler ou m'envoyer un message.", "assistant", True)

    def toggle_theme_requested(self):
        window = self.window()
        if hasattr(window, "toggle_theme"):
            window.toggle_theme()

    def toggle_panel_requested(self):
        window = self.window()
        if hasattr(window, "toggle_chat_panel"):
            window.toggle_chat_panel()

    def set_panel_open(self, opened):
        self.toggle_btn.setText("×" if opened else "□")
        self.toggle_btn.setToolTip("Fermer le panneau" if opened else "Ouvrir le panneau")

    def eventFilter(self, obj, event):
        if obj is self.input and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self.send_message(); return True
        return super().eventFilter(obj, event)

    def add_message(self, content, role="assistant", markdown=True):
        widget = MessageWidget(content, role, markdown)
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, widget)
        QTimer.singleShot(20, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def send_message(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.add_message(text, "user", False)
        self.input.clear()
        self.orb.set_mode("thinking")
        QTimer.singleShot(450, lambda: self.demo_answer(text))

    def demo_answer(self, text):
        self.add_message(
            "### Réponse\n\nTu as écrit : **" + text.replace("**", "") + "**\n\n"
            "Ceci est le moteur de démonstration. On pourra ensuite brancher ton IA ici.",
            "assistant", True
        )
        self.orb.set_mode("speaking")
        QTimer.singleShot(1600, lambda: self.orb.set_mode("idle"))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mon Assistant IA")
        self.resize(1280, 760)
        self.setMinimumSize(1050, 650)
        self.setObjectName("main")
        self.dark_mode = True
        self.chat_open = True
        self.last_chat_width = 650

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # QSplitter permet de redimensionner librement le panneau de discussion.
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(5)
        root.addWidget(self.splitter)

        left = QFrame()
        left.setObjectName("orbArea")
        left.setMinimumWidth(430)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(20, 20, 20, 20)
        ll.addStretch(1)
        self.orb = VoiceOrb()
        ll.addWidget(self.orb, 1)
        self.status = QLabel("Prêt à écouter")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setObjectName("status")
        ll.addWidget(self.status)
        ll.addStretch(1)

        self.chat = ChatPanel(self.orb)
        self.chat.setMinimumWidth(360)

        self.splitter.addWidget(left)
        self.splitter.addWidget(self.chat)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 6)
        self.splitter.setSizes([630, 650])

        # Bouton flottant visible quand le panneau est fermé.
        self.open_chat_btn = QPushButton("☰  Chat")
        self.open_chat_btn.setObjectName("openChatButton")
        self.open_chat_btn.setFixedSize(110, 42)
        self.open_chat_btn.clicked.connect(self.toggle_chat_panel)
        self.open_chat_btn.hide()
        self.open_chat_btn.setParent(self)

        self.orb.set_theme(self.dark_mode)
        self.apply_theme()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.open_chat_btn.move(self.width() - self.open_chat_btn.width() - 20, 20)

    def toggle_chat_panel(self):
        if self.chat_open:
            sizes = self.splitter.sizes()
            if len(sizes) == 2 and sizes[1] > 0:
                self.last_chat_width = max(360, sizes[1])
            self.chat_open = False
            self.chat.hide()
            self.splitter.setSizes([self.splitter.width(), 0])
            self.open_chat_btn.show()
            self.open_chat_btn.raise_()
            self.chat.set_panel_open(False)
        else:
            self.chat_open = True
            self.chat.show()
            available = self.splitter.width()
            chat_width = min(max(self.last_chat_width, 360), available - 430)
            self.splitter.setSizes([max(430, available - chat_width), chat_width])
            self.open_chat_btn.hide()
            self.chat.set_panel_open(True)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.orb.set_theme(self.dark_mode)
        self.apply_theme()

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
            QWidget#main { background:#090b10; color:#e7ebf3; }
            QFrame#orbArea { background:#090b10; border-right:1px solid #1d222c; }
            QFrame#chatPanel { background:#0d1016; }
            QFrame#header { background:#0d1016; border-bottom:1px solid #1c212b; }
            QLabel#title { color:#f3f6fb; font-size:16px; font-weight:600; }
            QLabel#subtitle { color:#747d8d; font-size:11px; }
            QLabel#status { color:#778195; font-size:12px; }
            QScrollArea#scroll { background:#0d1016; border:0; }
            QWidget#messages { background:#0d1016; }
            QLabel#role { color:#8e98a9; font-size:11px; font-weight:600; }
            QTextEdit#content, QLabel#content { color:#dfe4ed; background:transparent; border:0; font-size:14px; }
            QFrame#composerArea { background:#0d1016; border-top:1px solid #1c212b; }
            QTextEdit#input { background:#171b23; color:#eef2f8; border:1px solid #2a303c; border-radius:16px; padding:10px 14px; font-size:14px; }
            QTextEdit#input:focus { border:1px solid #4c79bd; }
            QPushButton#send { background:#e9edf4; color:#11151c; border:0; border-radius:24px; font-size:21px; font-weight:bold; }
            QPushButton#send:hover { background:#ffffff; }
            QPushButton#send:pressed { background:#cbd2de; }
            QPushButton#headerButton { background:transparent; color:#9da7b8; border:0; border-radius:10px; font-size:20px; }
            QPushButton#headerButton:hover { background:#1b2029; color:#ffffff; }
            QPushButton#openChatButton { background:#171b23; color:#eef2f8; border:1px solid #303744; border-radius:14px; font-size:13px; font-weight:600; }
            QPushButton#openChatButton:hover { background:#222834; }
            QSplitter::handle { background:#1b2029; }
            QSplitter::handle:hover { background:#4c79bd; }
            QScrollBar:vertical { background:transparent; width:10px; margin:5px 2px 5px 0; }
            QScrollBar::handle:vertical { background:#303745; border-radius:5px; min-height:35px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            """)
        else:
            self.setStyleSheet("""
            QWidget#main { background:#f7f8fa; color:#20242b; }
            QFrame#orbArea { background:#f7f8fa; border-right:1px solid #e1e4e9; }
            QFrame#chatPanel { background:#ffffff; }
            QFrame#header { background:#ffffff; border-bottom:1px solid #e6e8ec; }
            QLabel#title { color:#171a1f; font-size:16px; font-weight:600; }
            QLabel#subtitle { color:#7a818d; font-size:11px; }
            QLabel#status { color:#707886; font-size:12px; }
            QScrollArea#scroll { background:#ffffff; border:0; }
            QWidget#messages { background:#ffffff; }
            QLabel#role { color:#737b88; font-size:11px; font-weight:600; }
            QTextEdit#content, QLabel#content { color:#252a32; background:transparent; border:0; font-size:14px; }
            QFrame#composerArea { background:#ffffff; border-top:1px solid #e6e8ec; }
            QTextEdit#input { background:#f4f5f7; color:#20242b; border:1px solid #d9dde4; border-radius:16px; padding:10px 14px; font-size:14px; }
            QTextEdit#input:focus { border:1px solid #7a9bd0; }
            QPushButton#send { background:#20242b; color:#ffffff; border:0; border-radius:24px; font-size:21px; font-weight:bold; }
            QPushButton#send:hover { background:#343a44; }
            QPushButton#send:pressed { background:#111318; }
            QPushButton#headerButton { background:transparent; color:#68717f; border:0; border-radius:10px; font-size:20px; }
            QPushButton#headerButton:hover { background:#eef0f3; color:#20242b; }
            QPushButton#openChatButton { background:#ffffff; color:#20242b; border:1px solid #d8dce3; border-radius:14px; font-size:13px; font-weight:600; }
            QPushButton#openChatButton:hover { background:#f0f2f5; }
            QSplitter::handle { background:#e1e4e9; }
            QSplitter::handle:hover { background:#8ba7d4; }
            QScrollBar:vertical { background:transparent; width:10px; margin:5px 2px 5px 0; }
            QScrollBar::handle:vertical { background:#c9ced7; border-radius:5px; min-height:35px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            """)

        # Style des bulles utilisateur selon le thème.
        user_bg = "#20242d" if self.dark_mode else "#eef0f3"
        self.chat.setStyleSheet(f"QFrame#message {{ border-radius:16px; }}")
        # Le style du widget est réappliqué sur les messages déjà présents.
        for widget in self.chat.messages.findChildren(MessageWidget):
            if widget.findChild(QLabel, "role") and widget.findChild(QLabel, "role").text() == "Vous":
                widget.setStyleSheet(f"QFrame#message {{ background:{user_bg}; border-radius:16px; }}")
            else:
                widget.setStyleSheet("QFrame#message { background:transparent; border-radius:16px; }")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
