import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, pyqtSlot, Qt
import time
from ..config import VIDEO_SETTINGS
import logging
from collections import deque
import torch

# --- Ultralytics gerektirir ---
try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False
# --- ---

class YoloProcessor(QObject):
    frame_processed = pyqtSignal(object, dict)  # frame ve istatistikler
    progress_updated = pyqtSignal(int, int)  # mevcut_kare, toplam_kare
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    model_loaded = pyqtSignal(bool, str) # Başarı (bool), mesaj/hata (str)
    process_next = pyqtSignal()

    # --- Sınıf Eşleştirme ---
    # Bunu EĞİTİLMİŞ YOLO modelinizin sınıf indekslerine göre ayarlayın
    CLASS_MAP = {
        0: "balloon",  # Örnek: sınıf 0 balon
        1: "red",   # Örnek: sınıf 1 kırmızı balon
        # Bu sadece bir örnektir. Modelinizin sınıflarına göre ayarlayın.
        # Gerekirse diğer sınıfları ekleyin veya beklenmeyen sınıfları ele alın
    }
    # --- ----------- ---

    def __init__(self):
        super().__init__()
        if not ULTRALYTICS_AVAILABLE:
            self.logger.error("Ultralytics kütüphanesi bulunamadı. YOLO modu devre dışı.")
            # İsteğe bağlı olarak hemen bir hata sinyali gönderin
            # self.error_occurred.emit("Ultralytics kütüphanesi bulunamadı.")
            return

        self.running = False
        self.paused = True
        self.cap = None
        self.model = None
        self.model_path = None
        self.total_frames = 0
        self.native_fps = 0
        self.processing_fps = 0
        self.target_fps = VIDEO_SETTINGS.get('TARGET_FPS', 30)
        self.frame_timing_history = deque(maxlen=60) # FPS hesaplaması için

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('YoloProcessor')

        # Cihazı belirle
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.logger.info(f"YOLO cihazı kullanıyor: {self.device}")

        self.process_next.connect(self._process_next_frame)

    @pyqtSlot(str)
    def load_model(self, model_path):
        if not ULTRALYTICS_AVAILABLE:
            self.model_loaded.emit(False, "Ultralytics kütüphanesi kurulu değil.")
            return
        try:
            self.logger.info(f"YOLO modeli yükleniyor: {model_path}")
            self.model = YOLO(model_path)
            # Modelin cihaza yüklendiğinden emin olmak için sahte bir çıkarım yapın
            # Küçük bir sahte görüntü kullanın
            dummy_img = np.zeros((64, 64, 3), dtype=np.uint8)
            self.model(dummy_img, device=self.device, verbose=False)
            self.model_path = model_path
            self.logger.info(f"YOLO modeli başarıyla {self.device} cihazına yüklendi.")
            self.model_loaded.emit(True, f"Model yüklendi: {model_path}")
        except Exception as e:
            error_msg = f"YOLO modeli yüklenemedi: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.model = None
            self.model_path = None
            self.model_loaded.emit(False, error_msg)
            self.error_occurred.emit(error_msg)

    def set_video(self, video_path):
        if self.cap:
            self.cap.release()
            self.native_fps = 0
        self.cap = cv2.VideoCapture(video_path)
        if self.cap.isOpened():
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.native_fps = self.cap.get(cv2.CAP_PROP_FPS) if self.cap.get(cv2.CAP_PROP_FPS) > 0 else 0
            self.logger.info(f"Video set for YOLO: {video_path}, Frames: {self.total_frames}, FPS: {self.native_fps:.2f}")
        else:
            self.logger.error(f"Failed to open video: {video_path}")
            self.total_frames = 0
            self.native_fps = 0
            self.cap = None
            self.error_occurred.emit(f"Video açılamadı: {video_path}")


    @pyqtSlot()
    def start(self):
        if not self.cap or not self.model:
            self.logger.warning("Cannot start YOLO processing: Video or model not set.")
            self.error_occurred.emit("Başlatılamıyor: Video veya YOLO modeli ayarlanmadı.")
            return
        if self.running and self.paused:
            self.paused = False
            self.logger.info("YOLO processing resumed.")
            QTimer.singleShot(0, self.process_next.emit)
        elif not self.running:
            self.running = True
            self.paused = False
            self.logger.info("YOLO processing started.")
            QTimer.singleShot(0, self.process_next.emit)

    @pyqtSlot()
    def stop_processing(self):
        self.paused = True
        # Not: Burada self.running = False ayarlamıyoruz, sadece duraklatıyoruz
        self.logger.info("YOLO işleme duraklatıldı.")

    @pyqtSlot()
    def quit_processor(self):
        self.running = False
        self.paused = True
        if self.cap:
            self.cap.release()
            self.cap = None
        # Modeli açıkça silmeye gerek yok? GC halletmeli.
        self.model = None
        self.finished.emit()
        self.logger.info("YOLO işlemcisi durduruldu.")

    @pyqtSlot()
    def _process_next_frame(self):
        if not self.running or self.paused or not self.cap or not self.model:
            return

        frame_start_time = time.perf_counter()
        ret, frame = self.cap.read()

        if not ret:
            self.logger.info("YOLO: End of video reached, looping.")
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                self.logger.error("YOLO: Failed to read frame after loop.")
                self.stop_processing()
                self.error_occurred.emit("Video karesi okunamadı.")
                return

        current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.progress_updated.emit(current_frame, self.total_frames)

        try:
            # YOLO çıkarımı yap
            results = self.model(frame, device=self.device, verbose=False) # Ayrıntılı loglamayı devre dışı bırak

            # Sonuçları işle
            detections = self._parse_yolo_results(results[0]) # results bir listedir

            # Görselleştir
            frame_with_detections = self._visualize_detections(frame.copy(), detections)

            # Timing & FPS
            frame_end_time = time.perf_counter()
            total_time = (frame_end_time - frame_start_time) * 1000 # ms
            self.frame_timing_history.append(total_time)
            if len(self.frame_timing_history) > 1:
                 avg_time = sum(self.frame_timing_history) / len(self.frame_timing_history)
                 self.processing_fps = 1000.0 / avg_time if avg_time > 0 else 0
            else:
                 self.processing_fps = 1000.0 / total_time if total_time > 0 else 0

            # Prepare stats
            stats = self._prepare_stats(detections)
            stats['frame_time'] = round(total_time, 2)

            # Sinyali gönder
            self.frame_processed.emit(frame_with_detections, stats)

            # Sonrakini planla
            target_latency = 1000 / self.target_fps
            elapsed_time = total_time
            wait_time = max(0, int(target_latency - elapsed_time))
            if self.running and not self.paused:
                QTimer.singleShot(wait_time, self.process_next.emit)

        except Exception as e:
            self.logger.error(f"Error during YOLO inference: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"YOLO işleme hatası: {str(e)}")
            self.stop_processing()


    def _parse_yolo_results(self, result):
        """Converts YOLO detection results to the application's format."""
        detections = []
        boxes = result.boxes  # Access the Boxes object

        for i in range(len(boxes.xyxy)):
            x1, y1, x2, y2 = map(int, boxes.xyxy[i])
            conf = float(boxes.conf[i])
            cls_id = int(boxes.cls[i])

            color = self.CLASS_MAP.get(cls_id, "unknown") # Eşleştirmeyi kullan

            # Temel filtreleme (isteğe bağlı, model iyi eğitilmiş olmalı)
            if conf < 0.25: # Örnek güven eşiği
                continue # Düşük güvenli tespitleri atla

            # Not: YOLO doğrudan elips sağlamaz. Sınırlayıcı kutu kullanıyoruz.
            # Görselleştirme tutarlılığı için, elips kısmını atlayabiliriz
            # veya başka bir yerde gerekirse bbox'tan tahmin edebiliriz.
            detections.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": conf,
                "color": color,
                "is_laser_mode": False, # YOLO'da bu kavram yok
                "color_ratio": conf, # Güveni bir vekil skor olarak kullan
                "ellipse": None # Veya gerekirse tahmin et
            })
        return detections

    def _visualize_detections(self, frame, detections):
        """Draws bounding boxes and labels on the frame."""
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            color_bgr = (0, 0, 255) if detection["color"] == "red" else (255, 0, 0) if detection["color"] == "blue" else (0, 255, 0) # Bilinmeyen için yeşil
            conf = detection["confidence"]

            cv2.rectangle(frame, (x1, y1), (x2, y2), color_bgr, 2)
            label = f"{detection['color']} {conf:.2f}"
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_bgr, 2)
        return frame

    def _prepare_stats(self, detections):
        return {
            "processing_fps": self.processing_fps,
            "target_fps": self.target_fps,
            "native_fps": self.native_fps,
            "blue_count": len([d for d in detections if d["color"] == "blue"]),
            "red_count": len([d for d in detections if d["color"] == "red"]),
            "mode": "YOLO",
            "control": f"Model: {self.model_path.split('/')[-1].split('\\')[-1]}" if self.model_path else "N/A", # Model adını göster
            "preset": "N/A" # Presetler YOLO modunda kullanılmaz
        }

    def seek_to_frame(self, frame_number):
        """Seek to a specific frame and process it."""
        if not self.cap or not self.model:
            return

        was_paused = self.paused
        self.paused = True # Pause processing during seek

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()

        if ret:
            try:
                results = self.model(frame, device=self.device, verbose=False)
                detections = self._parse_yolo_results(results[0])
                frame_with_detections = self._visualize_detections(frame.copy(), detections)
                stats = self._prepare_stats(detections)
                 # Add dummy timing for single frame processing
                stats['frame_time'] = -1.0
                self.frame_processed.emit(frame_with_detections, stats)
                self.progress_updated.emit(frame_number, self.total_frames)
            except Exception as e:
                 self.logger.error(f"Error processing single YOLO frame {frame_number}: {e}", exc_info=True)
                 self.error_occurred.emit(f"Tek kare işleme hatası (YOLO): {e}")
        else:
            self.logger.warning(f"YOLO: Could not seek to or read frame {frame_number}")

        self.paused = was_paused
        if not self.paused and self.running:
            QTimer.singleShot(0, self.process_next.emit) # Resume processing loop