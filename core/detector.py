import cv2
import numpy as np
from ..config import DETECTION_SETTINGS

class BalloonDetector:
    def __init__(self):
        self.last_blue_counts = []
        self.laser_frame_count = 0
        self.use_laser_mode = False
        self.auto_mode = True
    
    def detect(self, frame, hsv_values):
        """Ana tespit metodu"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        masks = self._create_masks(hsv, frame.shape, hsv_values)
        detections = self._detect_objects(hsv, masks)
        
        if self.auto_mode:
            self._check_mode_switch(detections)
        
        return detections, masks['combined']
    
    def _create_masks(self, hsv, shape, hsv_values):
        """HSV değerlerine göre maskeleri oluşturur"""
        masks = {
            'red': np.zeros(shape[:2], dtype=np.uint8),
            'blue': np.zeros(shape[:2], dtype=np.uint8)
        }
        
        # Mavi maske
        blue_key = 'laser_blue' if self.use_laser_mode else 'normal_blue'
        blue_values = hsv_values[blue_key]
        masks['blue'] = self._create_single_mask(hsv, blue_values)
        
        # Kırmızı maskeler
        for idx in ['1', '2']:
            red_key = f"laser_red{idx}" if self.use_laser_mode else f"normal_red{idx}"
            red_values = hsv_values[red_key]
            red_mask = self._create_single_mask(hsv, red_values)
            masks['red'] = cv2.bitwise_or(masks['red'], red_mask)
        
        masks['combined'] = cv2.bitwise_or(masks['red'], masks['blue'])
        return masks
    
    def _create_single_mask(self, hsv, values):
        """Tek bir renk için maske oluşturur"""
        lower = np.array([values['H Min'], values['S Min'], values['V Min']])
        upper = np.array([values['H Max'], values['S Max'], values['V Max']])
        return cv2.inRange(hsv, lower, upper)
    
    def _detect_objects(self, hsv, masks):
        """Maskeleri kullanarak balonları tespit eder"""
        contours, _ = cv2.findContours(masks['combined'], 
                                     cv2.RETR_EXTERNAL, 
                                     cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if DETECTION_SETTINGS['MIN_AREA'] < area < DETECTION_SETTINGS['MAX_AREA']:
                detection = self._process_contour(contour, hsv, masks)
                if detection:
                    detections.append(detection)
        
        return self._apply_nms(detections)
    
    def _process_contour(self, contour, hsv, masks):
        """Kontur bilgilerini işler ve tespit nesnesini oluşturur"""
        if len(contour) < 5:
            return None
            
        ellipse = cv2.fitEllipse(contour)
        (x, y), (MA, ma), angle = ellipse
        
        aspect_ratio = max(MA, ma) / min(MA, ma)
        if aspect_ratio >= DETECTION_SETTINGS['MAX_ASPECT_RATIO']:
            return None
        
        # ROI analizi
        y1, y2 = int(max(0, y-ma/2)), int(min(hsv.shape[0], y+ma/2))
        x1, x2 = int(max(0, x-MA/2)), int(min(hsv.shape[1], x+MA/2))
        roi = hsv[y1:y2, x1:x2]
        
        if roi.size == 0:
            return None
        
        # Renk oranları
        red_pixels = cv2.countNonZero(masks['red'][y1:y2, x1:x2])
        blue_pixels = cv2.countNonZero(masks['blue'][y1:y2, x1:x2])
        total_pixels = roi.shape[0] * roi.shape[1]
        
        if total_pixels == 0:
            return None
            
        red_ratio = red_pixels / total_pixels
        blue_ratio = blue_pixels / total_pixels
        
        if max(red_ratio, blue_ratio) <= DETECTION_SETTINGS['MIN_COLOR_RATIO']:
            return None
        
        color = "red" if red_ratio > blue_ratio else "blue"
        
        return {
            "bbox": [x1, y1, x2, y2],
            "confidence": 1.0 / aspect_ratio,
            "color": color,
            "is_laser_mode": self.use_laser_mode,
            "color_ratio": red_ratio if color == "red" else blue_ratio,
            "ellipse": {
                "center": [x, y],
                "axes": [MA, ma],
                "angle": angle
            }
        }
    
    def _apply_nms(self, detections, iou_threshold=0.5):
        """Non-maximum suppression uygular"""
        if not detections:
            return []
        
        detections = sorted(detections, key=lambda x: x["color_ratio"], reverse=True)
        filtered_detections = []
        
        while detections:
            best = detections.pop(0)
            filtered_detections.append(best)
            
            detections = [
                d for d in detections
                if self._calculate_iou(d["bbox"], best["bbox"]) < iou_threshold
                or d["color"] != best["color"]
            ]
        
        return filtered_detections
    
    def _calculate_iou(self, box1, box2):
        """İki bounding box arasındaki IoU değerini hesaplar"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = box1_area + box2_area - intersection
        
        return intersection / union if union > 0 else 0
    
    def _check_mode_switch(self, detections):
        """Otomatik mod için mod değişikliği kontrolü yapar"""
        blue_count = len([d for d in detections if d["color"] == "blue"])
        self.last_blue_counts.append(blue_count)
        
        if len(self.last_blue_counts) > DETECTION_SETTINGS['DETECTION_HISTORY_SIZE']:
            self.last_blue_counts.pop(0)
        
        if len(self.last_blue_counts) == DETECTION_SETTINGS['DETECTION_HISTORY_SIZE']:
            avg_blue = sum(self.last_blue_counts[:-1]) / (DETECTION_SETTINGS['DETECTION_HISTORY_SIZE'] - 1)
            current_blue = self.last_blue_counts[-1]
            
            if not self.use_laser_mode:
                if current_blue < avg_blue * DETECTION_SETTINGS['DETECTION_DROP_THRESHOLD'] and avg_blue > 0:
                    self.use_laser_mode = True
                    self.laser_frame_count = 0
            else:
                self.laser_frame_count += 1
                if (self.laser_frame_count >= DETECTION_SETTINGS['MIN_LASER_FRAMES'] and 
                    current_blue >= avg_blue * DETECTION_SETTINGS['NORMAL_MODE_THRESHOLD']):
                    self.use_laser_mode = False 