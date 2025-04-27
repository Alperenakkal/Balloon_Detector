from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QComboBox, QPushButton,
                           QInputDialog, QScrollArea, QLabel, QFormLayout, QGroupBox)
from PyQt5.QtCore import pyqtSignal, Qt
from .collapsible_box import QCollapsibleBox
from .hsv_slider_group import HSVSliderGroup

class PresetPanel(QWidget):
    preset_selected = pyqtSignal(str)
    preset_saved = pyqtSignal(str, dict)
    hsv_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.slider_groups = {}
        self._init_ui()
    
    def _init_ui(self):
        # Ana dış layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0) # Dış kenar boşluklarını sıfırla

        # Scroll Area oluştur (içerik çok uzun olursa kaydırılabilir olması için)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True) # İçeriğin scroll area'yı doldurmasını sağla
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Yatay scroll'u kapat

        # Scroll Area'nın içereceği asıl widget (bu widget'ın layout'u içerikleri tutar)
        scroll_content_widget = QWidget()
        
        # İçerik layout'u (bu layout scroll edilecek)
        content_layout = QVBoxLayout(scroll_content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5) # İçerik için kenar boşluğu
        content_layout.setSpacing(10) # Widget'lar arası boşluk
        
        # Preset kontrollerini oluştur ve layout'a ekle
        self._create_preset_controls(content_layout)
        
        # Normal mod ayarlarını oluştur ve layout'a ekle
        self._create_normal_mode_settings(content_layout)
        
        # Lazer mod ayarlarını oluştur ve layout'a ekle
        self._create_laser_mode_settings(content_layout)

        # Esnek alan ekle (widget'ları yukarı iter)
        content_layout.addStretch(1)

        # content_layout'u scroll edilecek widget'a ata
        scroll_content_widget.setLayout(content_layout)
        
        # Scroll edilecek widget'ı scroll area'ya ata
        scroll_area.setWidget(scroll_content_widget)
        
        # Scroll area'yı ana dış layout'a ekle
        outer_layout.addWidget(scroll_area)
        
        # Slider değişiklik bağlantıları
        for group in self.slider_groups.values():
            group.valueChanged.connect(self._on_hsv_changed)
        
        # Ana widget'ın layout'unu ayarla
        self.setLayout(outer_layout)
    
    def _create_preset_controls(self, layout):
        preset_box = QCollapsibleBox("Preset Kontrolleri", collapsed=True)
        
        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        
        save_preset_btn = QPushButton("Preset Kaydet")
        save_preset_btn.clicked.connect(self._on_save_preset)
        
        preset_layout = QVBoxLayout()
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(save_preset_btn)
        
        preset_widget = QWidget()
        preset_widget.setLayout(preset_layout)
        preset_box.addWidget(preset_widget)
        
        layout.addWidget(preset_box)
    
    def _create_normal_mode_settings(self, layout):
        normal_box = QCollapsibleBox("Normal Mod Ayarları", collapsed=True)
        normal_box.setStyleSheet("QGroupBox { background-color: #f8f9fa; }") # Hafif arkaplan rengi
        self.slider_groups['normal_blue'] = HSVSliderGroup("Normal Mavi Ayarları")
        self.slider_groups['normal_red1'] = HSVSliderGroup("Normal Kırmızı-1 Ayarları")
        self.slider_groups['normal_red2'] = HSVSliderGroup("Normal Kırmızı-2 Ayarları")
        
        normal_widget = QWidget()
        normal_layout = QVBoxLayout(normal_widget)
        for group in ['normal_blue', 'normal_red1', 'normal_red2']:
            normal_layout.addWidget(self.slider_groups[group])
        
        normal_box.addWidget(normal_widget)
        layout.addWidget(normal_box)
    
    def _create_laser_mode_settings(self, layout):
        laser_box = QCollapsibleBox("Lazer Mod Ayarları", collapsed=True)
        laser_box.setStyleSheet("QGroupBox { background-color: #f8f9fa; }") # Hafif arkaplan rengi
        self.slider_groups['laser_blue'] = HSVSliderGroup("Lazer Mavi Ayarları")
        self.slider_groups['laser_red1'] = HSVSliderGroup("Lazer Kırmızı-1 Ayarları")
        self.slider_groups['laser_red2'] = HSVSliderGroup("Lazer Kırmızı-2 Ayarları")
        
        laser_widget = QWidget()
        laser_layout = QVBoxLayout(laser_widget)
        for group in ['laser_blue', 'laser_red1', 'laser_red2']:
            laser_layout.addWidget(self.slider_groups[group])
        
        laser_box.addWidget(laser_widget)
        layout.addWidget(laser_box)
    
    def update_presets(self, preset_names):
        """Preset listesini günceller."""
        current_text = self.preset_combo.currentText()
        self.preset_combo.blockSignals(True) # Sinyal göndermeyi geçici durdur
        self.preset_combo.clear()
        self.preset_combo.addItems(preset_names)
        # Önceki seçili preseti tekrar seçmeye çalış
        index = self.preset_combo.findText(current_text)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        self.preset_combo.blockSignals(False) # Sinyalleri tekrar etkinleştir
    
    def set_values(self, values):
        """Tüm HSV slider gruplarının değerlerini ayarlar."""
        for group_name, group_values in values.items():
            if group_name in self.slider_groups:
                self.slider_groups[group_name].set_values(group_values)
    
    def get_values(self):
        """Tüm HSV slider gruplarından mevcut değerleri alır."""
        return {
            name: group.get_values()
            for name, group in self.slider_groups.items()
        }
    
    # Olay işleyiciler (Event Handlers)
    def _on_preset_selected(self, name):
        """Preset seçildiğinde tetiklenir."""
        if name: # Boş seçim değilse sinyal gönder
            self.preset_selected.emit(name)
    
    def _on_save_preset(self):
        """Preset kaydet butonuna basıldığında tetiklenir."""
        name, ok = QInputDialog.getText(self, 'Preset Kaydet', 
                                      'Preset adını girin:')
        if ok and name: # Kullanıcı OK dedi ve isim girdiyse
            values = self.get_values()
            self.preset_saved.emit(name, values)
    
    def _on_hsv_changed(self, values):
        """Herhangi bir HSV slider değiştiğinde tetiklenir."""
        # Tüm HSV değerlerini içeren bir sözlük gönder
        all_values = self.get_values()
        self.hsv_changed.emit(all_values) 