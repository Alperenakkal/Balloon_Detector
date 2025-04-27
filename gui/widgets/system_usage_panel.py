import psutil
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QSizePolicy
from PyQt5.QtCore import QTimer, Qt

class SystemUsagePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._process = psutil.Process(os.getpid()) # Mevcut işlemi al
        self._init_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_usage)
        self._timer.start(1000) # Her 1 saniyede bir güncelle

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5) # Azaltılmış kenar boşlukları

        # Sistem Kullanımı Grubu
        system_group = QGroupBox("Genel Sistem Kullanımı")
        system_layout = QVBoxLayout(system_group)

        self.cpu_label = QLabel("CPU: - %")
        system_layout.addWidget(self.cpu_label)

        self.memory_label = QLabel("Bellek: - %")
        system_layout.addWidget(self.memory_label)

        # İsteğe bağlı: Kütüphane mevcutsa GPU kullanım etiketi buraya eklenebilir
        # self.gpu_label = QLabel("GPU: - %")
        # system_layout.addWidget(self.gpu_label)

        layout.addWidget(system_group)

        # Uygulama Kullanımı Grubu
        app_group = QGroupBox("Uygulama Kullanımı")
        app_layout = QVBoxLayout(app_group)

        self.app_cpu_label = QLabel("Uygulama CPU: - %")
        app_layout.addWidget(self.app_cpu_label)

        self.app_memory_label = QLabel("Uygulama Bellek: - MB")
        app_layout.addWidget(self.app_memory_label)

        layout.addWidget(app_group)

        # Kaynak Uyarıları (İsteğe Bağlı)
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red;")
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)

        layout.addStretch(1) # Widget'ları yukarı iter

        # Boyut politikasını dikey genişlemeyi tercih edecek şekilde ayarla
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)


    def _update_usage(self):
        try:
            # Sistem Kullanımı
            cpu_percent = psutil.cpu_percent(interval=None) # Bloklamayan çağrı
            mem_info = psutil.virtual_memory()
            mem_percent = mem_info.percent

            self.cpu_label.setText(f"CPU: {cpu_percent:.1f} % ({psutil.cpu_count()} Çekirdek)")
            self.memory_label.setText(f"Bellek: {mem_percent:.1f} % ({mem_info.used / (1024**3):.2f}/{mem_info.total / (1024**3):.2f} GB)")

            # Uygulama Kullanımı
            app_cpu_percent = self._process.cpu_percent(interval=None) / psutil.cpu_count() # Çekirdek sayısına göre normalleştir
            app_mem_info = self._process.memory_info()
            app_mem_mb = app_mem_info.rss / (1024**2) # MB cinsinden Resident Set Size (Kullanılan Fiziksel Bellek)

            self.app_cpu_label.setText(f"Uygulama CPU: {app_cpu_percent:.1f} %")
            self.app_memory_label.setText(f"Uygulama Bellek: {app_mem_mb:.2f} MB")

            # Uyarılar
            warnings = []
            if cpu_percent > 90:
                warnings.append("Yüksek CPU kullanımı!")
            if mem_percent > 90:
                warnings.append("Yüksek Bellek kullanımı!")
            if app_cpu_percent > 50: # Uygulama CPU için örnek eşik değeri
                 warnings.append("Uygulama CPU kullanımı yüksek!")

            self.warning_label.setText("\n".join(warnings))

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.cpu_label.setText("CPU: Hata")
            self.memory_label.setText("Bellek: Hata")
            self.app_cpu_label.setText("Uygulama CPU: Hata")
            self.app_memory_label.setText("Uygulama Bellek: Hata")
            self.warning_label.setText(f"Kaynak bilgisi alınamadı: {e}")
            self._timer.stop() # Hata durumunda zamanlayıcıyı durdur

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event) 