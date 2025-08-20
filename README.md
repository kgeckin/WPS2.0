# WhatsApp Phishing Awareness Simulator (WPS)

## Proje Hakkında

WhatsApp Phishing Awareness Simulator, kurum çalışanlarının siber güvenlik farkındalığını artırmak için geliştirilmiş bir simülasyon ve eğitim platformudur. Kullanıcılara WhatsApp üzerinden sahte mesajlar gönderilir, etkileşimler (tıklama, giriş denemesi, eğitim) hem GUI arayüzünde hem de MySQL tabanında gerçek zamanlı olarak raporlanır.

---

## Dizin Yapısı

```
WPS/
├── main.py                # Ana başlatıcı: Flask server + masaüstü GUI
├── gui.py                 # Tkinter tabanlı masaüstü arayüz
├── sender.py              # Selenium ile WhatsApp mesajlarını gönderir
├── encrypt_utils.py       # Link şifreleme/deşifreleme (Fernet)
├── db_utils.py            # MySQL bağlantısı ve CRUD işlemleri
├── phishing_server/
│   ├── app.py             # Flask backend (redirect/login/awareness)
│   └── templates/
│       ├── login.html     # Sahte giriş formu
│       └── awareness.html # Farkındalık/awareness sayfası
├── .env                   # Ortam değişkenleri (örnek: .env.example)
├── requirements.txt       # Python bağımlılıkları
├── wps_local.sql          # MySQL tablo şeması
```

---

## Contributor'lar

* Proje sahibi: Kardelen Geçkin
* Katkıda bulunanlar: Beytül Kocakaplan

---

## Kurulum ve Çalıştırma

1. **Depoyu klonla:**

   ```bash
   git clone <repo-link>
   cd WPS
   ```

2. **Python paketlerini yükle:**

   ```bash
   pip install -r requirements.txt
   ```

3. **.env dosyasını oluştur ve yapılandır:**

   Örnek:

   ```env
   SECRET_KEY=xxx  # Fernet anahtarı
   ADMIN_PASS=xxx  # Yönetici şifresi
   DB_HOST=localhost
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_NAME=wps_local
   ```

   > DB ayarlarını ve backend IP/hostname/portunu kendi ortamına göre düzenle.

4. **MySQL kurulumu**

   * Proje MySQL veritabanı gerektirir. Kendi bilgisayarında veya ağdaki bir sunucuda MySQL Community Server kurulu olmalıdır.
   * Yalnızca awareness simülasyonu için değil, tüm loglama, raporlama ve kullanıcı yönetimi için MySQL kurulumu şarttır.
   * MySQL yoksa uygulama çalışmaz.

5. **MySQL’de tablo şemasını yükle:**

   ```sql
   -- MySQL Workbench veya terminalde:
   source wps_local.sql
   ```

6. **Projeyi başlat:**

   ```bash
   python main.py
   ```

   * Hem Flask backend hem de masaüstü GUI açılır.

---

## Kısa Açıklama

* WhatsApp mesajları Selenium ile otomatik gönderilir.
* Linkler, kullanıcıya özel şifreli token ile gelir.
* Kullanıcılar tıkladığında, şirket ağı içindeki Flask backend’e yönlenir.
* Login denemeleri ve awareness sayfası, hem GUI arayüzünde hem de MySQL tabanında raporlanır.

---

## Güvenlik ve Gizlilik

* Proje yalnızca eğitim ve farkındalık amaçlıdır.
* Gerçek kullanıcı şifresi toplanmaz, tüm girişler simülasyon amaçlıdır.
* Veriler şirket içi veritabanında tutulur.

---

## Destek ve İletişim

Sorularınız için:

* Proje Sahibi: Kardelen Geçkin
* E-posta: kardelengeckin@gmail.com
