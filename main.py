import sys
import os
import subprocess
import datetime
import re
from PyQt5 import QtWidgets, QtCore, QtGui

SUPERUSER_ID = "solka"
SUPERUSER_SECRET = "1337blazeit"
LOG_FILE = "server_logs.txt"

class ServerWorker(QtCore.QThread):
    output_received = QtCore.pyqtSignal(str)
    status_changed = QtCore.pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.process = None
        self._stop_requested = False
        self.working_dir = os.path.abspath(".")

    def set_working_dir(self, directory):
        self.working_dir = directory

    def run(self):
        self._stop_requested = False
        self.status_changed.emit(True)
        try:
            cmd = "pnpm start --hostname 0.0.0.0 --port 80"
            
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                shell=True,
                cwd=self.working_dir,
                startupinfo=startupinfo
            )
            
            for line in self.process.stdout:
                if self._stop_requested:
                    break
                self.output_received.emit(line)
                self.log_to_file(line)
                
            self.process.wait()
        except Exception as e:
            error_msg = f"Ошибка запуска: {str(e)}\n"
            self.output_received.emit(error_msg)
            self.log_to_file(error_msg)
        finally:
            self.status_changed.emit(False)

    def stop(self):
        self._stop_requested = True
        if self.process:
            if sys.platform == "win32":
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], creationflags=0x08000000)
            else:
                self.process.terminate()
        self.wait()

    def log_to_file(self, text):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        try:
            with open(os.path.join(self.working_dir, LOG_FILE), "a", encoding="utf-8") as f:
                f.write(timestamp + text)
        except:
            pass

class CustomTitleBar(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(38)
        self.setObjectName("customTitleBar")
        self._drag_pos = None

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 6, 0)
        layout.setSpacing(0)

        self.lbl_icon = QtWidgets.QLabel('MEM<span style="color:#e87a5d;">[O]</span>RIA')
        self.lbl_icon.setTextFormat(QtCore.Qt.RichText)
        self.lbl_icon.setObjectName("titleBarLabel")
        layout.addWidget(self.lbl_icon)

        layout.addStretch()

        self.btn_minimize = QtWidgets.QPushButton("─")
        self.btn_minimize.setObjectName("titleBtn")
        self.btn_minimize.setFixedSize(38, 38)
        self.btn_minimize.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_minimize.clicked.connect(self._minimize)
        layout.addWidget(self.btn_minimize)

        self.btn_maximize = QtWidgets.QPushButton("□")
        self.btn_maximize.setObjectName("titleBtn")
        self.btn_maximize.setFixedSize(38, 38)
        self.btn_maximize.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.btn_maximize)

        self.btn_close = QtWidgets.QPushButton("✕")
        self.btn_close.setObjectName("titleBtnClose")
        self.btn_close.setFixedSize(38, 38)
        self.btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self._close)
        layout.addWidget(self.btn_close)

    def _minimize(self):
        self.parent_window.showMinimized()

    def _toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()

    def _close(self):
        self.parent_window.close()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == QtCore.Qt.LeftButton:
            self.parent_window.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._toggle_maximize()

