import sys
import datetime
import json
import os
import hashlib
from PyQt5.QtCore import Qt, QPoint, QParallelAnimationGroup, QPropertyAnimation, QEasingCurve, pyqtProperty, QSize
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLabel, QFrame, QGraphicsDropShadowEffect,
    QInputDialog, QMessageBox, QLineEdit, QDialog, QDialogButtonBox, QComboBox
)
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QFont, QColor
from cryptography.fernet import Fernet

CONFIG_FILE = "config.json"

def load_config():
    """
    Load configuration from CONFIG_FILE.
    Default config: password protection off, no password set, timeout 60 sec.
    """
    default_config = {
        "password_protected": False,
        "password_hash": "",
        "password_timeout": 60  # seconds; default 1 minute
    }
    if not os.path.exists(CONFIG_FILE):
        return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        for key in default_config:
            if key not in config:
                config[key] = default_config[key]
        return config
    except Exception:
        return default_config

def save_config(config):
    """Save the configuration dictionary to CONFIG_FILE."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def hash_password(password: str) -> str:
    """Return a SHA256 hex digest of the given password."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_key():
    """
    Load the encryption key from 'secret.key'. If the key file does not exist,
    generate a new key and save it.
    """
    try:
        with open("secret.key", "rb") as key_file:
            return key_file.read()
    except FileNotFoundError:
        key = Fernet.generate_key()
        with open("secret.key", "wb") as key_file:
            key_file.write(key)
        return key

def save_notes_to_file(notes, filename="notes.json"):
    """
    Save notes to a JSON file.
    Convert datetime objects to ISO strings.
    """
    notes_to_save = []
    for note in notes:
        notes_to_save.append({
            "title": note["title"],
            "content": note["content"],
            "created": note["created"].isoformat(),
            "updated": note["updated"].isoformat(),
            "read_only": note.get("read_only", False)
        })
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(notes_to_save, f, indent=4)

def load_notes_from_file(filename="notes.json"):
    """
    Load notes from a JSON file.
    Convert ISO date strings back to datetime objects.
    """
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    notes = []
    for note in loaded:
        notes.append({
            "title": note["title"],
            "content": note["content"],
            "created": datetime.datetime.fromisoformat(note["created"]),
            "updated": datetime.datetime.fromisoformat(note["updated"]),
            "read_only": note.get("read_only", False)
        })
    return notes

def add_neumorphic_effect(widget, blur_radius=20, x_offset=6, y_offset=6, shadow_color=QColor(163, 177, 198, 180)):
    """
    Apply a soft drop shadow to simulate a neumorphic extruded effect.
    """
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(x_offset, y_offset)
    shadow.setColor(shadow_color)
    widget.setGraphicsEffect(shadow)

class PasswordDialog(QDialog):
    def __init__(self, title="Enter Password", label_text="Enter password:", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        layout = QVBoxLayout(self)

        self.label = QLabel(label_text)
        layout.addWidget(self.label)

        # Password field with echo mode password.
        self.line_edit = QLineEdit()
        self.line_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.line_edit)

        # Toggle button to show/hide password.
        self.toggle_button = QPushButton("Show")
        self.toggle_button.setCheckable(True)
        self.toggle_button.toggled.connect(self.toggle_echo)
        layout.addWidget(self.toggle_button)

        # OK and Cancel buttons.
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def toggle_echo(self, checked):
        if checked:
            self.line_edit.setEchoMode(QLineEdit.Normal)
            self.toggle_button.setText("Hide")
        else:
            self.line_edit.setEchoMode(QLineEdit.Password)
            self.toggle_button.setText("Show")

    def get_password(self):
        return self.line_edit.text()

class ToggleButton(QPushButton):
    """
    A simple toggle button that changes its text when toggled.
    Provide the text for ON state and OFF state in the constructor.
    """
    def __init__(self, on_text, off_text, parent=None):
        super().__init__(parent)
        self.on_text = on_text
        self.off_text = off_text
        self.setCheckable(True)
        # Start unchecked.
        self.setChecked(False)
        self.setText(self.off_text)
        # Use a style similar to the password dialog toggle.
        self.setStyleSheet("""
            QPushButton {
                background-color: #dfe4ee;
                border: 1px solid #bbb;
                padding: 4px 10px;
                border-radius: 4px;
                font-family: 'Segoe UI';
                font-size: 12pt;
            }
            QPushButton:checked {
                background-color: #b0bec5;
                border: 1px solid #888;
            }
        """)
        self.toggled.connect(self.update_text)

    def update_text(self, checked):
        if checked:
            self.setText(self.on_text)
        else:
            self.setText(self.off_text)

class SettingsPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._panelHeight = 0
        self.setFixedHeight(self._panelHeight)
        self.setStyleSheet("""
            QWidget {
                background-color: #E0E5EC;
            }
            QPushButton, QLabel, QComboBox {
                font-family: 'Segoe UI';
                font-size: 12pt;
                color: #333;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)
        
        # Add the toggle button for Prevent Edit without a label.
        self.preventEditToggle = ToggleButton("Prevent Edit", "Allow Edit", self)
        layout.addWidget(self.preventEditToggle)
        
        # Add the toggle button for Password Protection without a label.
        self.passwordProtectionToggle = ToggleButton("Password Protection On", "Password Protection Off", self)
        layout.addWidget(self.passwordProtectionToggle)
        
        # Button to set or change the password.
        self.changePasswordButton = QPushButton("Set/Change Password")
        layout.addWidget(self.changePasswordButton)
        add_neumorphic_effect(
            self.changePasswordButton,
            blur_radius=15,
            x_offset=4,
            y_offset=4,
            shadow_color=QColor(163, 177, 198, 150)
        )
        
        # Combo box for selecting password timeout.
        timeout_layout = QHBoxLayout()
        # If you want a label for the timeout, you can keep it; otherwise, remove it as well.
        # For now, we'll leave it.
        timeout_label = QLabel("Password Timeout:")
        timeout_layout.addWidget(timeout_label)
        
        self.timeoutComboBox = QComboBox()
        self.timeoutComboBox.addItem("1 minute", 60)
        self.timeoutComboBox.addItem("2 minutes", 120)
        self.timeoutComboBox.addItem("5 minutes", 300)
        timeout_layout.addWidget(self.timeoutComboBox)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)
        
        layout.addStretch()
    
    def getPanelHeight(self):
        return self._panelHeight

    def setPanelHeight(self, h):
        self._panelHeight = h
        self.setFixedHeight(h)
    
    panelHeight = pyqtProperty(int, fget=getPanelHeight, fset=setPanelHeight)

class NotesApp(QWidget):
    def __init__(self):
        super().__init__()
        self.notes = load_notes_from_file()  # persisted notes
        self.current_item = None
        self.current_note_index = None
        self.sideBarOpen = False
        self.sideBarWidth = 200
        self.key = load_key()
        self.config = load_config()
        # Track last successful password entry time.
        self.last_password_entry = None  
        self.init_ui()

    def encrypt_text(self, text: str) -> str:
        f = Fernet(self.key)
        return f.encrypt(text.encode()).decode()

    def decrypt_text(self, token: str) -> str:
        f = Fernet(self.key)
        return f.decrypt(token.encode()).decode()

    def init_ui(self):
        self.setWindowTitle("C-Note")
        self.setGeometry(100, 100, 400, 600)
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI';
                background-color: #E0E5EC;
                color: #333;
            }
            QListWidget {
                background-color: #E0E5EC;
                border: none;
                outline: none;
            }
            QListWidget::item:selected {
                background: transparent;
                border: none;
            }
            QTextEdit {
                background-color: #E0E5EC;
                border: none;
                padding: 8px;
                font-size: 16pt;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.container = QWidget(self)
        main_layout.addWidget(self.container)

        self.list_layer = QWidget(self.container)
        list_layout = QVBoxLayout(self.list_layer)
        list_layout.setContentsMargins(10, 10, 10, 10)
        list_layout.setSpacing(10)

        self.note_list_widget = QListWidget()
        self.note_list_widget.setSpacing(10)
        self.note_list_widget.setStyleSheet("QListWidget::item { border: none; }")
        self.note_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.note_list_widget.itemClicked.connect(self.show_notepad_for_edit)
        list_layout.addWidget(self.note_list_widget)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.plus_button = QPushButton("+")
        self.plus_button.setFixedSize(60, 60)
        self.plus_button.setStyleSheet("""
            QPushButton {
                background-color: #E0E5EC;
                border: none;
                border-radius: 30px;
                font-size: 32pt;
                color: #7F8FA6;
            }
            QPushButton:hover {
                background-color: #dfe4ee;
            }
        """)
        add_neumorphic_effect(self.plus_button, blur_radius=15, x_offset=6, y_offset=6,
                                shadow_color=QColor(163, 177, 198, 150))
        self.plus_button.clicked.connect(self.show_notepad_for_new)
        bottom_layout.addWidget(self.plus_button)
        bottom_layout.addStretch()
        list_layout.addLayout(bottom_layout)

        self.notepad_layer = QWidget(self.container)
        notepad_layout = QVBoxLayout(self.notepad_layer)
        notepad_layout.setContentsMargins(10, 10, 10, 10)
        notepad_layout.setSpacing(10)

        self.topBar = QWidget(self.notepad_layer)
        topBarLayout = QHBoxLayout(self.topBar)
        topBarLayout.setContentsMargins(0, -5, 0, 0)
        topBarLayout.addStretch()
        self.menuButton = QPushButton("≡")
        self.menuButton.setFixedSize(40, 40)
        self.menuButton.setStyleSheet("""
            QPushButton {
                background-color: #E0E5EC;
                border: none;
                font-size: 24pt;
                color: #7F8FA6;
            }
            QPushButton:hover {
                background-color: #dfe4ee;
            }
        """)
        add_neumorphic_effect(self.menuButton, blur_radius=10, x_offset=4, y_offset=4,
                                shadow_color=QColor(163, 177, 198, 150))
        self.menuButton.clicked.connect(self.toggleSettingsPanel)
        topBarLayout.addWidget(self.menuButton)
        notepad_layout.addWidget(self.topBar)

        self.settingsPanel = SettingsPanel(self.notepad_layer)
        self.settingsPanel.panelHeight = 0  # start hidden

        # Connect toggle buttons.
        self.settingsPanel.preventEditToggle.toggled.connect(self.updatePreventEdit)
        self.settingsPanel.passwordProtectionToggle.toggled.connect(self.onPasswordProtectionToggled)
        self.settingsPanel.changePasswordButton.clicked.connect(self.onChangePasswordClicked)
        # Set initial state for password protection button.
        is_protected = self.config.get("password_protected", False)
        self.settingsPanel.passwordProtectionToggle.setChecked(is_protected)
        # Set initial timeout combo selection based on config.
        timeout = self.config.get("password_timeout", 60)
        index = self.settingsPanel.timeoutComboBox.findData(timeout)
        if index >= 0:
            self.settingsPanel.timeoutComboBox.setCurrentIndex(index)
        self.settingsPanel.timeoutComboBox.currentIndexChanged.connect(self.onTimeoutChanged)
        notepad_layout.addWidget(self.settingsPanel)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Enter title here...")
        self.text_edit.setFontPointSize(16)
        self.text_edit.textChanged.connect(self.apply_formatting)
        notepad_layout.addWidget(self.text_edit)

        self.bottomBar = QWidget(self.notepad_layer)
        bottomBarLayout = QHBoxLayout(self.bottomBar)
        bottomBarLayout.setContentsMargins(0, 0, 0, 0)
        bottomBarLayout.addStretch()
        self.close_button = QPushButton("✕")
        self.close_button.setFixedSize(50, 50)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #E0E5EC;
                border: none;
                border-radius: 25px;
                font-size: 24pt;
                color: #7F8FA6;
            }
            QPushButton:hover {
                background-color: #dfe4ee;
            }
        """)
        add_neumorphic_effect(self.close_button, blur_radius=15, x_offset=6, y_offset=6,
                                shadow_color=QColor(163, 177, 198, 150))
        self.close_button.clicked.connect(self.close_notepad)
        bottomBarLayout.addWidget(self.close_button)
        bottomBarLayout.addStretch()
        notepad_layout.addWidget(self.bottomBar)

        self.notepad_layer.hide()
        self.refresh_note_list()

        self.sideBar = QWidget(self)
        self.sideBar.setGeometry(-self.sideBarWidth, 0, self.sideBarWidth, self.height())
        self.sideBar.setStyleSheet("""
            background-color: #F7F9FB;
            border-top-right-radius: 15px;
            border-bottom-right-radius: 15px;
            border: 1px solid #dfe4ee;
        """)
        sideLayout = QVBoxLayout(self.sideBar)
        sideLayout.setContentsMargins(15, 15, 15, 15)
        sideLayout.setSpacing(15)

        headerLayout = QHBoxLayout()
        headerLabel = QLabel("Menu")
        headerLabel.setFont(QFont("Segoe UI", 14, QFont.Bold))
        headerLayout.addWidget(headerLabel)
        headerLayout.addStretch()
        self.sideBarCloseButton = QPushButton("←")
        self.sideBarCloseButton.setFixedSize(30, 30)
        self.sideBarCloseButton.setStyleSheet("""
            QPushButton {
                background-color: #F7F9FB;
                border: none;
                font-size: 18pt;
                color: #7F8FA6;
            }
            QPushButton:hover {
                background-color: #dfe4ee;
            }
        """)
        self.sideBarCloseButton.clicked.connect(self.toggleSideBar)
        headerLayout.addWidget(self.sideBarCloseButton)
        sideLayout.addLayout(headerLayout)

        btn_home = QPushButton("Home")
        btn_settings = QPushButton("Settings")
        btn_about = QPushButton("About")
        for btn in (btn_home, btn_settings, btn_about):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F7F9FB;
                    border: none;
                    font-size: 14pt;
                    color: #333;
                    text-align: left;
                }
                QPushButton:hover {
                    color: #7F8FA6;
                }
            """)
            sideLayout.addWidget(btn)
        sideLayout.addStretch()

    def resizeEvent(self, event):
        container_width = self.container.width()
        container_height = self.container.height()
        self.list_layer.setGeometry(0, 0, container_width, container_height)
        self.notepad_layer.setGeometry(0, container_height, container_width, container_height)
        if self.sideBarOpen:
            self.sideBar.setGeometry(0, 0, self.sideBarWidth, self.height())
        else:
            self.sideBar.setGeometry(-self.sideBarWidth, 0, self.sideBarWidth, self.height())
        super().resizeEvent(event)

    def toggleSideBar(self):
        anim = QPropertyAnimation(self.sideBar, b"pos")
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        current_pos = self.sideBar.pos()
        if not self.sideBarOpen:
            anim.setStartValue(current_pos)
            anim.setEndValue(QPoint(0, current_pos.y()))
            self.sideBarOpen = True
        else:
            anim.setStartValue(current_pos)
            anim.setEndValue(QPoint(-self.sideBarWidth, current_pos.y()))
            self.sideBarOpen = False
        anim.start()
        self.sideBar.animation = anim

    def refresh_note_list(self):
        self.note_list_widget.clear()
        for idx, note in enumerate(self.notes):
            item = QListWidgetItem()
            widget = self.create_note_widget(note)
            item.setSizeHint(widget.sizeHint())
            self.note_list_widget.addItem(item)
            self.note_list_widget.setItemWidget(item, widget)

    def create_note_widget(self, note: dict) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #E0E5EC;
                border-radius: 15px;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        try:
            decrypted_title = self.decrypt_text(note["title"]) if note["title"] else "Untitled"
        except Exception:
            decrypted_title = "Untitled"
        title_label = QLabel(decrypted_title)
        title_font = QFont("Segoe UI", 14, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        created_str = note["created"].strftime("%Y-%m-%d %H:%M")
        updated_str = note["updated"].strftime("%Y-%m-%d %H:%M")
        info_text = f"Created: {created_str}   Last Updated: {updated_str}"
        info_label = QLabel(info_text)
        info_font = QFont("Segoe UI", 10)
        info_label.setFont(info_font)
        info_label.setStyleSheet("color: #7F8FA6;")
        layout.addWidget(info_label)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("color: #dfe4ee;")
        layout.addWidget(line)
        add_neumorphic_effect(widget, blur_radius=20, x_offset=6, y_offset=6,
                              shadow_color=QColor(163, 177, 198, 180))
        return widget

    def is_password_valid(self):
        """Return True if password protection is off or if the timeout period hasn’t expired."""
        if not self.config.get("password_protected", False):
            return True
        if self.last_password_entry is not None:
            elapsed = (datetime.datetime.now() - self.last_password_entry).total_seconds()
            if elapsed < self.config.get("password_timeout", 60):
                return True
        return False

    def check_password(self) -> bool:
        """
        If password protection is enabled and the timeout has expired, prompt the user.
        Return True if the password is correct or not needed.
        """
        if self.is_password_valid():
            return True
        dlg = PasswordDialog(title="Password Required", label_text="Enter password:", parent=self)
        if dlg.exec_() == QDialog.Accepted:
            pwd = dlg.get_password()
            if hash_password(pwd) == self.config.get("password_hash", ""):
                self.last_password_entry = datetime.datetime.now()
                return True
            else:
                QMessageBox.warning(self, "Incorrect Password", "The password you entered is incorrect.")
                return False
        return False

    def show_notepad_for_new(self):
        if not self.check_password():
            return
        # Hide the settings panel (menu) every time notepad is entered.
        self.settingsPanel.setPanelHeight(0)
        self.current_item = None
        self.current_note_index = None
        self.text_edit.clear()
        self.text_edit.setReadOnly(False)
        self.settingsPanel.preventEditToggle.setChecked(False)
        self.slide_up_notepad()

    def show_notepad_for_edit(self, item: QListWidgetItem):
        if not self.check_password():
            return
        self.settingsPanel.setPanelHeight(0)
        index = self.note_list_widget.row(item)
        note = self.notes[index]
        self.current_note_index = index
        try:
            title = self.decrypt_text(note["title"]) if note["title"] else ""
            content = self.decrypt_text(note["content"]) if note["content"] else ""
        except Exception:
            title, content = "", ""
        combined_text = title + "\n" + content if title else content
        self.text_edit.setPlainText(combined_text)
        if note.get("read_only", False):
            self.text_edit.setReadOnly(True)
            self.settingsPanel.preventEditToggle.setChecked(True)
        else:
            self.text_edit.setReadOnly(False)
            self.settingsPanel.preventEditToggle.setChecked(False)
        self.slide_up_notepad()

    def toggleSettingsPanel(self):
        expandedHeight = 120  # increased height for new widgets
        currentHeight = self.settingsPanel.height()
        anim = QPropertyAnimation(self.settingsPanel, b"panelHeight")
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        if currentHeight == 0:
            anim.setStartValue(0)
            anim.setEndValue(expandedHeight)
        else:
            anim.setStartValue(currentHeight)
            anim.setEndValue(0)
        anim.start()
        self.settingsPanel.animation = anim

    def updatePreventEdit(self, checked):
        self.text_edit.setReadOnly(checked)
        if self.current_note_index is not None:
            self.notes[self.current_note_index]["read_only"] = checked
            save_notes_to_file(self.notes)

    def onPasswordProtectionToggled(self, checked):
        if checked:
            if not self.config.get("password_hash"):
                dlg = PasswordDialog(title="Set Password", label_text="Enter new password:", parent=self)
                if dlg.exec_() == QDialog.Accepted:
                    pwd = dlg.get_password()
                    if not pwd:
                        self.settingsPanel.passwordProtectionToggle.setChecked(False)
                        return
                    confirm_dlg = PasswordDialog(title="Confirm Password", label_text="Re-enter new password:", parent=self)
                    if confirm_dlg.exec_() == QDialog.Accepted:
                        if pwd != confirm_dlg.get_password():
                            QMessageBox.warning(self, "Password Mismatch", "The passwords do not match.")
                            self.settingsPanel.passwordProtectionToggle.setChecked(False)
                            return
                        self.config["password_hash"] = hash_password(pwd)
                else:
                    self.settingsPanel.passwordProtectionToggle.setChecked(False)
                    return
            self.config["password_protected"] = True
        else:
            self.config["password_protected"] = False
        save_config(self.config)

    def onChangePasswordClicked(self):
        # If there is already a password, verify it.
        if self.config.get("password_hash"):
            dlg = PasswordDialog(title="Verify Password", label_text="Enter current password:", parent=self)
            result = dlg.exec_()
            if result == QDialog.Rejected:
                return  # User cancelled; do nothing.
            if hash_password(dlg.get_password()) != self.config.get("password_hash"):
                QMessageBox.warning(self, "Incorrect Password", "Current password is incorrect.")
                return
        # Proceed to ask for the new password.
        new_dlg = PasswordDialog(title="New Password", label_text="Enter new password:", parent=self)
        result = new_dlg.exec_()
        if result == QDialog.Rejected or not new_dlg.get_password():
            return
        confirm_dlg = PasswordDialog(title="Confirm Password", label_text="Re-enter new password:", parent=self)
        result = confirm_dlg.exec_()
        if result == QDialog.Rejected or new_dlg.get_password() != confirm_dlg.get_password():
            QMessageBox.warning(self, "Password Mismatch", "The passwords do not match.")
            return
        self.config["password_hash"] = hash_password(new_dlg.get_password())
        self.config["password_protected"] = True
        self.settingsPanel.passwordProtectionToggle.setChecked(True)
        save_config(self.config)
        QMessageBox.information(self, "Password Changed", "Your password has been updated.")

    def onTimeoutChanged(self, index):
        # When user selects a different timeout from the combo box.
        timeout = self.settingsPanel.timeoutComboBox.itemData(index)
        self.config["password_timeout"] = timeout
        save_config(self.config)

    def slide_up_notepad(self):
        container_height = self.container.height()
        self.notepad_layer.show()
        anim_list = QPropertyAnimation(self.list_layer, b"pos")
        anim_list.setDuration(300)
        anim_list.setStartValue(self.list_layer.pos())
        anim_list.setEndValue(QPoint(0, container_height))
        anim_list.setEasingCurve(QEasingCurve.OutCubic)
        anim_notepad = QPropertyAnimation(self.notepad_layer, b"pos")
        anim_notepad.setDuration(300)
        anim_notepad.setStartValue(self.notepad_layer.pos())
        anim_notepad.setEndValue(QPoint(0, 0))
        anim_notepad.setEasingCurve(QEasingCurve.OutCubic)
        group = QParallelAnimationGroup()
        group.addAnimation(anim_list)
        group.addAnimation(anim_notepad)
        group.start()
        self.current_animation = group

    def close_notepad(self):
        if self.text_edit.isReadOnly():
            self.slide_down_notepad()
            return

        full_text = self.text_edit.toPlainText().strip()
        if full_text:
            lines = full_text.splitlines()
            title_text = lines[0]
            content_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            now = datetime.datetime.now()
            encrypted_title = self.encrypt_text(title_text)
            encrypted_content = self.encrypt_text(content_text)
            if self.current_note_index is None:
                new_note = {
                    "title": encrypted_title,
                    "content": encrypted_content,
                    "created": now,
                    "updated": now,
                    "read_only": False
                }
                self.notes.append(new_note)
            else:
                note = self.notes[self.current_note_index]
                note["title"] = encrypted_title
                note["content"] = encrypted_content
                note["updated"] = now
        self.refresh_note_list()
        save_notes_to_file(self.notes)
        self.slide_down_notepad()

    def slide_down_notepad(self):
        container_height = self.container.height()
        anim_list = QPropertyAnimation(self.list_layer, b"pos")
        anim_list.setDuration(300)
        anim_list.setStartValue(self.list_layer.pos())
        anim_list.setEndValue(QPoint(0, 0))
        anim_list.setEasingCurve(QEasingCurve.OutCubic)
        anim_notepad = QPropertyAnimation(self.notepad_layer, b"pos")
        anim_notepad.setDuration(300)
        anim_notepad.setStartValue(self.notepad_layer.pos())
        anim_notepad.setEndValue(QPoint(0, container_height))
        anim_notepad.setEasingCurve(QEasingCurve.InQuad)
        group = QParallelAnimationGroup()
        group.addAnimation(anim_list)
        group.addAnimation(anim_notepad)
        group.finished.connect(self.notepad_layer.hide)
        group.start()
        self.current_animation = group

    def apply_formatting(self):
        self.text_edit.blockSignals(True)
        doc = self.text_edit.document()
        block = doc.firstBlock()
        first = True
        while block.isValid():
            cursor = QTextCursor(block)
            cursor.select(QTextCursor.BlockUnderCursor)
            fmt = QTextCharFormat()
            fmt.setFontFamily("Segoe UI")
            if first:
                fmt.setFontPointSize(22)
                fmt.setFontWeight(QFont.Bold)
            else:
                fmt.setFontPointSize(16)
                fmt.setFontWeight(QFont.Normal)
            cursor.setCharFormat(fmt)
            first = False
            block = block.next()
        self.text_edit.blockSignals(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NotesApp()
    window.show()
    sys.exit(app.exec_())
