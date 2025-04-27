from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QFrame
from PyQt5.QtCore import Qt, pyqtSignal

class HSVSliderGroup(QWidget):
    valueChanged = pyqtSignal(dict)
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.sliders = {}
        self._init_ui(title)
    
    def _init_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Başlık
        self._add_title(layout, title)
        
        # Sliderlar
        self._create_sliders(layout)
    
    def _add_title(self, layout, title):
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                font-size: 12px;
                padding: 5px;
                border-bottom: 1px solid #bdc3c7;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(title_label)
    
    def _add_separator(self, layout):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("QFrame { color: #bdc3c7; }")
        layout.addWidget(separator)
    
    def _create_sliders(self, layout):
        for hsv_type, ranges in [
            ('H', [(0, 180), (180, 180)]),
            ('S', [(0, 255), (255, 255)]),
            ('V', [(0, 255), (255, 255)])
        ]:
            # Ayırıcı çizgi
            self._add_separator(layout)
            
            # Min/Max sliderları
            for i, (default, max_val) in enumerate(ranges):
                name = f'{hsv_type} {"Min" if i == 0 else "Max"}'
                slider_layout = QHBoxLayout()
                
                label = QLabel(name)
                label.setFixedWidth(50)
                label.setStyleSheet("QLabel { color: #34495e; }")
                
                slider = QSlider(Qt.Horizontal)
                slider.setMinimum(0)
                slider.setMaximum(max_val)
                slider.setValue(default)
                
                value_label = QLabel(str(default))
                value_label.setFixedWidth(30)
                value_label.setStyleSheet("QLabel { color: #2980b9; }")
                
                slider.valueChanged.connect(
                    lambda v, label=value_label, name=name: self.on_slider_change(v, label, name))
                
                slider_layout.addWidget(label)
                slider_layout.addWidget(slider)
                slider_layout.addWidget(value_label)
                
                layout.addLayout(slider_layout)
                self.sliders[name] = (slider, value_label)
    
    def on_slider_change(self, value, label, name):
        label.setText(str(value))
        self.valueChanged.emit(self.get_values())
    
    def get_values(self):
        return {name: slider[0].value() for name, slider in self.sliders.items()}
    
    def set_values(self, values):
        for name, value in values.items():
            if name in self.sliders:
                slider, label = self.sliders[name]
                print(f"Slider güncelleniyor: {name} = {value}")  # Hata ayıklama için
                slider.setValue(value)
                label.setText(str(value)) 