from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QStackedWidget,
                             QGroupBox, QLabel, QPushButton, QFormLayout,
                             QSpinBox, QCheckBox, QSizePolicy, QProgressBar, QMessageBox,
                             QFileDialog)
from PyQt5.QtCore import pyqtSignal, pyqtSlot

class ModePanel(QWidget):
    mode_changed = pyqtSignal(str) # Seçilen modun adını yayınla

    # --- Arka uç ile etkileşim için sinyaller ---
    start_test_signal = pyqtSignal(int, int, bool, str) # başlangıç_karesi, bitiş_karesi, tam_kullan, dedektör_tipi
    cancel_test_signal = pyqtSignal()
    load_yolo_model_signal = pyqtSignal(str) # model_yolu
    export_results_signal = pyqtSignal(str) # çıktı_yolu
    load_test_yolo_model_signal = pyqtSignal(str) # model_yolu (Test modu için)
    show_contours_signal = pyqtSignal(bool) # Kontur gösterme sinyali

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # --- Mod Seçimi ---
        mode_selection_group = QGroupBox("İşlem Modu Seçimi")
        mode_selection_layout = QVBoxLayout(mode_selection_group)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["OpenCV (Renk Tabanlı)", "Test Modu", "YOLO Modu"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_selection_layout.addWidget(self.mode_combo)

        main_layout.addWidget(mode_selection_group)

        # --- Mode Specific Controls ---
        self.stacked_widget = QStackedWidget()
        self._create_opencv_mode_widget()
        self._create_test_mode_widget()
        self._create_yolo_mode_widget()

        main_layout.addWidget(self.stacked_widget)
        main_layout.addStretch(1) # Widget'ları yukarı iter

        # Başlangıç modunu ayarla
        self._on_mode_changed(0)

    def _create_opencv_mode_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)

        description = QLabel(
            "Mevcut renk tabanlı (HSV) balon tespit algoritmasını kullanır.\n"
            "Ayarlar Preset Panelinden yönetilir."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.show_contours_checkbox = QCheckBox("Konturları Göster (Geliştirme)")
        self.show_contours_checkbox.setToolTip("Tespit edilen maske/konturları ayrı bir pencerede gösterir.")
        self.show_contours_checkbox.toggled.connect(self.show_contours_signal.emit) # Sinyali doğrudan yayınla
         # self.show_contours_checkbox.stateChanged.connect(self.on_show_contours_changed)
        layout.addWidget(self.show_contours_checkbox)


        layout.addStretch(1)
        self.stacked_widget.addWidget(widget)

    def _create_test_mode_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)

        description = QLabel(
            "Videoyu toplu olarak işlemek, tespit geçmişini kaydetmek, istatistik raporları oluşturmak ve verileri dışa aktarmak içindir."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        test_group = QGroupBox("Test Kontrolleri")
        test_layout = QFormLayout(test_group)

        # --- Dedektör Seçimi ---
        self.test_detector_combo = QComboBox()
        self.test_detector_combo.addItems(["OpenCV (HSV)", "YOLO"])
        self.test_detector_combo.currentTextChanged.connect(self._on_test_detector_changed) # YOLO butonunu göster/gizle
        test_layout.addRow("Dedektör:", self.test_detector_combo)

        # --- Teste Özel YOLO Yükleme ---
        test_yolo_layout = QHBoxLayout() # Buton ve etiket için
        self.load_test_yolo_button = QPushButton("YOLO Modeli Seç...")
        self.load_test_yolo_button.clicked.connect(self._on_load_test_yolo_model)
        self.test_yolo_model_label = QLabel("Model Seçilmedi")
        self.test_yolo_model_label.setWordWrap(True)
        test_yolo_layout.addWidget(self.load_test_yolo_button)
        test_yolo_layout.addWidget(self.test_yolo_model_label, 1) # Etiket genişlesin
        self.test_yolo_row_widget = QWidget() # Layout'u içeren widget
        self.test_yolo_row_widget.setLayout(test_yolo_layout)
        test_layout.addRow(self.test_yolo_row_widget) # Widget'ı satıra ekle
        self.test_yolo_row_widget.setVisible(False) # Başlangıçta gizle
        # --- ---


        self.start_frame_spin = QSpinBox()
        self.start_frame_spin.setRange(0, 999999)
        self.end_frame_spin = QSpinBox()
        self.end_frame_spin.setRange(0, 999999)
        self.process_full_checkbox = QCheckBox("Tüm Videoyu İşle")
        self.process_full_checkbox.setChecked(True)
        self.process_full_checkbox.toggled.connect(self._toggle_frame_spins)

        test_layout.addRow("Başlangıç Frame:", self.start_frame_spin)
        test_layout.addRow("Bitiş Frame:", self.end_frame_spin)
        test_layout.addRow(self.process_full_checkbox)

        # Test Buttons and Progress
        button_layout = QHBoxLayout()

        self.start_test_button = QPushButton("Testi Başlat")
        self.start_test_button.clicked.connect(self._on_start_test)
        self.cancel_test_button = QPushButton("İptal Et")
        self.cancel_test_button.clicked.connect(self._on_cancel_test)
        self.cancel_test_button.setEnabled(False) # Test başladığında etkinleştir
        button_layout.addWidget(self.start_test_button)
        button_layout.addWidget(self.cancel_test_button)
        test_layout.addRow(button_layout)

        self.export_results_button = QPushButton("Sonuçları Dışa Aktar")
        self.export_results_button.setEnabled(False) # Test bittikten sonra etkinleştir
        self.export_results_button.clicked.connect(self._on_export_results)
        test_layout.addRow(self.export_results_button)

        # Test İlerleme ve Durum
        self.test_progress_bar = QProgressBar()
        self.test_progress_bar.setTextVisible(True)
        self.test_progress_bar.setValue(0)
        self.test_status_label = QLabel("Durum: Beklemede")
        self.test_status_label.setWordWrap(True)
        test_layout.addRow("İlerleme:", self.test_progress_bar)
        test_layout.addRow(self.test_status_label)

        self._toggle_frame_spins(True) # Başlangıç durumunu ayarla

        layout.addWidget(test_group)
        layout.addStretch(1)
        self.stacked_widget.addWidget(widget)

    def _create_yolo_mode_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 5)

        description = QLabel(
            "Önceden eğitilmiş bir YOLO modeli (.pt dosyası) kullanarak nesne tespiti yapar.\n"
            "('ultralytics' kütüphanesi gereklidir).\n"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        yolo_group = QGroupBox("YOLO Kontrolleri")
        yolo_layout = QVBoxLayout(yolo_group) # Buton ve etiket için QVBoxLayout kullan

        self.load_model_button = QPushButton("YOLO Modelini Yükle (.pt)")
        # Ultralytics kullanılabilirliğine göre mi etkinleştirilsin? Yoksa her zaman mı?
        self.load_model_button.clicked.connect(self._on_load_yolo_model)

        self.loaded_model_label = QLabel("Yüklenen Model: Yok")
        self.loaded_model_label.setWordWrap(True)

        yolo_layout.addWidget(self.load_model_button)
        yolo_layout.addWidget(self.loaded_model_label)

        layout.addWidget(yolo_group)
        layout.addStretch(1)
        self.stacked_widget.addWidget(widget)

    def _on_mode_changed(self, index):
        self.stacked_widget.setCurrentIndex(index)
        selected_mode = self.mode_combo.currentText()
        self.mode_changed.emit(selected_mode)
        print(f"Mod değiştirildi: {selected_mode}") # Hata ayıklama
        # Kontur checkbox'ını sadece OpenCV modunda etkinleştir
        is_opencv_mode = "OpenCV" in selected_mode
        self.show_contours_checkbox.setEnabled(is_opencv_mode)
        if not is_opencv_mode:
            self.show_contours_checkbox.setChecked(False) # Mod değişince kapat
        # Test modundaysak ve YOLO seçiliyse ilgili satırı göster/gizle
        self._update_test_yolo_visibility()

        
    def _on_test_detector_changed(self, detector_name):
        """Test dedektörü değiştiğinde YOLO model seçme alanını göster/gizle."""
        self._update_test_yolo_visibility()

    def _update_test_yolo_visibility(self):
        show_yolo_options = ("YOLO" in self.test_detector_combo.currentText()) and (self.stacked_widget.currentIndex() == 1) # Index 1 Test Modu varsayımı
        self.test_yolo_row_widget.setVisible(show_yolo_options)

    def _toggle_frame_spins(self, checked):
        """'Tamamını İşle' checkbox'ına göre frame spin kutularını etkinleştir/devre dışı bırak."""
        self.start_frame_spin.setEnabled(not checked)
        self.end_frame_spin.setEnabled(not checked)

    # --- UI'ı sinyallere bağlayan slotlar ---
    def _on_start_test(self):
        start_frame = self.start_frame_spin.value()
        end_frame = self.end_frame_spin.value()
        process_full = self.process_full_checkbox.isChecked()
        detector_type = self.test_detector_combo.currentText()
        # Doğrulama ekle? örn., tam değilse end_frame > start_frame
        self.start_test_button.setEnabled(False)
        self.cancel_test_button.setEnabled(True)
        self.export_results_button.setEnabled(False)
        self.test_status_label.setText("Durum: Başlatılıyor...")
        self.test_progress_bar.setValue(0)
        self.start_test_signal.emit(start_frame, end_frame, process_full, detector_type)

    def _on_cancel_test(self):
        self.test_status_label.setText("Durum: İptal ediliyor...")
        self.cancel_test_button.setEnabled(False)
        self.cancel_test_signal.emit()

    def _on_export_results(self):
        default_name = "test_results.csv"
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Test Sonuçlarını Kaydet", default_name, "CSV Dosyaları (*.csv)")
        if file_name:
            self.export_results_signal.emit(file_name)
            self.test_status_label.setText(f"Durum: Sonuçlar şuraya aktarılıyor: {file_name}")

    def _on_load_yolo_model(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "YOLO Modeli Seç", "", "PyTorch Modelleri (*.pt)")
        if file_name:
            self.loaded_model_label.setText(f"Yüklenen Model: Seçildi, yükleniyor...")
            # Yükleme sırasında butonu devre dışı bırak? Yükleme hızlıysa gerekmeyebilir.
            self.load_yolo_model_signal.emit(file_name)

    # --- Arka uçtan güncellemeleri alan slotlar ---
    @pyqtSlot(int, int, str)
    def update_test_progress(self, percentage, count, status):
        self.test_progress_bar.setValue(percentage)
        self.test_status_label.setText(f"Durum: {status}")

    @pyqtSlot(bool) # Bitiş sinyalinin başarı/tamamlanma belirttiğini varsayalım
    def on_test_completed(self, completed_successfully):
        self.start_test_button.setEnabled(True)
        self.cancel_test_button.setEnabled(False)
        self.export_results_button.setEnabled(completed_successfully) # Sadece başarılıysa export et
        # Optional: Reset progress bar/status if needed or show final status
        if not completed_successfully:
            self.test_status_label.setText("Durum: Test başarısız oldu veya iptal edildi.")
            # Reset progress bar?
            # self.test_progress_bar.setValue(0)
        else:
            self.test_status_label.setText("Durum: Test tamamlandı.")

    @pyqtSlot(bool, str)
    def on_yolo_model_loaded(self, success, message):
        # Update the label based on success/failure
        if success:
            # Extract filename from the message (assuming message is like "Model loaded: path/to/model.pt")
            try:
                filename = message.split(': ')[-1].split('/')[-1].split('\\')[-1]
                self.loaded_model_label.setText(f"Yüklenen Model: {filename}")
            except Exception:
                self.loaded_model_label.setText(f"Yüklenen Model: Başarılı ({message})")
        else:
            self.loaded_model_label.setText(f"Model Yükleme Hatası: {message}")
            # Re-enable button?
            # self.load_model_button.setEnabled(True)

    def _on_load_test_yolo_model(self):
        """Opens file dialog to select YOLO model specifically for Test mode."""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Test İçin YOLO Modeli Seç", "", "PyTorch Modelleri (*.pt)")
        if file_name:
            self.load_test_yolo_model_signal.emit(file_name) # Emit signal to MainWindow
            # Label updated via slot below

    @pyqtSlot(str)
    def update_test_yolo_label(self, model_path):
        """Updates the label showing the selected YOLO model for Test mode."""
        if model_path:
            try:
                filename = model_path.split('/')[-1].split('\\')[-1]
                self.test_yolo_model_label.setText(f"YOLO Model: {filename}")
            except Exception:
                self.test_yolo_model_label.setText(f"YOLO Model: {model_path}")
        else:
            self.test_yolo_model_label.setText("Model Seçilmedi")

    # --- Helper Methods for UI Management ---
    def set_opencv_options_visibility(self, visible):
        self.show_contours_checkbox.setVisible(visible)
        # Add other OpenCV specific controls here if any

    def set_yolo_options_visibility(self, visible):
        self.load_model_button.setVisible(visible)
        self.loaded_model_label.setVisible(visible)
        # Add other YOLO specific controls here if any

    def set_test_options_visibility(self, visible):
        # Iterate through all widgets in the test group layout and set visibility
        test_group = self.stacked_widget.widget(1).findChild(QGroupBox) # Assuming Test is index 1
        if test_group:
            test_group.setVisible(visible)
        # Add other Test specific controls here if any