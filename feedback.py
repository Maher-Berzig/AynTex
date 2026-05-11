import sys
import json
import platform
import smtplib
from email.message import EmailMessage

import psutil
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QComboBox, QMessageBox
)

# =========================
# CONFIGURATION
# =========================

APP_VERSION = "1.0.0"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = "@yourdomain.com"
SMTP_PASSWORD = "APP_PASSWORD"

MASKED_EMAIL = "maths.ipeiem@gmail.com"

# =========================
# SYSTEM INFO COLLECTION
# =========================

def collect_system_info(app_version: str):
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "python_version": sys.version,
        "cpu_cores": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "app_version": app_version,
    }

# =========================
# EMAIL SENDING
# =========================

def send_email(user_email, feedback_type, message, system_info):
    msg = EmailMessage()
    msg["Subject"] = f"[Feedback] {feedback_type}"
    msg["From"] = MASKED_EMAIL
    msg["To"] = MASKED_EMAIL
    msg["Reply-To"] = user_email

    body = f"""
User email: {user_email}
Feedback type: {feedback_type}

Message:
{message}
"""

    if system_info:
        body += "\n\nSystem information:\n"
        body += json.dumps(system_info, indent=2)

    msg.set_content(body)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

# =========================
# FEEDBACK DIALOG
# =========================

class FeedbackDialog(QDialog):
    def __init__(self, app_version):
        super().__init__()

        self.app_version = app_version
        self.system_info = None

        self.setWindowTitle("Send Feedback")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Email
        layout.addWidget(QLabel("Your email address"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("you@example.com")
        layout.addWidget(self.email_input)

        # Feedback type
        layout.addWidget(QLabel("Feedback type"))
        self.type_box = QComboBox()
        self.type_box.addItems(["Bug report", "Suggestion"])
        layout.addWidget(self.type_box)

        # Message
        layout.addWidget(QLabel("Message"))
        self.message_box = QTextEdit()
        self.message_box.setPlaceholderText("Describe the problem or suggestion")
        layout.addWidget(self.message_box)

        # Buttons
        self.collect_btn = QPushButton("Collect system information")
        self.send_btn = QPushButton("Send feedback")

        self.collect_btn.clicked.connect(self.collect_info)
        self.send_btn.clicked.connect(self.send_feedback)

        layout.addWidget(self.collect_btn)
        layout.addWidget(self.send_btn)

        # Privacy notice
        privacy = QLabel(
            "System information is optional and will only be sent with your confirmation."
        )
        privacy.setWordWrap(True)
        layout.addWidget(privacy)

    def collect_info(self):
        info = collect_system_info(self.app_version)
        preview = json.dumps(info, indent=2)

        reply = QMessageBox.question(
            self,
            "Confirm system information",
            "The following information will be included:\n\n"
            f"{preview}\n\n"
            "Do you want to include it?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.system_info = info
        else:
            self.system_info = None

    def send_feedback(self):
        #print("Resolving SMTP server...")
        import socket
        #print(socket.gethostbyname(SMTP_SERVER))

        if not self.email_input.text().strip():
            QMessageBox.warning(self, "Missing email", "Please enter your email.")
            return

        if not self.message_box.toPlainText().strip():
            QMessageBox.warning(self, "Empty message", "Please enter a message.")
            return

        try:
            send_email(
                user_email=self.email_input.text().strip(),
                feedback_type=self.type_box.currentText(),
                message=self.message_box.toPlainText().strip(),
                system_info=self.system_info,
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to send feedback:\n{e}"
            )
            return

        QMessageBox.information(
            self,
            "Thank you",
            "Your feedback has been sent successfully."
        )
        self.accept()

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = FeedbackDialog(APP_VERSION)
    dialog.exec_()
