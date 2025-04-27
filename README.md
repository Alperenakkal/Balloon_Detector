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
    *Not: Torch kurulumunu req içine eklemedim. Tercihi kendiniz yapabilmeniz için, eğer GPU'nuzda CUDA desteği varsa GPU kullanımı için kendinize uygun modeli yüklemelisiniz. 
     https://developer.nvidia.com/cuda-gpus buradan bakıp versiyonunuza göre yükleme yapabilirsiniz. 
     https://pytorch.org/get-started/locally/ bu siteden otomatik seçim de yapabilirsiniz.
     Eğer uğraşmak istemiyorsanız CPU kısmını seçip normal 1.8+ Torch ile de çalışabilirsiniz. İşlemci üzerinden yürütmüş olursunuz.*

4.  **YOLO Modeli (İsteğe Bağlı):**
    Google Drive linki: https://drive.google.com/file/d/1mT1PBRCZNb0AIt5kSMmF5pNPCWqybxug/

5. **Videolar**
   
    [Upscale x4](https://drive.google.com/file/d/1gCBHThvpjkFONm_a40dcgfIg8G3-92OO/)

    [x4to576](https://drive.google.com/file/d/1hrxgBg0rJh-2jgY65Oo7U3cFaYLfa71K/)

## **Katkıda Bulunma (Contributing)**


Projeyi Fork'layın.

 
Yeni bir Feature Branch oluşturun (git checkout -b feature/YeniOzellik).

 
Değişikliklerinizi Commit'leyin (git commit -am 'Yeni özellik eklendi').

 
Branch'inizi Push'layın (git push origin feature/YeniOzellik).

 
Bir Pull Request açın.


---

## Proje Yol Haritası ve Değişiklik Geçmişi

Bu belge, Balloon Detector projesinin gelişim aşamalarını ve gelecek planlarını özetlemektedir.

**Lejant:**
*   `[x]` - Tamamlandı
*   `[ ]` - Planlandı / Devam Ediyor

---

### **Tamamlanmış Versiyonlar**

#### **v1: Başlangıç ve Temel Entegrasyon**
*   `[x]` Projenin ilk kurulumu ve temel yapının oluşturulması.
*   `[x]` Temel OpenCV renk tabanlı tespit mantığının entegrasyonu.
*   `[x]` İlk PyQt5 tabanlı basit grafik arayüz (GUI) oluşturulması.

#### **v2: Modüler Yapıya Geçiş**
*   `[x]` Tek dosya yapısından modüler bir yapıya geçiş (örn: `core`, `gui`, `utils` klasörleri).
*   `[x]` Kodun yeniden düzenlenmesi ve okunabilirliğin artırılması.

#### **v3: GUI Geliştirmeleri ve Threading İyileştirmeleri**
*   `[x]` **UI İyileştirmeleri:**
    *   `[x]` Panel yönetimi için Dock Widget yapısı eklendi.
    *   `[x]` Uygulama ayarlarını göstermek için Konfigürasyon Paneli eklendi.
    *   `[x]` Videoda belirli bir kareye atlamak için sürükle-bırak özellikli ProgressBar eklendi.
    *   `[x]` Preset Panelinde açılıp kapanabilir (Collapsible Box) gruplar kullanıldı.
*   `[x]` **Arka Plan İşlemleri:**
    *   `[x]` Video işleme için daha sağlam bir QThread yapısı implemente edildi.
    *   `[x]` İşlem sürelerini (kare yakalama, tespit vb.) takip etmek için Zamanlama Metrikleri Paneli eklendi.

---

### **Mevcut Versiyon**

#### **v4: Test Modu, YOLO Entegrasyonu ve İyileştirmeler**
*   `[x]` Kod tekrarını azaltmak için yeniden yapılandırma (refactoring) yapıldı.
*   `[x]` **Sistem Kullanımı Paneli:**
    *   `[x]` Genel sistem ve uygulama özelinde CPU/Bellek kullanımı gösterimi eklendi.
    *   `[x]` Yüksek kaynak kullanımı durumunda uyarılar eklendi.
*   `[x]` **Test Modu:**
    *   `[x]` Videoları toplu olarak işleme yeteneği eklendi (belirli kare aralığı veya tam video).
    *   `[x]` Test için OpenCV (HSV) veya YOLO dedektörünü seçme imkanı sağlandı.
    *   `[x]` Tespit geçmişini (kare no, renk, güven, konum vb.) CSV formatında dışa aktarma özelliği eklendi.
*   `[x]` **YOLO Modu:**
    *   `[x]` Önceden eğitilmiş `.pt` YOLO modelleri ile nesne tespiti yapma yeteneği eklendi.
    *   `[x]` GUI üzerinden YOLO modeli yükleme arayüzü sağlandı.
*   `[x]` **OpenCV Modu Güncellemeleri:**
    *   `[x]` Tespit edilen konturları/maskeyi ayrı bir pencerede gösterme seçeneği eklendi (`show_contours_checkbox`).
    *   `[x]` Preset Panelindeki HSV slider'larının anlık olarak işlemciyi etkilemesi sağlandı.
*   `[ ]` **Yapılandırma:** `config.py` dosyasının kapsamını genişletme (daha fazla ayar ekleme).

---

### **Gelecek Planları**

#### **v5: Performans, Lazer Tespiti ve Karşılaştırma Modu**
*   `[ ]` **Lazer Tespiti:** Lazerli ortamdaki tespit algoritmasının doğruluğunu ve kararlılığını artırma.
Belki lazer tespiti için performanstan feragat edip görüntüdeki mavi piksel sayısının anlık çok fazla değişimini tespit etmeliyiz?
Kolayca implement edilebilir.
*   `[ ]` **Performans İyileştirmeleri:**
    *   `[ ]` GUI olmadan (headless) sadece işlem yapabilme seçeneği ekleme.
    Direkt GUI'siz olmak zorunda değil, ama en azından görüntüyü yansıtmayı kapatabiliriz. 
    If(!headless){ visualisation } gibi bir şey olabilir.
    *   `[ ]` YOLO için CUDA Kullanımı Seçeneği: Arayüzde bir onay kutusu ile kullanıcının (eğer sisteminde CUDA ve uyumlu PyTorch kuruluysa) YOLO çıkarım işlemini GPU üzerinde yapmasını sağlamak (device='cuda' veya device='cpu' seçimi).
    *   `[ ]` Çoklu iş parçacığı (multithreading) kullanımını daha da optimize etme.
    *   `[ ]` Kare işleme algoritmalarını hızlandırma (OpenCV optimizasyonları / YOLO için Quantization). 
    *   `[ ]` Bellek kullanımını azaltmak için veri yapılarını ve algoritmaları gözden geçirme. Pek önemli değil.
*   `[ ]` **Karşılaştırma Modu:**
    *   `[ ]` Farklı ayarların veya modların sonuçlarını yan yana karşılaştırma imkanı.
    *   `[ ]` *veya* Aynı anda birden fazla (örn. 4 tane) video kaynağını işleme yeteneği.

#### **v6: Gelişmiş Analiz Özellikleri**
*   `[ ]` **Takip:** Tespit edilen balonları kareler arasında takip etme (object tracking).
*   `[ ]` **Analiz:** Balonların yaklaşık hızını ve hareket yönünü hesaplama. 
    3 Kare baktıktan sonra anlamlı karar verilebilir, mevcut lazer tespite yakın bir şey deneyebilirsiniz, nesnenin kaybolma durumu ve çizilen bounding box'un değişimini kontrolü ilgili kendiniz bir kararda bulunun.  
*   `[ ]` **Olay Tespiti:** Balon patlama anlarını tespit etme ve takip için yeni balona geçiş.

#### **v7: Kontrol ve Otomasyon (Deneysel)**
*   `[ ]` Harici sistemleri simüle etmek için PID kontrolcü entegrasyonu olasılığı.
*   `[ ]` (Potansiyel) Otomatik hedefleme uygulamaları için altyapı yani nişancı.

#### **v8: Canlı Yayın Desteği**
*   `[ ]` Webcam, IP kamera veya diğer canlı video akışlarını işleyebilme desteği.

#### **v9: Dokümantasyon, Test ve Kalite**
*   `[ ]` **Dokümantasyon:** Kullanıcı kılavuzu ve geliştirici dokümantasyonunu iyileştirme.
*   `[ ]` **Test Süreçleri:**
    *   `[ ]` Kodun doğruluğunu sağlamak için birim testleri (unit tests) ekleme.
    *   `[ ]` Modüllerin birlikte doğru çalıştığını kontrol etmek için entegrasyon testleri ekleme.
    *   `[ ]` Farklı senaryolarda performans ölçümleri yapmak için performans testleri (benchmarks) geliştirme.
    *   `[ ]` Proje kalitesini takip etmek için metrikler belirleme.

---
