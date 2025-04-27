import cv2
import numpy as np
import logging
import pandas as pd
import torch
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt, QThread
from .detector import BalloonDetector # Use the existing detector
from .yolo_processor import YoloProcessor, ULTRALYTICS_AVAILABLE


YOLO_CLASS_MAP_TEST = YoloProcessor.CLASS_MAP if ULTRALYTICS_AVAILABLE else {}
YOLO_DEVICE_TEST = 'cuda' if ULTRALYTICS_AVAILABLE and torch.cuda.is_available() else 'cpu'

class TestProcessorWorker(QObject):
    """Test döngüsünü çalıştırmak için işçi (worker) thread'i."""
    finished = pyqtSignal(list)
    progress = pyqtSignal(int, int, str) # mevcut_kare, toplam_işlenen, durum_mesajı
    error = pyqtSignal(str)

    def __init__(self, video_path, start_frame, end_frame, use_full_video, hsv_values, detector_type, yolo_model_path):
        super().__init__()
        self.video_path = video_path
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.use_full_video = use_full_video
        self.hsv_values = hsv_values
        self.detector_type = detector_type
        self.yolo_model_path = yolo_model_path

        # Dedektörü burada başlatma
        self.cv_detector = None
        self.yolo_model = None
        if "OpenCV" in self.detector_type:
            self.cv_detector = BalloonDetector()

        self.is_cancelled = False
        self.logger = logging.getLogger('TestWorker')

    @pyqtSlot()
    def run_test(self):
        self.logger.info("Test worker started.")
        results = []
        cap = cv2.VideoCapture(self.video_path)

        # Eğer YOLO kullanılacaksa, modeli burada yükle (worker thread içinde)
        if "YOLO" in self.detector_type:
            if ULTRALYTICS_AVAILABLE and self.yolo_model_path:
                try:
                    from ultralytics import YOLO
                    self.logger.info(f"Loading YOLO model for test: {self.yolo_model_path}")
                    self.yolo_model = YOLO(self.yolo_model_path)
                    # Cihaz önemli ölçüde fark yaratıyorsa ısınma için sahte çıkarım gerekebilir
                    # self.yolo_model(np.zeros((64, 64, 3), dtype=np.uint8), device=YOLO_DEVICE_TEST, verbose=False)
                    self.logger.info("Test için YOLO modeli başarıyla yüklendi.")
                except Exception as e:
                    self.logger.error(f"İşçi thread'inde YOLO modeli yüklenemedi: {e}", exc_info=True)
                    self.error.emit(f"Test (YOLO): Model yüklenemedi - {e}")
                    self.yolo_model = None # Yükleme başarısız olursa modelin None olduğundan emin olun
            else:
                 self.logger.error("Test için YOLO seçildi, ancak Ultralytics mevcut değil veya model yolu eksik.")
                 self.error.emit("Test (YOLO): Ultralytics kütüphanesi veya model yolu bulunamadı.")

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.logger.error(f"Test Worker: Failed to open video {self.video_path}")
            self.error.emit(f"Test: Video açılamadı - {self.video_path}")
            return

        total_frames_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        actual_start_frame = 0
        actual_end_frame = total_frames_video
        

        if not self.use_full_video:
            actual_start_frame = max(0, self.start_frame)
            actual_end_frame = min(total_frames_video, self.end_frame)

        if actual_start_frame >= actual_end_frame:
             self.logger.warning("Test İşçisi: Başlangıç karesi >= bitiş karesi. İşlenecek kare yok.")
             self.error.emit("Test: Başlangıç karesi bitiş karesinden büyük veya eşit.")
             cap.release()
             self.finished.emit([]) # Boş sonuçları gönder
             return

        frames_to_process = actual_end_frame - actual_start_frame
        processed_count = 0

        self.logger.info(f"Test processing frames {actual_start_frame} to {actual_end_frame-1} ({frames_to_process} frames)")
        cap.set(cv2.CAP_PROP_POS_FRAMES, actual_start_frame)

        current_frame_num = actual_start_frame
        while current_frame_num < actual_end_frame:
            if self.is_cancelled:
                self.logger.info("Test worker cancelled.")
                break

            ret, frame = cap.read()
            if not ret:
                self.logger.warning(f"Test İşçisi: Kare {current_frame_num} okunamadı. Durduruluyor.")
                break
            # --- Kontrol Ekle ---
            if frame is None:
                self.logger.warning(f"Test İşçisi: {current_frame_num} konumunda geçersiz (None) kare okundu. Atlanıyor.")
                break
            # --- Seçilen dedektörü kullan ---
            try:
                detections = []
                if "OpenCV" in self.detector_type and self.cv_detector:
                    # OpenCV (HSV) Tespiti
                    # Not: Otomatik mod geçişi detector içinde yönetiliyor
                    cv_detections, _ = self.cv_detector.detect(frame, self.hsv_values)
                    # OpenCV formatını standart formata uyarla (zaten uyumlu olmalı)
                    for det in cv_detections:
                         detections.append({
                            'frame': current_frame_num,
                            'detector': 'opencv',
                            'color': det['color'],
                            'confidence': det.get('confidence', -1.0),
                            'bbox_x1': det['bbox'][0],
                            'bbox_y1': det['bbox'][1],
                            'bbox_x2': det['bbox'][2],
                            'bbox_y2': det['bbox'][3],
                            'ellipse_cx': det['ellipse']['center'][0] if det.get('ellipse') else -1,
                            'ellipse_cy': det['ellipse']['center'][1] if det.get('ellipse') else -1,
                            'ellipse_ax1': det['ellipse']['axes'][0] if det.get('ellipse') else -1,
                            'ellipse_ax2': det['ellipse']['axes'][1] if det.get('ellipse') else -1,
                            'ellipse_angle': det['ellipse']['angle'] if det.get('ellipse') else -1,
                        })

                elif "YOLO" in self.detector_type and self.yolo_model:
                    # YOLO Tespiti
                    yolo_results = self.yolo_model(frame, device=YOLO_DEVICE_TEST, verbose=False)
                    boxes = yolo_results[0].boxes
                    for i in range(len(boxes.xyxy)):
                        x1, y1, x2, y2 = map(int, boxes.xyxy[i])
                        conf = float(boxes.conf[i])
                        cls_id = int(boxes.cls[i])
                        color = YOLO_CLASS_MAP_TEST.get(cls_id, f"class_{cls_id}") # Eşleşme veya sınıf ID

                        detections.append({
                            'frame': current_frame_num,
                            'detector': 'yolo',
                            'color': color, # Veya class_id'yi sakla
                            'confidence': conf,
                            'bbox_x1': x1,
                            'bbox_y1': y1,
                            'bbox_x2': x2,
                            'bbox_y2': y2,
                            'ellipse_cx': -1, # YOLO elips vermez
                            'ellipse_cy': -1,
                            'ellipse_ax1': -1,
                            'ellipse_ax2': -1,
                            'ellipse_angle': -1,
                        })

                # Toplanan detection'ları ana listeye ekle
                results.extend(detections)

            except Exception as e:
                self.logger.error(f"Test İşçisinde kare {current_frame_num}'de tespit sırasında hata: {e}", exc_info=True)
                self.error.emit(f"Test Hatası (Kare {current_frame_num}): {e}")
                # Durup durmayacağınıza karar verin
                # break # Hata durumunda durmak için yorumu kaldırın

            processed_count += 1
            if processed_count % 25 == 0 or current_frame_num == actual_end_frame - 1: # İlerlemeyi periyodik olarak güncelle
                percentage = int((processed_count / frames_to_process) * 100)
                status = f"İşleniyor: {processed_count}/{frames_to_process} (%{percentage})"
                self.progress.emit(percentage, processed_count, status)

            current_frame_num += 1
            # İsteğe bağlı: Gerekirse %100 CPU kullanımını önlemek için küçük bir uyku ekleyin
            # time.sleep(0.001)


        cap.release()
        status = "Test Tamamlandı." if not self.is_cancelled else "Test İptal Edildi."
        self.progress.emit(100, processed_count, status) # Son ilerleme güncellemesi
        self.finished.emit(results)
        self.logger.info(f"Test işçisi bitti. Sonuç sayısı: {len(results)}")

    def cancel(self):
        """İşçi döngüsünün durmasını ister."""
        self.logger.info("Test işçisi iptal isteği alındı.")
        self.is_cancelled = True

    # İsteğe bağlı: Thread biterken modeli temizle
    # def __del__(self):
    #     self.logger.info("TestProcessorWorker siliniyor.")

