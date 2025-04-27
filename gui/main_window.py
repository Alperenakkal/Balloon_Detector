from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QDockWidget, QStyle, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSlot
import cv2
from balloon_detector.gui.widgets.video_panel import VideoPanel
from balloon_detector.gui.widgets.preset_panel import PresetPanel
from balloon_detector.gui.widgets.timing_panel import TimingPanel
from balloon_detector.gui.widgets.config_panel import ConfigPanel
from balloon_detector.gui.widgets.system_usage_panel import SystemUsagePanel
from balloon_detector.gui.widgets.mode_panel import ModePanel

from balloon_detector.utils.preset_manager import PresetManager

from balloon_detector.config import DEFAULT_HSV_VALUES, GUI_SETTINGS

from balloon_detector.core.video_processor import VideoProcessor # OpenCV
from balloon_detector.core.yolo_processor import YoloProcessor   # YOLO
from balloon_detector.core.test_processor import TestProcessor # Test Modu

PROCESSOR_TYPE_MAP = { "opencv": 0, "yolo": 1, "test": 2 } # Tip kontrolü için basit eşleştirme

class BalloonDetectorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_panel = None
        self.timing_panel = None
        self.system_usage_panel = None
        self.mode_panel = None
        self._init_ui()
        self.preset_manager = PresetManager()

        # --- İşlemci Yönetimi ---
        self.current_processor_type = None # örn., PROCESSOR_TYPE_MAP["opencv"]
        self.current_processor = None
        self.current_thread = None
        self.current_video_file = None
        self.test_yolo_model_path = None # Test modunda kullanılacak YOLO modeli yolu
        self.loaded_yolo_model_path = None # YOLO modunda başarıyla yüklenen model yolu
        self.test_results_cache = [] # TestProcessor'dan gelen sonuçları önbelleğe al
        # --- -------------------- ---
        
        self._connect_signals()
        self._load_default_values()
        
        # Başlangıç işlemcisini başlat (örn. OpenCV)
        self._start_processor(PROCESSOR_TYPE_MAP["opencv"])
    
    def _init_ui(self):
        self.setWindowTitle("Balon Tespit Programı")
        self.setGeometry(100, 100, 
                        GUI_SETTINGS['WINDOW_WIDTH'], 
                        GUI_SETTINGS['WINDOW_HEIGHT'])
        
        self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)

        # Merkez widget (Video Paneli)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.video_panel = VideoPanel()
        layout.addWidget(self.video_panel)
        
        # Preset paneli (Dock Widget)
        self.preset_panel = PresetPanel()
        preset_dock_widget = QDockWidget("Preset Ayarları", self)
        preset_dock_widget.setObjectName("PresetDock") 
        preset_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        preset_dock_widget.setWidget(self.preset_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, preset_dock_widget)
        
        # Konfigürasyon paneli (Dock Widget)
        self.config_panel = ConfigPanel()
        config_dock_widget = QDockWidget("Konfigürasyon", self)
        config_dock_widget.setObjectName("ConfigDock") 
        config_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        config_dock_widget.setWidget(self.config_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, config_dock_widget)
        
        # Zamanlama paneli (Dock Widget)
        self.timing_panel = TimingPanel()
        timing_dock_widget = QDockWidget("Zamanlama Metrikleri", self)
        timing_dock_widget.setObjectName("TimingDock")
        timing_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        timing_dock_widget.setWidget(self.timing_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, timing_dock_widget)
        
        # Sistem Kullanımı paneli (Dock Widget)
        self.system_usage_panel = SystemUsagePanel()
        system_usage_dock_widget = QDockWidget("Sistem Kullanımı", self)
        system_usage_dock_widget.setObjectName("SystemUsageDock")
        system_usage_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        system_usage_dock_widget.setWidget(self.system_usage_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, system_usage_dock_widget)
        self.mode_panel = ModePanel()
        mode_dock_widget = QDockWidget("İşlem Modu", self)
        mode_dock_widget.setObjectName("ModeDock")
        mode_dock_widget.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        mode_dock_widget.setWidget(self.mode_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, mode_dock_widget)
        self.setMinimumSize(800, 600)

        # Menü çubuğu
        view_menu = self.menuBar().addMenu("Görünüm")
        view_menu.addAction(preset_dock_widget.toggleViewAction())
        view_menu.addAction(config_dock_widget.toggleViewAction())
        view_menu.addAction(timing_dock_widget.toggleViewAction())
        view_menu.addAction(system_usage_dock_widget.toggleViewAction())
        view_menu.addAction(mode_dock_widget.toggleViewAction())
    
    def _connect_signals(self):
        # Video paneli sinyalleri (Tüm modlar için geçerli)
        self.video_panel.video_toggled.connect(self._on_video_toggled)
        self.video_panel.file_opened.connect(self._on_file_opened)
        self.video_panel.frame_changed.connect(self._on_frame_changed)
        
        # --- Sadece OpenCV Modu İçin Geçerli Sinyaller ---
        self.video_panel.auto_mode_changed.connect(self._on_auto_mode_changed)
        self.video_panel.laser_mode_changed.connect(self._on_laser_mode_changed)
        self.mode_panel.show_contours_signal.connect(self._on_show_contours_changed)
        # --- ---------------------------------------- ---
        
        # --- Preset/HSV Sinyalleri (OpenCV ve Test Konfigürasyonu) ---
        self.preset_panel.preset_selected.connect(self._on_preset_selected)
        self.preset_panel.preset_saved.connect(self._on_preset_saved)
        self.preset_panel.hsv_changed.connect(self._on_hsv_changed)
        # --- ------------------------------------------------- ---

        # --- Genel Konfigürasyon Sinyalleri ---
        if self.config_panel:
            self.config_panel.target_fps_changed.connect(self._on_target_fps_changed)
        # --- --------------------------------- ---

        # --- Mod Değişimi ve Mod Paneli Sinyalleri ---
        self.mode_panel.mode_changed.connect(self._on_mode_changed_requested)
        # ModePanel -> Ana Pencere (YOLO Model Yükleme İsteği)
        self.mode_panel.load_yolo_model_signal.connect(self._request_yolo_model_load)
        # ModePanel -> Ana Pencere (Test İşlemleri)
        self.mode_panel.start_test_signal.connect(self._on_start_test)
        self.mode_panel.cancel_test_signal.connect(self._on_cancel_test)
        self.mode_panel.export_results_signal.connect(self._on_export_results)
        self.mode_panel.load_test_yolo_model_signal.connect(self._on_set_test_yolo_model_path)
        # --- ------------------------------------------ ---

    # --- İşlemci Yaşam Döngüsü Yönetimi ---

    def _stop_current_processor(self):
        """Mevcut işlemciyi güvenli bir şekilde durdurur ve thread'inin bitmesini bekler."""
        if self.current_processor:
            print(f"İşlemci durduruluyor: {type(self.current_processor).__name__}")
            if hasattr(self.current_processor, 'quit_processor'):
                # İşlemcinin 'finished' sinyalinin thread'i durdurmasını bekleyebiliriz
                 self.current_processor.quit_processor() # finished sinyali -> thread.quit tetikler
            elif self.current_thread:
                # quit_processor olmayan işlemciler için (örn. TestProcessor)
                self.current_thread.quit()

        if self.current_thread and self.current_thread.isRunning():
            print("Thread'in bitmesi bekleniyor...")
            self.current_thread.wait(5000) # En fazla 5 saniye bekle
            if self.current_thread.isRunning():
                print("Uyarı: Thread düzgün bir şekilde bitmedi. Sonlandırılıyor.")
                self.current_thread.terminate() # Takılırsa zorla sonlandır
            else:
                print("Thread bitti.")

        self.current_processor = None
        self.current_thread = None
        self.current_processor_type = None
        # İşlemci durumuna bağlı UI elemanlarını sıfırla?
        self.video_panel.update_progress(0, 1) # İlerlemeyi sıfırla
        self.timing_panel.update_timings({}) # Zamanlamaları temizle
        # Diğer modlara özel UI sıfırlamaları eklenebilir

    def _start_processor(self, processor_type, model_path=None):
        """Mevcut işlemciyi durdurur ve belirtilen türü başlatır."""
        # Test modu hariç, aynı tür işlemci zaten aktifse yeniden başlatma
        if self.current_processor_type == processor_type and processor_type != PROCESSOR_TYPE_MAP["test"]:
            print(f"İşlemci türü {processor_type} zaten aktif.")
            # Mevcut video varsa kontrolleri tekrar etkinleştir
            if self.current_processor and self.current_video_file:
                 self.video_panel.set_controls_enabled(True)
                 self.video_panel.update_video_info(self.current_processor.total_frames)
            return

        self._stop_current_processor() # Öncekinin durduğundan emin ol

        self.current_processor_type = processor_type
        self.current_thread = QThread()
        processor_instance = None
        hsv_values = self.preset_panel.get_values() # OpenCV/Test için mevcut HSV'yi al

        print(f"İşlemci türü başlatılıyor: {processor_type}")

        if processor_type == PROCESSOR_TYPE_MAP["opencv"]:
            processor_instance = VideoProcessor()
            processor_instance.hsv_values = hsv_values # Başlangıç HSV'sini ayarla
            processor_instance.target_fps = self.config_panel.target_fps_spinbox.value() if self.config_panel else 30
            # OpenCV'ye özgü sinyalleri bağla
            processor_instance.performance_metrics.connect(self.timing_panel.update_timings)
            # Preset/HSV etkileşimlerini etkinleştir
            self.preset_panel.setEnabled(True)
            # OpenCV moduna özel UI elemanlarını etkinleştir/göster
            self.video_panel.set_opencv_controls_visibility(True)
            self.mode_panel.set_opencv_options_visibility(True)
            self.mode_panel.set_yolo_options_visibility(False)
            self.mode_panel.set_test_options_visibility(False)

        elif processor_type == PROCESSOR_TYPE_MAP["yolo"]:
            processor_instance = YoloProcessor()
            processor_instance.target_fps = self.config_panel.target_fps_spinbox.value() if self.config_panel else 30
            # YOLO'ya özgü sinyalleri bağla
            processor_instance.model_loaded.connect(self._on_yolo_model_actually_loaded)
            processor_instance.model_loaded.connect(self.mode_panel.on_yolo_model_loaded) # ModePanel etiketini güncelle
            processor_instance.error_occurred.connect(self._show_error_message)
            # Preset/HSV etkileşimlerini devre dışı bırak
            self.preset_panel.setEnabled(False)
            # YOLO moduna özel UI elemanlarını etkinleştir/göster
            self.video_panel.set_opencv_controls_visibility(False)
            self.mode_panel.set_opencv_options_visibility(False)
            self.mode_panel.set_yolo_options_visibility(True)
            self.mode_panel.set_test_options_visibility(False)
            # Model sinyal aracılığıyla ayrı olarak yüklenmeli

        elif processor_type == PROCESSOR_TYPE_MAP["test"]:
            processor_instance = TestProcessor()
            # Test'e özgü sinyalleri bağla
            processor_instance.test_progress.connect(self.mode_panel.update_test_progress)
            processor_instance.test_finished.connect(self._on_test_finished)
            processor_instance.test_error.connect(self._show_error_message)
            processor_instance.test_error.connect(lambda: self.mode_panel.on_test_completed(False)) # Hata durumunda UI'ı güncelle
            # Preset/HSV etkileşimlerini etkinleştir (test başlamadan önce ayarlanabilir)
            self.preset_panel.setEnabled(True)
            # Test moduna özel UI elemanlarını etkinleştir/göster
            self.video_panel.set_opencv_controls_visibility(False)
            self.video_panel.set_controls_enabled(False) # Video kontrolü test modunda yok
            self.mode_panel.set_opencv_options_visibility(False)
            self.mode_panel.set_yolo_options_visibility(False)
            self.mode_panel.set_test_options_visibility(True)
            # Test işlemi otomatik olarak değil, sinyal ile başlatılır

        else:
            print(f"Hata: Bilinmeyen işlemci türü {processor_type}")
            return

        self.current_processor = processor_instance
        self.current_processor.moveToThread(self.current_thread)

        # Ortak sinyalleri bağla
        if hasattr(self.current_processor, 'frame_processed'):
            self.current_processor.frame_processed.connect(self.video_panel.update_frame)
        if hasattr(self.current_processor, 'progress_updated'):
            self.current_processor.progress_updated.connect(self.video_panel.update_progress)
        # OpenCV ve YOLO işlemcilerinin 'finished' sinyali thread'i durdurur
        if processor_type == PROCESSOR_TYPE_MAP["opencv"] or processor_type == PROCESSOR_TYPE_MAP["yolo"]:
            if hasattr(self.current_processor, 'finished'):
                self.current_processor.finished.connect(self.current_thread.quit)
        # TestProcessor thread'i kendi sinyaliyle değil, _stop_current_processor ile durdurulur.

        # İsteğe bağlı: Thread bittiğinde işlemci örneğini temizle
        # self.current_thread.finished.connect(self.current_processor.deleteLater)
        # self.current_thread.finished.connect(self.current_thread.deleteLater)

        self.current_thread.start()

        # Eğer önceden bir video yüklenmişse, yeni işlemci için ayarla
        if self.current_video_file:
             self._set_video_for_processor(self.current_video_file)

        # Eğer YOLO başlatılıyorsa ve model yolu verildiyse, model yüklemeyi tetikle
        if processor_type == PROCESSOR_TYPE_MAP["yolo"] and model_path:
             self.current_processor.load_model(model_path)

    def _set_video_for_processor(self, filename):
         """Mevcut işlemci için video dosyasını ayarlar."""
         if self.current_processor and hasattr(self.current_processor, 'set_video'):
             self.current_processor.set_video(filename)
             # Video ayarlandıktan sonra UI'ı güncelle
             if self.current_processor.cap and self.current_processor.cap.isOpened():
                  self.video_panel.update_video_info(self.current_processor.total_frames)
                  # Kontrolleri sadece video yüklendikten sonra OpenCV/YOLO modlarında etkinleştir
                  is_realtime_mode = self.current_processor_type in [PROCESSOR_TYPE_MAP["opencv"], PROCESSOR_TYPE_MAP["yolo"]]
                  self.video_panel.set_controls_enabled(is_realtime_mode)
                  if is_realtime_mode:
                      # Görsel geri bildirim için başlangıca git ve ilk kareyi göster
                      self.current_processor.seek_to_frame(0)
                      # Burada otomatik oynatma yapma, kullanıcı play'e bassın
                      self.video_panel.play_button.setChecked(False)
                      self.video_panel.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
             else:
                  self.video_panel.update_video_info(0)
                  self.video_panel.set_controls_enabled(False)
         self.current_video_file = filename # Dosya adını her durumda sakla

    # --- Sinyal İşleyiciler (Signal Handlers) ---
    def _on_file_opened(self, filename):
        try:
            print(f"Dosya açma isteği: {filename}")
            self._set_video_for_processor(filename)
        except Exception as e:
            print(f"Video açma hatası: {str(e)}")
            self._show_error_message(f"Video açma hatası: {str(e)}")
    
    def _on_video_toggled(self, playing):
        """Video oynatma/durdurma durumunu değiştir (Sadece OpenCV/YOLO)"""
        # Test modunda veya işlemci yoksa oynatmayı engelle
        if not self.current_processor or self.current_processor_type == PROCESSOR_TYPE_MAP["test"]:
             self.video_panel.play_button.setChecked(False)
             self.video_panel.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
             return
        if playing:
            if hasattr(self.current_processor, 'start'):
                self.current_processor.start() # start() devam etmeyi de yönetmeli
        else:
            if hasattr(self.current_processor, 'stop_processing'):
                self.current_processor.stop_processing() # Döngüyü duraklatır
    
    def _on_frame_changed(self, frame):
        # Sadece OpenCV ve YOLO modlarında kare atlamaya izin ver
        if self.current_processor and self.current_processor_type in [PROCESSOR_TYPE_MAP["opencv"], PROCESSOR_TYPE_MAP["yolo"]]:
            if hasattr(self.current_processor, 'seek_to_frame'):
                self.current_processor.seek_to_frame(frame)
    
    def _on_auto_mode_changed(self, enabled):
        # Sadece OpenCV İşlemcisi için geçerli
        if self.current_processor_type == PROCESSOR_TYPE_MAP["opencv"]:
            if hasattr(self.current_processor, 'set_auto_mode'):
                self.current_processor.set_auto_mode(enabled)
    
    def _on_laser_mode_changed(self, enabled):
        # Sadece OpenCV İşlemcisi için geçerli
        if self.current_processor_type == PROCESSOR_TYPE_MAP["opencv"]:
            if hasattr(self.current_processor, 'set_laser_mode'):
                self.current_processor.set_laser_mode(enabled)
    
    def _on_preset_selected(self, name):
        preset_values = self.preset_manager.load_preset(name)
        if preset_values:
            self.preset_panel.set_values(preset_values)
            # HSV değerlerini ilgili işlemciye uygula
            self._apply_hsv_to_processor(name, preset_values)
    
    def _on_preset_saved(self, name, values):
        self.preset_manager.save_preset(name, values)
        self.preset_panel.update_presets(self.preset_manager.get_preset_names())
    
    def _on_hsv_changed(self, values):
        # HSV değerlerini ilgili işlemciye uygula
        self._apply_hsv_to_processor(self.preset_panel.preset_combo.currentText(), values)

    def _apply_hsv_to_processor(self, name, values):
        """HSV değerlerini mevcut ilgili işlemciye (OpenCV veya Test) uygular."""
        # Eğer aktifse OpenCV işlemcisine uygula
        if self.current_processor_type == PROCESSOR_TYPE_MAP["opencv"] and self.current_processor:
            if hasattr(self.current_processor, 'set_preset'): # set_preset hsv_values'i de ayarlar
                self.current_processor.set_preset(name, values)
        # Test işlemcisi için sakla (test başladığında okunacak)
        elif self.current_processor_type == PROCESSOR_TYPE_MAP["test"] and self.current_processor:
             self.current_processor.hsv_values = values # TestProcessor config'i günceller
             print("Sonraki Test çalıştırması için HSV değerleri güncellendi.")

    def _on_target_fps_changed(self, new_fps):
        # Eğer aktifse OpenCV veya YOLO işlemcilerine uygula
        if self.current_processor and hasattr(self.current_processor, 'target_fps'):
            self.current_processor.target_fps = new_fps
            print(f"Hedef FPS güncellendi: {new_fps}")

    def _on_mode_changed_requested(self, mode_name):
        """ModePanel'den gelen mod seçimi değişikliğini yönetir."""
        print(f"Ana Pencere: Mod değişimi istendi - {mode_name}")
        if "OpenCV" in mode_name:
            self._start_processor(PROCESSOR_TYPE_MAP["opencv"])
        elif "YOLO" in mode_name:
            # İşlemci kurulumunu başlat, ancak model yükleme buton tıklamasıyla olur
            self._start_processor(PROCESSOR_TYPE_MAP["yolo"])
        elif "Test" in mode_name:
            # İşlemci kurulumunu başlat, test çalıştırma buton tıklamasıyla olur
            self._start_processor(PROCESSOR_TYPE_MAP["test"])

    @pyqtSlot(str)
    def _request_yolo_model_load(self, model_path):
        """ModePanel tarafından bir YOLO modelini yüklemek için tetiklenir."""
        if self.current_processor_type == PROCESSOR_TYPE_MAP["yolo"] and self.current_processor:
             if hasattr(self.current_processor, 'load_model'):
                print(f"YOLO işlemcisinden model yüklemesi isteniyor: {model_path}")
                self.current_processor.load_model(model_path)
        else:
            self._show_error_message("YOLO Modu aktif değil.")

    @pyqtSlot(bool, str)
    def _on_yolo_model_actually_loaded(self, success, message):
        """YoloProcessor modeli yüklemeyi bitirdiğinde çağrılır."""
        if success:
             self.loaded_yolo_model_path = self.current_processor.model_path # Onaylanan yolu sakla
             # Model yüklendiğinde ve video varsa, kontrolleri etkinleştir ve başlangıca git
             if self.current_video_file:
                 self._set_video_for_processor(self.current_video_file)
        else:
            self.loaded_yolo_model_path = None # Başarısız olursa yolu temizle
            self.video_panel.set_controls_enabled(False) # Kontrolleri devre dışı bırak
            # Hata mesajı zaten mode_panel sinyal bağlantısıyla gösterildi

    @pyqtSlot(int, int, bool, str)
    def _on_start_test(self, start_frame, end_frame, use_full_video, detector_type):
        """ModePanel tarafından testi başlatmak için tetiklenir."""
        if self.current_processor_type == PROCESSOR_TYPE_MAP["test"] and self.current_processor:
            if not self.current_video_file:
                 self._show_error_message("Test başlatılamıyor: Önce bir video açın.")
                 self.mode_panel.on_test_completed(False) # UI durumunu sıfırla
                 return
            hsv_values = self.preset_panel.get_values() # Mevcut HSV'yi al
            # YOLO seçiliyse ve bir model yüklü olup olmadığını kontrol et
            yolo_model_path_for_test = None
            if "YOLO" in detector_type:
                if self.test_yolo_model_path: # ModePanel'den ayarlanan yolu kullan
                    yolo_model_path_for_test = self.test_yolo_model_path
                else:
                    self._show_error_message("Test (YOLO) başlatılamıyor: Önce test için bir YOLO modeli seçin.")
                    self.mode_panel.on_test_completed(False) # UI durumunu sıfırla
                    return

            # Test işlemcisini yapılandır
            self.current_processor.set_config(
                self.current_video_file, start_frame, end_frame, use_full_video, hsv_values,
               detector_type, yolo_model_path_for_test # Yeni bilgiyi geçir
            )
            self.test_results_cache = [] # Önceki test sonuçlarını temizle
            self.current_processor.start_test() # Bu, işçiyi kendi thread'inde çalıştırır
        else:
            self._show_error_message("Testi başlatmak için Test Modunda olmalısınız.")
            self.mode_panel.on_test_completed(False) # UI durumunu sıfırla

    @pyqtSlot()
    def _on_cancel_test(self):
        """ModePanel tarafından çalışan testi iptal etmek için tetiklenir."""
        if self.current_processor_type == PROCESSOR_TYPE_MAP["test"] and self.current_processor:
             if hasattr(self.current_processor, 'cancel_test'):
                 self.current_processor.cancel_test()
        else:
            # Buton doğru şekilde devre dışı bırakılırsa bu olmamalı
            print("Uyarı: Test iptali çağrıldı ancak test modunda değil.")

    @pyqtSlot(bool)
    def _on_show_contours_changed(self, enabled):
        """OpenCV işlemcisine konturları göstermesini/gizlemesini söyler."""
        if self.current_processor_type == PROCESSOR_TYPE_MAP["opencv"] and self.current_processor:
            if hasattr(self.current_processor, 'set_show_contours'):
                self.current_processor.set_show_contours(enabled)
                print(f"Kontur gösterimi {'etkinleştirildi' if enabled else 'devre dışı bırakıldı'}.")

    @pyqtSlot(str)
    def _on_set_test_yolo_model_path(self, path):
        """ModePanel'den gelen test YOLO modeli yolunu saklar ve label'ı günceller."""
        self.test_yolo_model_path = path
        print(f"Test için YOLO modeli ayarlandı: {path}")
        # ModePanel'deki etiketi güncellemek için ayrı bir sinyal/slot gerekebilir veya ModePanel kendi içinde yapabilir
        if self.mode_panel:
            self.mode_panel.update_test_yolo_label(path)

    @pyqtSlot(list)
    def _on_test_finished(self, results_list):
        """TestProcessor işçisi bittiğinde çağrılır."""
        print(f"Test tamamlandı, {len(results_list)} sonuç alındı.")
        self.test_results_cache = results_list # Sonuçları sonraki export için sakla
        # ModePanel UI'ını güncelle (export'u etkinleştir, ilerlemeyi sıfırla)
        self.mode_panel.on_test_completed(True if results_list else False) # Sonuç varsa export'u etkinleştir
        # Burada bir özet mesaj kutusu gösterebilirsiniz
        QMessageBox.information(self, "Test Tamamlandı", f"Test tamamlandı. {len(results_list)} tespit bulundu.")

    @pyqtSlot(str)
    def _on_export_results(self, output_path):
        """ModePanel tarafından test sonuçlarını dışa aktarmak için tetiklenir."""
        if self.current_processor_type == PROCESSOR_TYPE_MAP["test"] and self.current_processor:
            # Önbelleğe alınmış sonuçları kullan
            if not self.test_results_cache:
                self._show_error_message("Dışa aktarılacak test sonucu bulunamadı.")
                return
            # Export işlemini TestProcessor'a devret (cache ile)
            success = self.current_processor.export_results(output_path)
            if success:
                 QMessageBox.information(self, "Dışa Aktarma Başarılı", f"Sonuçlar başarıyla '{output_path}' dosyasına kaydedildi.")
            # Hata mesajı zaten işlemci sinyali tarafından işleniyor
        else:
             self._show_error_message("Sonuçları dışa aktarmak için Test Modunda olmalısınız.")

    @pyqtSlot(str)
    def _show_error_message(self, message):
        """Bir hata mesajı kutusu gösterir."""
        print(f"Hata: {message}") # Hatayı ayrıca logla
        QMessageBox.warning(self, "Hata", message)
    
    def _load_default_values(self):
        # Varsayılan HSV değerlerini yükle (sadece PresetPanel için)
        self.preset_panel.set_values(DEFAULT_HSV_VALUES)
        # HSV değerleri işlemci başlatıldığında veya değiştirildiğinde uygulanır
        
        # Presetleri yükle
        preset_names = self.preset_manager.get_preset_names()
        self.preset_panel.update_presets(preset_names)
        
        # Başlangıç Target FPS değerini ayarla (varsayılan işlemci için)
        if self.config_panel and self.current_processor and hasattr(self.current_processor, 'target_fps'):
            initial_fps = self.config_panel.target_fps_spinbox.value()
            self.current_processor.target_fps = initial_fps
    
    def closeEvent(self, event):
        """Uygulama kapatılırken thread'i temizle ve pencereleri kapat"""
        print("Kapatma olayı tetiklendi. İşlemci durduruluyor...")
        self._stop_current_processor() # Yardımcı fonksiyonu kullan
        cv2.destroyAllWindows() # Tüm OpenCV pencerelerini kapat
        super().closeEvent(event)