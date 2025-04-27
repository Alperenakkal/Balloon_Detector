from PyQt5.QtWidgets import QGroupBox, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import QSize, QParallelAnimationGroup, pyqtSlot, Qt, QEvent

class QCollapsibleBox(QGroupBox):
    """Açılıp kapanabilen bir grup kutusu widget'ı."""
    def __init__(self, title="", parent=None, collapsed=False):
        super().__init__(title, parent)
        
        self.toggle_button = QPushButton(self)
        self.toggle_button.setStyleSheet("QPushButton { border: none; }") # Buton kenarlığını kaldır
        self.toggle_button.setIconSize(QSize(12, 12))
        self.toggle_button.setFixedSize(20, 20) # İkon için sabit boyut
        self.toggle_button.setCheckable(True)
        
        # Ok ikonları
        # self.toggle_button.setText("▼")
        
        # İçerik widget'ı
        self.content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content.setLayout(self.content_layout)
        
        # Ana layout
        self.setTitle("") # QGroupBox'un varsayılan başlığını gizle, kendi etiketimizi kullanacağız
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5) # Kenar boşlukları
        layout.setSpacing(5) # Elemanlar arası boşluk
        title_layout = QHBoxLayout() # Başlık ve buton için yatay layout
        self.title_label = QLabel(title)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch() # Butonu sağa it
        title_layout.addWidget(self.toggle_button)
        layout.addLayout(title_layout)
        layout.addWidget(self.content)
        
        # Animasyon için hazırlık
        # self.animation = QParallelAnimationGroup()
        self.content_height = 0
        # self.is_collapsed = False
        
        # Sinyal bağlantısı
        self.toggle_button.clicked.connect(self._on_button_clicked)

        # Başlangıç durumunu ayarla
        self.setChecked(not collapsed)
    
    @pyqtSlot(bool)
    def setChecked(self, checked):
        """Kutunun açık (checked=True) veya kapalı (checked=False) durumunu ayarlar."""
        self.toggle_button.setChecked(checked)
        
        is_collapsed = not checked
        self.toggle_button.setText("►" if is_collapsed else "▼") # Ok ikonunu değiştir
        
        # İçerik yüksekliğini hesapla (ilk seferde veya gerekirse)
        if not self.content_height:
            # content.sizeHint() widget görünür olmadan doğru sonuç vermeyebilir.
            # Alternatif: layout'un sizeHint'i?
            self.content_height = self.content.sizeHint().height() if self.content.sizeHint().height() > 0 else 1000 # Güvenli bir varsayılan

        if is_collapsed:
            self.content.setMaximumHeight(0) # İçeriği gizle
        else:
            self.content.setMaximumHeight(16777215) # İçeriği göster (maksimum yükseklik)

    @pyqtSlot()
    def _on_button_clicked(self):
        """Butona tıklandığında durumu günceller."""
        self.setChecked(self.toggle_button.isChecked())

    def addWidget(self, widget):
        """İçerik alanına bir widget ekler."""
        self.content_layout.addWidget(widget)
        # İçerik yüksekliğini burada tekrar hesaplamak daha güvenilir olabilir
        # ancak layout tam oturmadan sizeHint doğru olmayabilir.

    def mousePressEvent(self, event):
        """Başlık alanına tıklandığında kutuyu aç/kapat."""
        # Sadece başlık çubuğuna (içerik alanının yukarısına) tıklandığında çalışır
        if event.button() == Qt.LeftButton and event.pos().y() < self.content.y():
            self.toggle_button.click() # Ok butonuna tıklanmış gibi yap
            event.accept() # Olayı işledik olarak işaretle
        else:
            # Diğer durumlar için (örn. sağ tık, içerik alanına tıklama) varsayılan davranışı uygula
            super().mousePressEvent(event) 