class TestProcessor(QObject):
    """TestProcessorWorker'ı yönetir."""
    test_finished = pyqtSignal(list) # Bittiğinde sonuç listesini yayınlar
    test_progress = pyqtSignal(int, int, str) # yüzde, işlenen_sayısı, durum
    test_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.worker_thread = None
        self.current_worker = None
        self.video_path = None
        self.hsv_values = None
        self.config = {}
        self.results = []
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('TestProcessor')


    def set_config(self, video_path, start_frame, end_frame, use_full_video, hsv_values, detector_type, yolo_model_path):
        self.video_path = video_path
        self.hsv_values = hsv_values # Ana pencereden mevcut HSV'yi al
        self.detector_type = detector_type
        self.yolo_model_path = yolo_model_path
        self.config = {
            'start_frame': start_frame,
            'end_frame': end_frame,
            'use_full_video': use_full_video,
        }
        # Dedektör türünü ve model yolunu logla?
        self.logger.info(f"Test yapılandırması ayarlandı: Video={video_path}, Aralık={start_frame}-{end_frame}, Tam={use_full_video}")

    @pyqtSlot()
    def start_test(self):
        if self.current_worker and self.worker_thread.isRunning():
            self.logger.warning("Test is already running.")
            self.test_error.emit("Test zaten çalışıyor.")
            return

        # HSV kontrolü sadece OpenCV seçiliyse mi gerekli? Belki burada kritik değil.
        if not self.video_path: # Sadece video yolunu kontrol et
              self.logger.error("Test başlatılamıyor: Video yolu veya HSV değerleri ayarlanmadı.")
              self.test_error.emit("Test başlatılamıyor: Video veya HSV değerleri ayarlanmadı.")

        self.logger.info("Test başlatılıyor...")
        self.results = [] # Önceki sonuçları temizle
        self.worker_thread = QThread()
        self.current_worker = TestProcessorWorker(
            video_path=self.video_path,
            start_frame=self.config['start_frame'],
            end_frame=self.config['end_frame'],
            use_full_video=self.config['use_full_video'],
            hsv_values=self.hsv_values,
            detector_type=self.detector_type, 
            yolo_model_path=self.yolo_model_path
        )
        self.current_worker.moveToThread(self.worker_thread)
        # İşçiden gelen sinyalleri işlemcinin sinyallerine bağla
        self.current_worker.finished.connect(self._on_worker_finished)
        self.current_worker.progress.connect(self.test_progress.emit) # İlerlemeyi yeniden yayınla
        self.current_worker.error.connect(self.test_error.emit)     # Hatayı yeniden yayınla

        # Bağlantıyı başlatmadan önce worker thread'in başlatıldığından emin olun
        self.worker_thread.started.connect(self.current_worker.run_test) # Thread başlayınca worker'ın işini başlat
        self.current_worker.finished.connect(self.worker_thread.quit) # Worker bitince thread'i durdur

        # Clean up thread and worker when thread finishes
        self.worker_thread.finished.connect(self.current_worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self._clear_thread_references) # Referansları temizle

        self.logger.info(f"Starting worker thread {id(self.worker_thread)}.")
        self.worker_thread.start() # Thread'i başlat
        # self.test_started.emit() # İsteğe bağlı

    @pyqtSlot()
    def cancel_test(self):
        if self.worker_thread and self.worker_thread.isRunning() and self.current_worker:
            self.logger.info("Attempting to cancel test...")
            self.current_worker.cancel()
            # Worker'ın run_test metodu cancel flag'ini kontrol edip döngüden çıkacak,
            # sonra finished sinyali emit edecek, bu da thread'i durduracak.
            # We might want to disable buttons immediately in the UI though.
        else:
            self.logger.warning("No active test to cancel.")

    @pyqtSlot(list)
    def _on_worker_finished(self, results_list):
        self.logger.info("Test worker finished signal received by processor.")
        self.results = results_list # Sonuçları sakla
        self.test_finished.emit(self.results) # Testin bittiğini ve sonuçları yayınla
        self._clear_thread_references()

    def _clear_thread_references(self):
        self.logger.info("Test thread and worker references cleared.")
        self.current_worker = None
        # Allow starting a new test
        self.worker_thread = None
    

    def export_results(self, output_path):
        """Tespit sonuçlarını bir CSV dosyasına aktarır."""
        if not self.results:
            self.logger.warning("Export failed: No test results available.")
            self.test_error.emit("Dışa aktarma başarısız: Test sonucu yok.")
            return False

        try:
            self.logger.info(f"Exporting {len(self.results)} results to {output_path}")
            df = pd.DataFrame(self.results)
            # 1. İstenen Sütunları Seç ve Sırala
            columns_to_keep = [
                 'frame',
                 'color',
                 'confidence',
                 'detector',
                 'bbox_x1',
                 'bbox_y1',
                 'bbox_x2',
                 'bbox_y2',
            ]
            # Sütunların var olup olmadığını kontrol et (bazı tespitlerde olmayabilir)
            existing_columns = [col for col in columns_to_keep if col in df.columns]
            df_export = df[existing_columns].copy() # Seçili sütunlarla yeni DataFrame

            # 2. Ondalık Hassasiyeti Ayarla (örneğin 'confidence' için)
            if 'confidence' in df_export.columns:
                df_export['confidence'] = pd.to_numeric(df_export['confidence'], errors='coerce').round(3) # Önce sayısal yap
            # Diğer ondalıklı sütunlar için de benzerini yapabilirsiniz (örn. elips)

            # 3. CSV'ye Kaydet (index olmadan)
            df_export.to_csv(output_path, index=False, float_format='%.3f') # float_format ondalık gösterimi de ayarlar
            # --- ---

            self.logger.info("Export successful.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to export results: {e}", exc_info=True)
            self.test_error.emit(f"Sonuçlar dışa aktarılamadı: {e}")
            return False