class MainWindow(QtWidgets.QMainWindow):
    GRIP_SIZE = 6

    def __init__(self):
        super().__init__()
        self.is_superuser = False
        self.worker = ServerWorker()
        self.current_folder = os.path.abspath(".")
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setMouseTracking(True)
        self.resize(950, 650)
        self.setMinimumSize(600, 400)
        
        self.setup_ui()
        self.setup_styles()
        self.setup_logic()
        self.setup_tray()
        
        self.worker.output_received.connect(self.append_log)
        self.worker.status_changed.connect(self.update_status)

    def setup_ui(self):
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.setCentralWidget(self.centralwidget)
        self.main_layout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        self.stackedWidget = QtWidgets.QStackedWidget(self.centralwidget)
        self.main_layout.addWidget(self.stackedWidget)

        # --- PAGE LOGIN ---
        self.page_login = QtWidgets.QWidget()
        self.page_login.setObjectName("page_login")
        self.login_layout = QtWidgets.QVBoxLayout(self.page_login)
        self.login_layout.setAlignment(QtCore.Qt.AlignCenter)

        self.loginFrame = QtWidgets.QFrame(self.page_login)
        self.loginFrame.setObjectName("loginFrame")
        self.loginFrame.setFixedSize(440, 520)
        self.frame_layout = QtWidgets.QVBoxLayout(self.loginFrame)
        self.frame_layout.setContentsMargins(40, 40, 40, 40)
        self.frame_layout.setSpacing(15)

        self.lbl_logo = QtWidgets.QLabel('MEM<span style="color:#e87a5d;">[O]</span>RIA', self.loginFrame)
        self.lbl_logo.setTextFormat(QtCore.Qt.RichText)
        self.lbl_logo.setObjectName("lbl_logo")
        self.lbl_logo.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_logo.setFixedHeight(90)
        self.frame_layout.addWidget(self.lbl_logo)

        self.lbl_subtitle = QtWidgets.QLabel("АВТОРИЗАЦИЯ ХОСТА", self.loginFrame)
        self.lbl_subtitle.setObjectName("lbl_subtitle")
        self.lbl_subtitle.setWordWrap(True)
        self.lbl_subtitle.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_subtitle.setFixedHeight(40)
        self.frame_layout.addWidget(self.lbl_subtitle)

        self.input_id = QtWidgets.QLineEdit(self.loginFrame)
        self.input_id.setPlaceholderText("ID Клиента")
        self.input_id.setFixedHeight(55)
        self.frame_layout.addWidget(self.input_id)

        self.input_secret = QtWidgets.QLineEdit(self.loginFrame)
        self.input_secret.setPlaceholderText("Пароль")
        self.input_secret.setEchoMode(QtWidgets.QLineEdit.Password)
        self.input_secret.setFixedHeight(55)
        self.frame_layout.addWidget(self.input_secret)

        self.lbl_error = QtWidgets.QLabel("", self.loginFrame)
        self.lbl_error.setObjectName("lbl_error")
        self.lbl_error.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_error.setFixedHeight(25)
        self.frame_layout.addWidget(self.lbl_error)

        self.btn_login = QtWidgets.QPushButton("ВОЙТИ В СИСТЕМУ", self.loginFrame)
        self.btn_login.setObjectName("btn_login")
        self.btn_login.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_login.setFixedHeight(55)
        self.frame_layout.addWidget(self.btn_login)

        self.login_layout.addWidget(self.loginFrame)

        self.stackedWidget.addWidget(self.page_login)

        # --- PAGE CONSOLE ---
        self.page_console = QtWidgets.QWidget()
        self.page_console.setObjectName("page_console")
        self.console_layout = QtWidgets.QVBoxLayout(self.page_console)
        self.console_layout.setContentsMargins(35, 35, 35, 35)
        self.console_layout.setSpacing(20)

        self.headerFrame = QtWidgets.QFrame(self.page_console)
        self.header_layout = QtWidgets.QHBoxLayout(self.headerFrame)
        self.header_layout.setContentsMargins(0, 0, 0, 0)

        self.titleFrame = QtWidgets.QFrame(self.headerFrame)
        self.title_layout = QtWidgets.QVBoxLayout(self.titleFrame)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        self.title_layout.setSpacing(5)

        self.lbl_main_title = QtWidgets.QLabel('MEM<span style="color:#e87a5d;">[O]</span>RIA', self.titleFrame)
        self.lbl_main_title.setObjectName("lbl_main_title")
        self.title_layout.addWidget(self.lbl_main_title)

        self.subtitleFrame = QtWidgets.QFrame(self.titleFrame)
        self.subtitle_layout = QtWidgets.QHBoxLayout(self.subtitleFrame)
        self.subtitle_layout.setContentsMargins(0, 0, 0, 0)
        self.subtitle_layout.setSpacing(12)

        self.lbl_role = QtWidgets.QLabel("ROOT", self.subtitleFrame)
        self.lbl_role.setObjectName("lbl_role")
        self.subtitle_layout.addWidget(self.lbl_role)

        self.lbl_main_subtitle = QtWidgets.QLabel("МЕНЕДЖЕР УПРАВЛЕНИЯ САЙТОМ", self.subtitleFrame)
        self.lbl_main_subtitle.setObjectName("lbl_main_subtitle")
        self.subtitle_layout.addWidget(self.lbl_main_subtitle)
        self.subtitle_layout.addStretch()

        self.title_layout.addWidget(self.subtitleFrame)
        self.header_layout.addWidget(self.titleFrame)

        self.statusFrame = QtWidgets.QFrame(self.headerFrame)
        self.status_layout = QtWidgets.QVBoxLayout(self.statusFrame)
        self.status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_layout.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.lbl_status = QtWidgets.QLabel("● ОЖИДАНИЕ", self.statusFrame)
        self.lbl_status.setObjectName("lbl_status")
        self.lbl_status.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.status_layout.addWidget(self.lbl_status)

        self.controlsFrame = QtWidgets.QFrame(self.statusFrame)
        self.controls_layout = QtWidgets.QHBoxLayout(self.controlsFrame)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setSpacing(12)

        self.btn_start = QtWidgets.QPushButton("ЗАПУСК", self.controlsFrame)
        self.btn_start.setCursor(QtCore.Qt.PointingHandCursor)
        self.controls_layout.addWidget(self.btn_start)

        self.btn_restart = QtWidgets.QPushButton("РЕСТАРТ", self.controlsFrame)
        self.btn_restart.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_restart.setEnabled(False)
        self.controls_layout.addWidget(self.btn_restart)

        self.btn_stop = QtWidgets.QPushButton("ОСТАНОВКА", self.controlsFrame)
        self.btn_stop.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.controls_layout.addWidget(self.btn_stop)

        self.status_layout.addWidget(self.controlsFrame)
        self.header_layout.addWidget(self.statusFrame)
        self.console_layout.addWidget(self.headerFrame)

        # --- Folder Selection ---
        self.folderFrame = QtWidgets.QFrame(self.page_console)
        self.folder_layout = QtWidgets.QHBoxLayout(self.folderFrame)
        self.folder_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_folder = QtWidgets.QLabel(f"Папка сайта: {self.current_folder}", self.folderFrame)
        self.lbl_folder.setObjectName("lbl_folder")
        self.folder_layout.addWidget(self.lbl_folder)

        self.btn_select_folder = QtWidgets.QPushButton("ВЫБРАТЬ ПАПКУ", self.folderFrame)
        self.btn_select_folder.setCursor(QtCore.Qt.PointingHandCursor)
        self.folder_layout.addWidget(self.btn_select_folder)

        self.console_layout.addWidget(self.folderFrame)

        # --- Text Browser ---
        self.textBrowser_console = QtWidgets.QTextBrowser(self.page_console)
        self.textBrowser_console.setOpenExternalLinks(True)
        self.console_layout.addWidget(self.textBrowser_console)

        self.stackedWidget.addWidget(self.page_console)

    def setup_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#centralwidget, QWidget#page_login, QWidget#page_console {
                background-color: #08080a;
            }

            /* Custom Title Bar */
            QWidget#customTitleBar {
                background-color: #0a0a0c;
                border-bottom: 1px solid #1a1a1e;
            }
            QLabel#titleBarLabel {
                color: #666;
                font-family: 'Playfair Display', 'Georgia', serif;
                font-size: 13px;
                letter-spacing: 3px;
            }
            QPushButton#titleBtn {
                background-color: transparent;
                color: #555;
                border: none;
                border-radius: 0px;
                font-size: 13px;
                padding: 0px;
                font-weight: normal;
                letter-spacing: 0px;
            }
            QPushButton#titleBtn:hover {
                background-color: #1a1a1e;
                color: #aaa;
                border: none;
            }
            QPushButton#titleBtnClose {
                background-color: transparent;
                color: #555;
                border: none;
                border-radius: 0px;
                font-size: 12px;
                padding: 0px;
                font-weight: normal;
                letter-spacing: 0px;
            }
            QPushButton#titleBtnClose:hover {
                background-color: #c42b1c;
                color: white;
                border: none;
            }

            QFrame#loginFrame {
                background-color: #0c0c0e;
                border: 1px solid #1a1a1e;
                border-radius: 6px;
            }
            QLabel {
                color: #a0a0a0;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel#lbl_logo, QLabel#lbl_main_title {
                font-family: 'Playfair Display', 'Georgia', serif;
                font-size: 38px;
                letter-spacing: 6px;
                padding: 0px;
            }
            QLabel#lbl_subtitle, QLabel#lbl_main_subtitle {
                font-size: 11px;
                letter-spacing: 3px;
                color: #555;
                padding: 0px;
            }
            QLabel#lbl_role {
                color: #e87a5d;
                font-size: 10px;
                border: 1px solid #e87a5d;
                padding: 2px 6px;
                border-radius: 3px;
                font-weight: bold;
            }
            QLabel#lbl_status {
                color: #555;
                font-size: 11px;
                letter-spacing: 2px;
                font-weight: bold;
            }
            QLabel#lbl_folder {
                color: #888;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #121214;
                border: 1px solid #222;
                border-radius: 4px;
                padding: 0px 15px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #e87a5d;
                background-color: #151518;
            }
            QPushButton {
                background-color: transparent;
                color: #a0a0a0;
                border: 1px solid #222;
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 12px;
                letter-spacing: 1px;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 1px solid #e87a5d;
                color: #e87a5d;
                background-color: rgba(232, 122, 93, 0.05);
            }
            QPushButton:disabled {
                color: #333;
                border: 1px solid #1a1a1e;
            }
            QPushButton#btn_login {
                color: #e87a5d;
                border: 1px solid #e87a5d;
                padding: 0px;
                font-size: 14px;
                margin-top: 5px;
            }
            QPushButton#btn_login:hover {
                background-color: rgba(232, 122, 93, 0.1);
            }
            QTextBrowser {
                background-color: #030303;
                color: #b0b0b0;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 13px;
                border: 1px solid #1a1a1e;
                border-radius: 6px;
                padding: 20px;
            }
        """)

    def setup_logic(self):
        self.stackedWidget.setCurrentIndex(0)
        self.btn_login.clicked.connect(self.handle_login)
        self.input_secret.returnPressed.connect(self.handle_login)
        self.input_id.returnPressed.connect(self.handle_login)
        
        self.btn_start.clicked.connect(self.worker.start)
        self.btn_stop.clicked.connect(self.worker.stop)
        self.btn_restart.clicked.connect(self.handle_restart)
        self.btn_select_folder.clicked.connect(self.select_folder)
        
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self.stackedWidget)
        self.stackedWidget.setGraphicsEffect(self.opacity_effect)
        
    def fade_transition(self, target_index):
        self.anim_out = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        
        self.anim_in = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_in.setDuration(350)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        
        self.anim_out.finished.connect(lambda: self._switch_page(target_index))
        self.anim_out.start()
        
    def _switch_page(self, index):
        self.stackedWidget.setCurrentIndex(index)
        self.anim_in.start()

    def handle_login(self):
        cid = self.input_id.text().strip().lower()
        secret = self.input_secret.text().strip().lower()
        
        if cid == SUPERUSER_ID.lower() and secret == SUPERUSER_SECRET.lower():
            self.is_superuser = True
            self.lbl_role.setText("ROOT")
            self.lbl_role.show()
            self.controlsFrame.show()
            self.fade_transition(1)
        elif cid != "" and secret == "":
            self.is_superuser = False
            self.lbl_role.setText("GUEST")
            self.lbl_role.setStyleSheet("color: #888; border-color: #888;")
            self.controlsFrame.hide()
            self.fade_transition(1)
        else:
            self.lbl_error.setText("Неверные учетные данные")
            self.lbl_error.setStyleSheet("color: #ff5555;")
            
    def select_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку с сайтом (Next.js)", self.current_folder)
        if folder:
            self.current_folder = os.path.abspath(folder)
            self.lbl_folder.setText(f"Папка сайта: {self.current_folder}")
            self.worker.set_working_dir(self.current_folder)
            self.append_log(f"Рабочая папка изменена на: {self.current_folder}\n")

    def handle_restart(self):
        self.append_log("Перезапуск сервера...\n")
        self.worker.stop()
        QtCore.QTimer.singleShot(1000, self.worker.start)
        
    def append_log(self, text):
        clean_text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
        color = "#b0b0b0"
        lower_text = clean_text.lower()
        if "error" in lower_text or "failed" in lower_text or "exception" in lower_text:
            color = "#ff6b6b"
        elif "warn" in lower_text:
            color = "#ffd93d"
        elif "success" in lower_text or "ready" in lower_text or "compiled successfully" in lower_text:
            color = "#6bc167"
        elif "starting" in lower_text or "next.js" in lower_text:
            color = "#e87a5d"

        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        safe_text = clean_text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        html = f'<span style="color: #444;">[{time_str}]</span> <span style="color: {color};">{safe_text}</span>'
        
        self.textBrowser_console.append(html)

    def update_status(self, is_running):
        if is_running:
            self.lbl_status.setText("● АКТИВЕН")
            self.lbl_status.setStyleSheet("color: #6bc167; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_restart.setEnabled(True)
            self.btn_select_folder.setEnabled(False)
            if self.tray_icon:
                self.tray_icon.setIcon(QtGui.QIcon.fromTheme("network-server-active", self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)))
        else:
            self.lbl_status.setText("● ОСТАНОВЛЕН")
            self.lbl_status.setStyleSheet("color: #ff6b6b; font-size: 11px; font-weight: bold; letter-spacing: 2px;")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            self.btn_restart.setEnabled(False)
            self.btn_select_folder.setEnabled(True)
            if self.tray_icon:
                self.tray_icon.setIcon(QtGui.QIcon.fromTheme("network-server", self.style().standardIcon(QtWidgets.QStyle.SP_DriveNetIcon)))

    def setup_tray(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
        
        tray_menu = QtWidgets.QMenu()
        show_action = tray_menu.addAction("Показать окно")
        show_action.triggered.connect(self.show_from_tray)
        
        self.start_action = tray_menu.addAction("Запустить сервер")
        self.start_action.triggered.connect(self.worker.start)
        
        self.stop_action = tray_menu.addAction("Остановить сервер")
        self.stop_action.triggered.connect(self.worker.stop)
        
        quit_action = tray_menu.addAction("Выход")
        quit_action.triggered.connect(QtWidgets.QApplication.instance().quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def show_from_tray(self):
        self.show()
        self.activateWindow()

    def tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.show_from_tray()

    def _get_resize_edge(self, pos):
        rect = self.rect()
        g = self.GRIP_SIZE
        edges = 0
        if pos.x() < g:
            edges |= 1
        elif pos.x() > rect.width() - g:
            edges |= 2
        if pos.y() < g:
            edges |= 4
        elif pos.y() > rect.height() - g:
            edges |= 8
        return edges

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            edges = self._get_resize_edge(event.pos())
            if edges:
                self._resize_edge = edges
                self._resize_start_pos = event.globalPos()
                self._resize_start_geo = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_edge and self._resize_start_pos:
            diff = event.globalPos() - self._resize_start_pos
            geo = QtCore.QRect(self._resize_start_geo)
            min_w, min_h = self.minimumWidth(), self.minimumHeight()

            if self._resize_edge & 1:
                new_left = geo.left() + diff.x()
                if geo.right() - new_left >= min_w:
                    geo.setLeft(new_left)
            if self._resize_edge & 2:
                new_w = geo.width() + diff.x()
                if new_w >= min_w:
                    geo.setRight(geo.left() + new_w - 1)
            if self._resize_edge & 4:
                new_top = geo.top() + diff.y()
                if geo.bottom() - new_top >= min_h:
                    geo.setTop(new_top)
            if self._resize_edge & 8:
                new_h = geo.height() + diff.y()
                if new_h >= min_h:
                    geo.setBottom(geo.top() + new_h - 1)

            self.setGeometry(geo)
            event.accept()
            return

        edges = self._get_resize_edge(event.pos())
        if edges in (1, 2):
            self.setCursor(QtCore.Qt.SizeHorCursor)
        elif edges in (4, 8):
            self.setCursor(QtCore.Qt.SizeVerCursor)
        elif edges in (5, 10):
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif edges in (6, 9):
            self.setCursor(QtCore.Qt.SizeBDiagCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "MEMORIA Host",
            "Приложение свернуто в трей и продолжает работу.",
            QtWidgets.QSystemTrayIcon.Information,
            2000
        )

if __name__ == "__main__":
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    font = QtGui.QFont("Segoe UI", 10)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
