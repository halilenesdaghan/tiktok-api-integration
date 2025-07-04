import os
import requests
import uuid
from flask import Flask, request, redirect, session, url_for
from dotenv import load_dotenv

# .env dosyasındaki gizli verileri yükle
load_dotenv()

app = Flask(__name__)
# Session'ları (kullanıcı oturumları) güvende tutmak için gizli bir anahtar.
# Gerçek bir projede bunu da .env dosyasından çekmelisiniz.
app.secret_key = os.urandom(24)

# TikTok'tan alınan ve .env dosyasında saklanan bilgiler
# Bu bilgileri doğrudan koda yazmak yerine .env dosyasından çekmek daha güvenlidir.
# os.getenv("TIKTOK_CLIENT_KEY", "sbawyis5zxfdx5u341") şeklinde kullanılabilir.
TIKTOK_CLIENT_KEY = "sbawyis5zxfdx5u341"
TIKTOK_CLIENT_SECRET = "9zTG7pVM8Tuoh128oHTgtxvMcJiJHzekH8fz0D7RqHI"

# Uygulama ayarlarında belirttiğimiz Geri Arama (Callback) URL'i
# Kodun ve TikTok ayarlarının tutarlı olması çok önemli!
TIKTOK_REDIRECT_URI = "https://6636-193-140-111-38.ngrok-free.app/api/v1/auth/tiktok/callback"

# TikTok API endpoint'leri
AUTHORIZATION_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

@app.route("/")
def homepage():
    """
    Ana sayfa. Kullanıcıya giriş yapma seçeneği sunar.
    """
    if 'tiktok_token_data' in session:
        token_data = session['tiktok_token_data']
        return f"""
        <h1>Hoş Geldin!</h1>
        <p>TikTok hesabınla başarıyla giriş yaptın.</p>
        <p><b>Access Token (ilk 15 karakter):</b> {token_data['access_token'][:15]}...</p>
        <p><b>Kullanılabilir İzinler:</b> {token_data['scope']}</p>
        <a href="/logout">Çıkış Yap</a>
        """
    return """
    <h1>Sosyal Medya Market Analizi Aracına Hoşgeldiniz</h1>
    <a href="/login/tiktok">
        <button>TikTok ile Giriş Yap</button>
    </a>
    """

@app.route("/login/tiktok")
def tiktok_login():
    """
    Kullanıcıyı TikTok giriş sayfasına yönlendirir.
    """
    state = str(uuid.uuid4())
    session['csrf_state'] = state

    # --- GÜNCELLEME ---
    # 1. Hata almamak için öncelikle sadece onay gerektirmeyen 'user.info.basic' iznini istiyoruz.
    # 2. İzinleri virgül yerine boşlukla ayırıyoruz (OAuth 2.0 standardı).
    scopes = "user.info.basic,video.list,artist.certification.read,artist.certification.update,user.info.profile,user.info.stats"

    # TikTok Developer Portal'dan 'video.list' ve 'video.insights' için onay aldıktan sonra
    # aşağıdaki satırı kullanabilirsiniz:
    # scopes = "user.info.basic video.list video.insights"

    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "scope": scopes,
        "response_type": "code",
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": state,
    }
    
    req = requests.Request('GET', AUTHORIZATION_URL, params=params)
    url = req.prepare().url
    
    print(f"Kullanıcı şu adrese yönlendiriliyor: {url}")
    
    return redirect(url)

@app.route("/tiktok/callback")
def tiktok_callback():
    """
    Kullanıcı TikTok'ta izin verdikten sonra bu adrese yönlendirilir.
    """
    auth_code = request.args.get("code")
    returned_state = request.args.get("state")

    if 'csrf_state' not in session or session['csrf_state'] != returned_state:
        return "Hatalı State Değeri! CSRF Saldırısı olabilir.", 400
    del session['csrf_state']

    if not auth_code:
        error = request.args.get("error")
        error_description = request.args.get("error_description")
        return f"Yetki kodu alınamadı. Hata: {error} - {error_description}", 400

    token_payload = {
        "client_key": TIKTOK_CLIENT_KEY,
        "client_secret": TIKTOK_CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": TIKTOK_REDIRECT_URI,
    }

    try:
        response = requests.post(TOKEN_URL, data=token_payload)
        response.raise_for_status()
        
        token_data = response.json()
        
        # Gelen token'ları session'a kaydediyoruz.
        # Gerçek bir uygulamada bu token'lar veritabanında kullanıcı ile ilişkilendirilerek
        # şifreli bir şekilde saklanmalıdır.
        session['tiktok_token_data'] = token_data
        print("Başarıyla alınan token verisi:", token_data)
        
        return redirect(url_for("homepage"))

    except requests.exceptions.RequestException as e:
        print(f"Token alınırken hata oluştu: {e}")
        if e.response:
            print(f"Hata detayı: {e.response.text}")
        return "Access token alınırken bir hata oluştu. Lütfen logları kontrol edin.", 500

@app.route("/logout")
def logout():
    """Kullanıcı oturumunu sonlandırır."""
    session.pop('tiktok_token_data', None)
    return redirect(url_for('homepage'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)