from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QFormLayout, QLabel, QGroupBox, QSpinBox
from balloon_detector import config

class ConfigPanel(QWidget):
    target_fps_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_fps_spinbox = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # --- Video Ayarları ---
        video_group = QGroupBox("Video Ayarları")
        video_layout = QFormLayout()
        video_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        video_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        video_layout.setLabelAlignment(Qt.AlignLeft)
        
        if hasattr(config, 'VIDEO_SETTINGS') and isinstance(config.VIDEO_SETTINGS, dict):
            for key, value in config.VIDEO_SETTINGS.items():
                if key == 'TARGET_FPS':
                    self.target_fps_spinbox = QSpinBox()
                    self.target_fps_spinbox.setToolTip("Video işlemcinin hedefleyeceği maksimum kare hızı.")
                    self.target_fps_spinbox.setRange(1, 300) 
                    self.target_fps_spinbox.setValue(int(value))
                    self.target_fps_spinbox.valueChanged.connect(self.target_fps_changed.emit)
                    video_layout.addRow(f"{key}:", self.target_fps_spinbox)
                else:
                    label_widget = QLabel(str(value))
                    label_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    video_layout.addRow(f"{key}:", label_widget)
        else:
             video_layout.addRow(QLabel("VIDEO_SETTINGS bulunamadı."))

        video_group.setLayout(video_layout)
        main_layout.addWidget(video_group)

        # --- Tespit Ayarları ---
        detection_group = QGroupBox("Tespit Ayarları")
        detection_layout = QFormLayout()
        detection_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        detection_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        detection_layout.setLabelAlignment(Qt.AlignLeft)

        if hasattr(config, 'DETECTION_SETTINGS') and isinstance(config.DETECTION_SETTINGS, dict):
            for key, value in config.DETECTION_SETTINGS.items():
                label_widget = QLabel(str(value))
                label_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
                detection_layout.addRow(f"{key}:", label_widget)
        else:
             detection_layout.addRow(QLabel("DETECTION_SETTINGS bulunamadı."))

        detection_group.setLayout(detection_layout)
        main_layout.addWidget(detection_group)
        
        main_layout.addStretch(1)
        self.setLayout(main_layout)