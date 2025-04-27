from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QProgressBar, QSpinBox, QCheckBox,
                           QFileDialog, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QImage, QPixmap

class VideoPanel(QWidget):
    video_toggled = pyqtSignal(bool)
    file_opened = pyqtSignal(str)
    frame_changed = pyqtSignal(int)
    auto_mode_changed = pyqtSignal(bool)
    laser_mode_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._is_user_changing_frame = False
        self._is_dragging_progress = False
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Video görüntüsünün gösterileceği alan
        self._create_video_display(layout)
        
        # Video oynatma, durdurma, dosya açma kontrolleri
        self._create_video_controls(layout)
        
        # Mod değiştirme kontrolleri (OpenCV moduna özel)
        self._create_mode_controls(layout)
        
        # Başlangıçta kontrolleri devre dışı bırak
        self.set_controls_enabled(False)
    
    def _create_video_display(self, layout):
        # Video karesinin gösterileceği QLabel
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("QLabel { background-color: black; }") # Arka plan siyah
        
        # İstatistiklerin gösterileceği yarı saydam overlay widget
        self.overlay_widget = QWidget(self.video_label) # video_label'ın üzerinde olacak
        self.overlay_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 127); /* Yarı saydam siyah */
                border-radius: 5px; /* Köşeleri yuvarla */
            }
        """)
        
        overlay_layout = QVBoxLayout(self.overlay_widget)
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("""
            QLabel {
                color: white; /* Beyaz yazı */
                font-weight: bold; /* Kalın yazı */
                font-size: 12px;
            }
        """)
        overlay_layout.addWidget(self.stats_label)
        
        self.overlay_widget.setGeometry(10, 10, 220, 140)
        layout.addWidget(self.video_label)
    
    def _create_video_controls(self, layout):
        controls = QHBoxLayout()
        
        # Play/Pause butonu
        self.play_button = QPushButton()
        self.play_button.setCheckable(True) # Basılı kalabilir (toggle)
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay)) # Başlangıç ikonu: Play
        self.play_button.clicked.connect(self._on_play_clicked)
        
        # Dosya açma butonu
        self.file_button = QPushButton("Video Aç")
        self.file_button.clicked.connect(self._on_file_clicked)
        
        # İlerleme çubuğu ve yüzde göstergesi
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMouseTracking(True) # Fare hareketlerini yakala (tıklama için)
        self.progress_bar.setTextVisible(False) # % değerini gösterme, label kullanacağız
        self.progress_bar.installEventFilter(self) # Tıklama olaylarını yakalamak için event filter
        
        self.progress_label = QLabel("0%")
        self.progress_label.setFixedWidth(50) # Sabit genişlik
        self.progress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter) # Sağa ve ortaya hizala
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        
        # Frame spinner
        self.frame_spinner = QSpinBox()
        self.frame_spinner.setMinimum(0)
        self.frame_spinner.editingFinished.connect(self._on_frame_changed)
        self.frame_spinner.installEventFilter(self) # Enter tuşu olayını yakalamak için
        
        controls.addWidget(self.play_button)
        controls.addWidget(self.file_button)
        controls.addLayout(progress_layout)
        controls.addWidget(self.frame_spinner)
        
        layout.addLayout(controls)
    
    def _create_mode_controls(self, layout):
        mode_controls = QHBoxLayout()
        
        self.auto_mode_check = QCheckBox("Otomatik Mod")
        self.auto_mode_check.setChecked(True)
        self.auto_mode_check.stateChanged.connect(self._on_auto_mode_changed)
        
        self.laser_mode_check = QCheckBox("Lazer Modu")
        self.laser_mode_check.setEnabled(False) # Başlangıçta devre dışı (Otomatik mod aktif)
        self.laser_mode_check.stateChanged.connect(self._on_laser_mode_changed)
        
        mode_controls.addWidget(self.auto_mode_check)
        mode_controls.addWidget(self.laser_mode_check)
        
        layout.addLayout(mode_controls)
    
    def update_frame(self, frame, stats):
        # Frame'i görüntüle
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888) # OpenCV BGR formatında
        # video_label boyutuna sığacak şekilde yeniden boyutlandır (oranı koru)
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.size(), Qt.KeepAspectRatio)
        self.video_label.setPixmap(scaled_pixmap)
        
        # İstatistikleri güncelle (İşleme FPS dahil)
        self.update_stats(stats)
    
    def update_stats(self, stats):
        # İşleme FPS'i tekrar ekle
        native_fps_text = f"{stats.get('native_fps', 0):.1f}" if stats.get('native_fps', 0) > 0 else "N/A"
        stats_text = (
            f"Kaynak FPS: {native_fps_text}\n"
            f"Hedef FPS: {stats.get('target_fps', '?')}\n"
            f"İşleme FPS: {stats.get('processing_fps', 0):.1f}\n"
            f"Preset: {stats.get('preset', '?')}\n"
            f"Mavi Balon: {stats.get('blue_count', '?')}\n"
            f"Kırmızı Balon: {stats.get('red_count', '?')}\n"
            f"Mod: {stats.get('mode', '?')} ({stats.get('control', '?')})\n"
        )
        self.stats_label.setText(stats_text)

    # Olay işleyiciler (Event Handlers)
    def _on_play_clicked(self, checked):
        self.video_toggled.emit(checked)
        # Buton ikonunu Play/Pause durumuna göre değiştir
        self.play_button.setIcon(
            self.style().standardIcon(
                QStyle.SP_MediaPause if checked else QStyle.SP_MediaPlay
            )
        )
    
    def _on_file_clicked(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Video Dosyası Aç", "", 
            "Video Dosyaları (*.mp4 *.avi);;Tüm Dosyalar (*.*)")
        if file_name:
            self.file_opened.emit(file_name)
    
    def _on_auto_mode_changed(self, state):
        self.laser_mode_check.setEnabled(not state)
        self.auto_mode_changed.emit(bool(state))
    
    def _on_laser_mode_changed(self, state):
        if not self.auto_mode_check.isChecked():
            self.laser_mode_changed.emit(bool(state))
    
    def update_video_info(self, total_frames):
        """Video bilgilerini güncelle ve kontrolleri hazırla"""
        self.progress_bar.setMaximum(total_frames)
        self.frame_spinner.setMaximum(total_frames)
        # Video yüklendiğinde, oynatmaya hazır olduğunu belirtmek için
        # Play ikonunu göster ve butonu 'checked=False' yap.
        self.play_button.setChecked(False)
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        # Kontrolleri etkinleştir (bu zaten _on_file_opened içinde yapılıyor ama burada da olabilir)
        # self.set_controls_enabled(total_frames > 0)
    
    def update_progress(self, current_frame, total_frames):
        if total_frames > 0:
            percentage = (current_frame / total_frames) * 100
            self.progress_bar.setValue(current_frame)
            self.progress_label.setText(f"{percentage:.1f}%")
            # Eğer video oynuyorsa ve kullanıcı manuel olarak frame değiştirmiyorsa spinner'ı güncelle
            if self.play_button.isChecked() and not self._is_user_changing_frame:
                self.frame_spinner.setValue(current_frame)
    
    def _calculate_frame_from_pos(self, x_pos):
        """Verilen x pozisyonuna göre frame numarasını hesaplar."""
        width = self.progress_bar.width()
        total_frames = self.progress_bar.maximum()
        if width <= 0 or total_frames <= 0:
            return 0
        
        frame = int((x_pos / width) * total_frames)
        # Değeri 0 ile total_frames arasında sınırla
        frame = max(0, min(frame, total_frames))
        return frame

    def _update_seek_ui(self, frame):
        """Sürükleme sırasında UI elemanlarını (progress bar, label, spinner) günceller."""
        total_frames = self.progress_bar.maximum()
        if total_frames > 0:
            percentage = (frame / total_frames) * 100
            self.progress_bar.setValue(frame)
            self.progress_label.setText(f"{percentage:.1f}%")
            # Spinner'ı sadece kullanıcı manuel olarak değiştirmiyorsa (focus yoksa) güncelle
            if not self.frame_spinner.hasFocus(): 
                self.frame_spinner.setValue(frame)

    def eventFilter(self, obj, event):
        # ProgressBar üzerindeki fare olaylarını yakala (atlamak için)
        if obj == self.progress_bar:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self._is_dragging_progress = True # Sürükleme başladı
                    frame = self._calculate_frame_from_pos(event.pos().x())
                    self._update_seek_ui(frame) # UI'ı anında güncelle
                    return True # Olayı tükettik, başkası işlemesin
            elif event.type() == QEvent.MouseMove:
                if self._is_dragging_progress: # Eğer sürükleniyorsa
                    frame = self._calculate_frame_from_pos(event.pos().x())
                    self._update_seek_ui(frame) # UI'ı güncellemeye devam et
                    return True # Olayı tükettik
            elif event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton and self._is_dragging_progress:
                    self._is_dragging_progress = False # Sürükleme bitti
                    frame = self._calculate_frame_from_pos(event.pos().x())
                    self.frame_changed.emit(frame) # Sadece bırakınca frame değişikliği sinyalini gönder
                    return True # Olayı tükettik

        # Frame Spinner için Enter tuşu kontrolü
        if obj == self.frame_spinner and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self._on_frame_changed() # Bu _is_user_changing_frame'i yönetir ve sinyal gönderir
                return True # Olayı tükettik
        
        # Diğer tüm olaylar için varsayılan işleyiciyi çağır
        return super().eventFilter(obj, event)

    def _on_frame_changed(self):
        # Kullanıcının spinner'ı manuel olarak düzenlediğini yönetmek önemli.
        # _update_seek_ui içindeki hasFocus() kontrolü bunu azaltmaya yardımcı olur.
        if not self._is_dragging_progress: # Sadece sürükleme yoksa manuel değişimi işle
            self._is_user_changing_frame = True # Backend'in spinner'ı güncellemesini engelle
            self.frame_changed.emit(self.frame_spinner.value()) # Yeni frame'i gönder
            self._is_user_changing_frame = False # Kilidi kaldır

    def set_controls_enabled(self, enabled):
        """Video kontrollerini (play, progress, frame) etkinleştirir/devre dışı bırakır."""
        self.play_button.setEnabled(enabled)
        self.progress_bar.setEnabled(enabled)
        self.frame_spinner.setEnabled(enabled)
        # Mod kontrolleri genellikle videodan bağımsızdır (OpenCV modunda)
        # self.auto_mode_check.setEnabled(enabled)
        # self.laser_mode_check.setEnabled(enabled and not self.auto_mode_check.isChecked())

    def set_opencv_controls_visibility(self, visible):
        """Shows or hides controls specific to OpenCV mode."""
        self.auto_mode_check.setVisible(visible)
        self.laser_mode_check.setVisible(visible) 