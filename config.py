# HSV değerleri için varsayılan ayarlar
DEFAULT_HSV_VALUES = {
    'normal_blue': {
        'H Min': 70, 'H Max': 110,
        'S Min': 90, 'S Max': 255,
        'V Min': 80, 'V Max': 255
    },
    'normal_red1': {
        'H Min': 0, 'H Max': 10,
        'S Min': 100, 'S Max': 255,
        'V Min': 100, 'V Max': 255
    },
    'normal_red2': {
        'H Min': 160, 'H Max': 180,
        'S Min': 100, 'S Max': 255,
        'V Min': 50, 'V Max': 255
    },
    'laser_blue': {
        'H Min': 60, 'H Max': 115,
        'S Min': 90, 'S Max': 255,
        'V Min': 70, 'V Max': 255
    },
    'laser_red1': {
        'H Min': 0, 'H Max': 10,
        'S Min': 150, 'S Max': 255,
        'V Min': 200, 'V Max': 255
    },
    'laser_red2': {
        'H Min': 128, 'H Max': 180,
        'S Min': 180, 'S Max': 255,
        'V Min': 128, 'V Max': 255
    }
}

# Tespit ayarları
DETECTION_SETTINGS = {
    'MIN_AREA': 300,  # Minimum balon alanı
    'MAX_AREA': 15000,  # Maximum balon alanı
    'MAX_ASPECT_RATIO': 1.5,  # Maximum en-boy oranı
    'MIN_COLOR_RATIO': 0.3,  # Minimum renk oranı
    'DETECTION_HISTORY_SIZE': 10,  # Mod değişimi için geçmiş boyutu
    'DETECTION_DROP_THRESHOLD': 0.5,  # Tespit düşüş eşiği
    'NORMAL_MODE_THRESHOLD': 0.8,  # Normal moda geçiş eşiği
    'MIN_LASER_FRAMES': 20,  # Minimum lazer modu frame sayısı
}

# GUI ayarları
GUI_SETTINGS = {
    'WINDOW_WIDTH': 1400,
    'WINDOW_HEIGHT': 800,
    'VIDEO_PANEL_RATIO': 2,  # Video panel genişlik oranı
    'PRESET_PANEL_RATIO': 1,  # Preset panel genişlik oranı
    'STATS_OVERLAY_WIDTH': 200,
    'STATS_OVERLAY_HEIGHT': 100,
    'MIN_WINDOW_WIDTH': 800,
    'MIN_WINDOW_HEIGHT': 600,
}

# Video işleme ayarları
VIDEO_SETTINGS = {
    'TARGET_FPS': 240,
    'NMS_THRESHOLD': 0.5,
} 