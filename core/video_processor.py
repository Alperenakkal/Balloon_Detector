import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot, Qt
import time
from ..config import VIDEO_SETTINGS
from .detector import BalloonDetector
import logging
from collections import deque
from balloon_detector.core.pid_controller import PIDController
class VideoProcessor(QObject):
    frame_processed = pyqtSignal(object, dict)  # frame ve stats
    progress_updated = pyqtSignal(int, int)  # mevcut_kare, toplam_kare
    performance_metrics = pyqtSignal(dict)  # Performans metrikleri için yeni sinyal
    finished = pyqtSignal()  # Thread'i durdurmak için
    process_next = pyqtSignal()  # Frame işleme sinyali
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.paused = True
        self.cap = None
        self.hsv_values = None
        self.detector = BalloonDetector()
        self.processing_fps = 0  # İşleme FPS'i
        self.native_fps = 0     # Videonun orijinal FPS'i
        self.current_preset = "Varsayılan"
        self.total_frames = 0
        # --- Kontur Gösterme ---
        self.show_contours_flag = False
        self._contour_window_name = "Konturlar ve Maske (OpenCV)"
        
        # FPS ve Metrik Hesaplama için Değişkenler
        self.fps_window = VIDEO_SETTINGS.get('FPS_WINDOW', 60) # config'den al, yoksa 60
        self.metrics_window = VIDEO_SETTINGS.get('METRICS_WINDOW', 60) # config'den al, yoksa 60
        self.target_fps = VIDEO_SETTINGS.get('TARGET_FPS', 30) # config'den al, yoksa 30
        
        # Zamanlama verilerini tutmak için tek bir deque
        # maxlen, hem FPS hem de metrikler için kullanılacak en büyük pencereyi almalı
        _max_window = max(self.fps_window, self.metrics_window)
        self.frame_timing_history = deque(maxlen=_max_window)
        
        # Frame işleme sinyalini bağla
        self.process_next.connect(self._process_next_frame)
        
        # Logging ayarları
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('VideoProcessor')
        # PID kontrolcü (örnek: yatay eksende hedefe odaklanma)
        self.pid = PIDController(kp=0.1, ki=0.01, kd=0.05)  

    
    def set_video(self, video_path):
        """Video dosyasını ayarla, toplam frame ve kaynak FPS'i hesapla"""
        if self.cap:
            self.cap.release()
            self.native_fps = 0 # Kaynak fps'i sıfırla
        
        self.cap = cv2.VideoCapture(video_path)
        if self.cap.isOpened():
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            # Kaynak FPS'i oku
            try:
                self.native_fps = self.cap.get(cv2.CAP_PROP_FPS)
                if self.native_fps <= 0: # Bazı video formatları 0 dönebilir
                    self.logger.warning("Video kaynak FPS'i okunamadı veya geçersiz.")
                    self.native_fps = 0
            except Exception as e:
                self.logger.error(f"Video kaynak FPS'i okunurken hata: {e}")
                self.native_fps = 0
                
            self.logger.info(f"Video açıldı: {video_path}, toplam frame: {self.total_frames}, kaynak FPS: {self.native_fps:.2f}")
        else:
            self.logger.error(f"Video açılamadı: {video_path}")
            self.total_frames = 0
            self.native_fps = 0
            self.cap = None
    
    @pyqtSlot()
    def start(self):
        """Video işlemeyi başlat veya devam ettir"""
        if not self.cap:
             self.logger.warning("Başlatma denendi ancak video kaynağı ayarlanmamış.")
             return
        # Zaten çalışıyor ama duraklatılmış mı kontrol et
        if self.running and self.paused:
             self.logger.info("Video işleme devam ettiriliyor.")
             self.set_paused(False) # Devam etmek için mevcut mantığı kullan
        elif not self.running:
             self.running = True
             self.paused = False
             # İlk frame'i işle
             self.logger.info("Video işleme başlatıldı")
             QTimer.singleShot(0, self.process_next.emit)
    
    @pyqtSlot()
    def stop_processing(self):
        """Mevcut video işlemeyi durdur (thread'i durdurmaz)"""
        self.running = False
        self.paused = True
        self.logger.info("Video işleme duraklatıldı/durduruldu (thread çalışıyor).")
    
    @pyqtSlot()
    def quit_processor(self):
        """Video işlemciyi tamamen durdur ve thread'den çıkış sinyali gönder."""
        self.running = False
        self.paused = True
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.show_contours_flag:
            cv2.destroyWindow(self._contour_window_name) # Pencereyi kapat
        self.finished.emit() # Thread çıkışı için sinyal gönder
        self.logger.info("Video işlemci tamamen durduruldu.")
    
    @pyqtSlot()
    def _process_next_frame(self):
        """Bir sonraki frame'i işle"""
        try:
            # Önce çalışıyor mu, sonra duraklatılmış mı kontrol et
            if not self.running:
                return

            if self.paused:
                return

            # cap geçerliliği kontrolü eklendi
            if not self.cap or not self.cap.isOpened():
                 self.logger.warning("Frame işlenemedi: Video kaynağı geçerli değil.")
                 self.stop_processing() # cap geçersiz hale gelirse durdur
                 return

            if not self.hsv_values:
                 self.logger.warning("Frame işlenemedi: HSV değerleri ayarlanmamış.")
                 return # HSV değerlerini bekle

            # Frame yakalama süresi
            capture_start = time.perf_counter()
            ret, frame = self.cap.read()
            capture_time = (time.perf_counter() - capture_start) * 1000
            
            if not ret:
                self.logger.info("Video sonuna gelindi, başa dönülüyor")
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    self.logger.error("Frame okunamadı")
                    return
            
            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.progress_updated.emit(current_frame, self.total_frames)
            
            # Tespit süresi
            detection_start = time.perf_counter()
            detections, combined_mask = self.detector.detect(frame, self.hsv_values)
            detection_time = (time.perf_counter() - detection_start) * 1000
            
            # Görselleştirme süresi
            vis_start = time.perf_counter()
            frame_with_detections = self._visualize_detections(frame.copy(), detections)
            vis_time = (time.perf_counter() - vis_start) * 1000
            
            # Toplam işleme süresi
            total_time = capture_time + detection_time + vis_time

            # Zamanlama verilerini deque'ye ekle
            timing_data = {
                'capture': capture_time,
                'detect': detection_time,
                'vis': vis_time,
                'total': total_time
            }
            self.frame_timing_history.append(timing_data)
            
            # İşleme FPS hesapla (deque kullanarak)
            if self.frame_timing_history:
                # Son fps_window kadar frame'in total sürelerini al
                relevant_times = [t['total'] for t in list(self.frame_timing_history)[-self.fps_window:]]
                if relevant_times:
                    avg_process_time = sum(relevant_times) / len(relevant_times)
                    self.processing_fps = 1000.0 / avg_process_time if avg_process_time > 0 else 0
                else:
                    self.processing_fps = 0 # relevant_times boşsa
            else:
                self.processing_fps = 0 # History boşsa
            
            # Metrikleri hazırla ve gönder (deque kullanarak)
            if len(self.frame_timing_history) >= self.metrics_window:
                # Son metrics_window kadar frame al
                metric_data = list(self.frame_timing_history)[-self.metrics_window:]
                metrics = {
                    'avg_frame_time': round(float(np.mean([t['total'] for t in metric_data])), 2),
                    'avg_detection_time': round(float(np.mean([t['detect'] for t in metric_data])), 2),
                    'avg_visualization_time': round(float(np.mean([t['vis'] for t in metric_data])), 2),
                    'avg_capture_time': round(float(np.mean([t['capture'] for t in metric_data])), 2),
                    'avg_fps': round(self.processing_fps, 1) # Zaten hesaplandı
                }
                self.performance_metrics.emit(metrics)
            
            # İstatistikleri hazırla (güncel FPS ile)
            stats = self._prepare_stats(detections)
            # Anlık süreleri de ekleyelim
            stats.update({
                'frame_time': round(total_time, 2), 
                'detection_time': round(detection_time, 2),
                'visualization_time': round(vis_time, 2),
                'capture_time': round(capture_time, 2),
                # processing_fps zaten _prepare_stats içinde
            })
            
            # Frame'i ve istatistikleri gönder
            self.frame_processed.emit(frame_with_detections, stats)

            # --- Konturları Göster (eğer aktifse) ---
            if self.show_contours_flag:
                try:
                    # Maskeyi BGR'ye çevirip renklendirme (opsiyonel)
                    mask_display = cv2.cvtColor(combined_mask, cv2.COLOR_GRAY2BGR)
                    # Konturları maske üzerinde çiz (opsiyonel, zaten tespitte kullanıldı)
                    # cv2.drawContours(mask_display, [d['contour'] for d in detections if 'contour' in d], -1, (0, 255, 0), 1)
                    cv2.imshow(self._contour_window_name, mask_display)
                except Exception as e_vis:
                    self.logger.warning(f"Kontur penceresi gösterilirken hata: {e_vis}")

            # Hedef FPS'e göre bekleme süresi
            target_latency = 1000 / self.target_fps
            remaining_time = max(0, target_latency - total_time)

            # Bir sonraki frame'i planla
            if self.running and not self.paused: # Planlamadan önce tekrar çalışıyor mu kontrol et
                QTimer.singleShot(int(remaining_time), self.process_next.emit)

            # --- OpenCV Pencere Güncellemesi İçin ---
            # Eğer cv2.imshow kullanılıyorsa, olayları işlemek için küçük bir bekleme gerekir.
            # cv2.waitKey(1) # Çok küçük tut, 1ms yeterli olmalı
            # --- PID Uygulaması (sadece ilk tespit için örnek) ---
            if detections:
            # İlk tespit edilen balonun merkezini al (ellipse.center)
                cx = detections[0]['ellipse']['center'][0]
                frame_center_x = frame.shape[1] / 2

            # PID çıktısını hesapla
                output = self.pid.update(target_value=frame_center_x, current_value=cx)

            # Konsola yaz veya logla
                self.logger.info(f"PID Output: {output:.2f} (Target: {frame_center_x}, Current: {cx})")

            # İstersen bu output'u GUI'de bir label'a da iletebilirsin
            # Frame'i ve istatistikleri gönder
            self.frame_processed.emit(frame_with_detections, stats)
        except Exception as e:
            # Daha iyi hata ayıklama için traceback ekle
            self.logger.error(f"Frame işleme hatası: {str(e)}", exc_info=True)
            self.stop_processing() # Hata durumunda işlemeyi durdur, ancak thread'den çıkma
    
    def _process_and_emit_frame(self, frame):
        try:
            if not self.hsv_values: return # HSV olmadan işlem yapma
            
            detection_start = time.perf_counter()
            detections, mask = self.detector.detect(frame, self.hsv_values)
            detection_time = (time.perf_counter() - detection_start) * 1000
            
            vis_start = time.perf_counter()
            frame_with_detections = self._visualize_detections(frame.copy(), detections)
            vis_time = (time.perf_counter() - vis_start) * 1000
            
            total_time = detection_time + vis_time
            
            # Geçici frame için timing history güncellenmez genellikle
            # İstatistikleri hazırla (Sadece anlık değerler)
            stats = self._prepare_stats(detections) # Temel istatistikler
            stats.update({
                'frame_time': round(total_time, 2),
                'detection_time': round(detection_time, 2),
                'visualization_time': round(vis_time, 2),
                'capture_time': 0 # Yakalama yok
            })
            
            self.frame_processed.emit(frame_with_detections, stats)
            
        except Exception as e:
            self.logger.error(f"Tek kare işleme hatası: {str(e)}", exc_info=True)
    
    def _visualize_detections(self, frame, detections):
        for detection in detections:
            color = (0, 0, 255) if detection["color"] == "red" else (255, 0, 0)
            
            # Elipsi çiz
            ellipse = detection["ellipse"]
            cv2.ellipse(frame,
                       (int(ellipse["center"][0]), int(ellipse["center"][1])),
                       (int(ellipse["axes"][0]/2), int(ellipse["axes"][1]/2)),
                       ellipse["angle"], 0, 360, color, 2)
            
            # Bilgi metnini yaz
            x1, y1 = detection["bbox"][:2]
            text = f"{detection['color']} {detection['confidence']:.2f}"
            cv2.putText(frame, text, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
    
    def _prepare_stats(self, detections):
        return {
            "processing_fps": self.processing_fps,
            "target_fps": self.target_fps,
            "native_fps": self.native_fps,
            "blue_count": len([d for d in detections if d["color"] == "blue"]),
            "red_count": len([d for d in detections if d["color"] == "red"]),
            "mode": "Lazer" if self.detector.use_laser_mode else "Normal",
            "control": "Otomatik" if self.detector.auto_mode else "Manuel",
            "preset": self.current_preset
        }
    
    def set_paused(self, paused):
        """Video işlemeyi duraklat/devam ettir"""
        was_paused = self.paused
        self.paused = paused
        if was_paused and not paused: # Resuming
            if not self.running: 
                 self.logger.info("Duraklatılmış durumdan devam ediliyor, işlem başlatılıyor.")
                 self.start()
            elif self.running:
                 self.logger.info("Duraklatılmış durumdan devam ediliyor.")
                 QTimer.singleShot(0, self.process_next.emit)
        elif not was_paused and paused: # Pausing
             self.logger.info("Video işleme duraklatıldı.")
    
    def set_auto_mode(self, enabled):
        self.detector.auto_mode = enabled
        if not enabled:
            self.detector.use_laser_mode = False
    
    def set_laser_mode(self, enabled):
        if not self.detector.auto_mode:
            self.detector.use_laser_mode = enabled

    @pyqtSlot(bool)
    def set_show_contours(self, enabled):
        """Kontur gösterme penceresini açar veya kapatır."""
        self.show_contours_flag = enabled
        if not enabled:
            try:
                cv2.destroyWindow(self._contour_window_name)
            except Exception: pass # Pencere zaten kapalıysa hata vermesin
    
    def set_preset(self, name, values):
        self.current_preset = name
        self.hsv_values = values
        # Eğer video durdurulmuşsa mevcut frame'i tekrar işle
        if self.cap and self.paused:
            current_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            # Bir önceki frame'e git
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, current_pos - 1))
            ret, frame = self.cap.read()
            if ret:
                self._process_and_emit_frame(frame)
    
    def process_frame(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        masks = self._create_masks(hsv, frame.shape)
        detections = self._detect_objects(hsv, masks)
        stats = self._calculate_stats(detections)
        return detections, masks['combined'], stats
    
    def seek_to_frame(self, frame_number):
        """Belirli bir frame'e atla"""
        if not self.cap:
            return
            
        # Geçerli durumu kaydet
        was_paused = self.paused
        # İşlem sırasında pause yapalım ki normal döngü devam etmesin
        self.paused = True 
        
        # Frame'e git
        # TODO: Hata kontrolü eklenebilir (set başarısız olursa?)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        
        if ret:
            self._process_and_emit_frame(frame)
            self.progress_updated.emit(frame_number, self.total_frames)

        else:
            self.logger.warning(f"Frame {frame_number}'a atlanamadı veya okunamadı.")
            # Belki UI'da bir hata gösterilebilir veya progress resetlenebilir
        
        # Önceki duruma geri dön
        self.paused = was_paused
        # Eğer video duraklatılmamışsa ve çalışıyorsa, normal işlemeye devam et
        # Not: was_paused False ise ve self.running True ise devam etmeli
        if not self.paused and self.running:
            # Bir sonraki frame işlemesini tetikle
            self.process_next.emit()
    
    # ... diğer metodlar ... 