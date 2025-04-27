from PyQt5.QtWidgets import QVBoxLayout, QFormLayout, QLabel, QGroupBox
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, pyqtSlot


class TimingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.metric_labels = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)
        metrics_group = QGroupBox("Ortalama Süreler (ms)")
        metrics_layout = QFormLayout()
        metrics_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        metrics_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        metrics_layout.setLabelAlignment(Qt.AlignLeft)
        metric_keys = {
            'avg_frame_time': "Toplam Kare Süresi:",
            'avg_capture_time': "Kare Yakalama Süresi:",
            'avg_detection_time': "Tespit Süresi:",
            'avg_visualization_time': "Görselleştirme Süresi:",
        }
        for key, label_text in metric_keys.items():
            value_label = QLabel("- ms")
            metrics_layout.addRow(label_text, value_label)
            self.metric_labels[key] = value_label
        metrics_group.setLayout(metrics_layout)
        main_layout.addWidget(metrics_group)
        main_layout.addStretch(1)
        self.setLayout(main_layout)

    @pyqtSlot(dict)
    def update_timings(self, metrics):
        for key, label_widget in self.metric_labels.items():
            if key in metrics:
                value = metrics[key]
                label_widget.setText(f"{value:.2f} ms")
            else:
                label_widget.setText("- ms")
