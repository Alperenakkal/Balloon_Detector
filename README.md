# Balloon_Detector
PyQt5 ile oluşturulmuş grafik arayüz (GUI) ve iki farklı tespit yöntemi kullanır: Renk tabanlı (HSV) segmentasyon ve YOLO (You Only Look Once) nesne tespiti.


1.  **Projeyi Klonlama:**
    ```bash
    git clone https://github.com/kullaniciadiniz/balloon_detector.git
    cd balloon_detector
    ```

2.  **Sanal Ortam Oluşturma:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Gerekli Kütüphaneleri Yükleme:**
    Proje kök dizininde bir `requirements.txt` dosyası var. Onu yükleyin.

    Yükleme komutu:
    ```bash
    pip install -r requirements.txt
    ```
    *Not: Ultralytics ve Torch kurulumu sisteminize (özellikle CUDA desteği varsa GPU kullanımı için) göre farklılık gösterebilir. 
     https://developer.nvidia.com/cuda-gpus buradan bakıp versiyonunuza göre yükleme yapabilirsiniz. Yapmadan işlemci ile de çalışabilirsiniz.*

4.  **YOLO Modeli (İsteğe Bağlı):**
    Google Drive linki: https://drive.google.com/file/d/1mT1PBRCZNb0AIt5kSMmF5pNPCWqybxug/

## **Katkıda Bulunma (Contributing)**


Projeyi Fork'layın.

 
Yeni bir Feature Branch oluşturun (git checkout -b feature/YeniOzellik).

 
Değişikliklerinizi Commit'leyin (git commit -am 'Yeni özellik eklendi').

 
Branch'inizi Push'layın (git push origin feature/YeniOzellik).

 
Bir Pull Request açın.
