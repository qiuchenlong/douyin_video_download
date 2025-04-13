import time

from PySide6.QtWidgets import (
    QLabel, QPushButton, QLineEdit, QTextEdit, QVBoxLayout, QWidget, QHBoxLayout, QApplication,
    QRadioButton, QTimeEdit
)
from PySide6.QtGui import QPalette, QColor, QIntValidator
from PySide6.QtCore import QThread, Signal, QSettings, QTimer, QTime
import sys
from core import Core


TITLE = '抖音下载器'


class InitThread(QThread):
    finished = Signal()

    def __init__(self, core, urls):
        super().__init__()
        self.core = core
        self.urls = urls
        self._running = True

    def run(self):
        self.core.Init()  # 假设你的 Core 有 download 方法
            # time.sleep(1000)
        self.finished.emit()

    def stop(self):
        self._running = False

class DownloadThread(QThread):
    finished = Signal()

    def __init__(self, core, urls):
        super().__init__()
        self.core = core
        self.urls = urls
        self._running = True

    def run(self):
        for url in self.urls:
            if not self._running:
                break
            self.core.Set_profile_url(url)
            self.core.Start()  # 假设你的 Core 有 download 方法
            # time.sleep(1000)
        self.finished.emit()

    def stop(self):
        self._running = False

class KuaishouWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self.settings = QSettings("MyCompany", "TiktokTool")  # 定义存储位置
        self.init_ui()
        self.init_event()
        # self.load_settings()  # 载入上次保存的数据

        self.core = Core()
        self.worker_thread = None  # 线程对象
        self.init_worker_thread = None
        self.timer = QTimer(self)

        # Connect Core's log_signal to the update_log function
        self.core.log_signal.connect(self.update_log)


    def closeEvent(self, event):
        print('closeEvent...')
        # 当窗口关闭时调用 core 的关闭方法
        if self.core:
            self.core.Close()
        event.accept()

    def init_ui(self):
        # 主布局
        layout = QVBoxLayout()

        # 多行文本输入框，用于填写 URL
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("请输入要下载的个人主页URL，一行一个")
        layout.addWidget(QLabel("个人主页 URL 列表："))
        layout.addWidget(self.url_input)

        # 按钮布局（开始和停止）
        button_layout = QHBoxLayout()
        self.init_button = QPushButton("初始化")
        self.login_confirm_button = QPushButton("我已登录")
        self.login_confirm_button.setEnabled(False)
        self.start_button = QPushButton("开始")
        self.stop_button = QPushButton("停止")
        button_layout.addWidget(self.init_button)
        button_layout.addWidget(self.login_confirm_button)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        layout.addLayout(button_layout)

        # 状态标签
        self.status_label = QLabel("状态：就绪")
        palette = QPalette()
        palette.setColor(QPalette.WindowText, QColor("green"))
        self.status_label.setPalette(palette)
        layout.addWidget(self.status_label)

        # 添加日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setPlaceholderText("运行日志显示区域...")
        self.log_display.setReadOnly(True)  # 使其不可编辑
        layout.addWidget(QLabel("运行日志："))
        layout.addWidget(self.log_display)

        # 应用主布局
        self.setLayout(layout)

    def init_event(self):
        self.init_button.clicked.connect(self.init_download)
        self.login_confirm_button.clicked.connect(self.on_login_confirmed)
        self.start_button.clicked.connect(self.start_download)
        self.stop_button.clicked.connect(self.stop_download)
        self.stop_button.setEnabled(False)  # 初始状态禁用

    def init_download(self):
        self.login_confirm_button.setEnabled(True)
        self.status_label.setText("状态：请扫码登录抖音，然后点击【我已登录】")
        self.status_label.setStyleSheet("color: blue;")

        # 创建并启动后台线程下载
        self.worker_thread = InitThread(self.core, 'https://www.douyin.com/')
        self.worker_thread.finished.connect(self.download_finished)
        self.worker_thread.start()

    def on_login_confirmed(self):
        self.status_label.setText("状态：正在保存 Cookies...")
        self.status_label.setStyleSheet("color: orange;")
        self.core.save_cookies(self.core.page)
        self.status_label.setText("状态：已保存 Cookies")
        self.login_confirm_button.setEnabled(False)

    def start_download(self):
        # 读取URL列表
        urls_text = self.url_input.toPlainText()
        urls = [line.strip() for line in urls_text.splitlines() if line.strip()]

        if not urls:
            self.status_label.setText("状态：请输入至少一个 URL")
            self.status_label.setStyleSheet("color: red;")
            return

        # 更新UI状态
        self.status_label.setText("状态：下载中...")
        self.status_label.setStyleSheet("color: orange;")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # 创建并启动后台线程下载
        self.worker_thread = DownloadThread(self.core, urls)
        self.worker_thread.finished.connect(self.download_finished)
        self.worker_thread.start()

    def stop_download(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()  # 你需要确保 DownloadThread 有 stop() 方法
            self.worker_thread.quit()
            # self.worker_thread.wait()

        self.status_label.setText("状态：已停止")
        self.status_label.setStyleSheet("color: red;")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def download_finished(self):
        self.status_label.setText("状态：下载完成")
        self.status_label.setStyleSheet("color: green;")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_log(self, log_message):
        """ This method will be called whenever a log message is emitted from Core. """
        self.log_display.append(log_message)  # Append the log message to the QTextEdit
        self.log_display.ensureCursorVisible()  # Make sure the cursor is always visible
