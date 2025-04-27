import sys
from PyQt5.QtWidgets import QApplication
from balloon_detector.gui.main_window import BalloonDetectorGUI

def main():
    app = QApplication(sys.argv)
    window = BalloonDetectorGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 