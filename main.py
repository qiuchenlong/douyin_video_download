import sys
from PySide6.QtWidgets import (QApplication)

from kuaishou_widget import KuaishouWidget
from core import Core


def run_core():
    Core().Start()

def main():
    app = QApplication(sys.argv)

    # widget = TiktokShopWidget()
    widget = KuaishouWidget()
    # 设置QWidget的固定大小
    widget.setFixedSize(650, 550)
    widget.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
    # run_core()
