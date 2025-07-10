#!/usr/bin/env python3
"""
TikTok Analytics CLI Script
Bu script, TikTok OAuth akışını takip ederek önce authorization code'dan access token alır,
sonra bu token ile TikTok Commercial API metriklerini çeker ve terminalde gösterir.
"""

import asyncio
import httpx
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import unquote

# Proje root'u Python path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Proje içinden settings'i import et
try:
    from app.config.settings import settings
except ImportError:
    print("Hata: Proje settings'i import edilemedi. Script'i proje dizininden çalıştırdığınızdan emin olun.")
    sys.exit(1)

# API Base URL
API_BASE_URL = "http://127.0.0.1:8000"

# Renkli çıktı için ANSI kodları
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


async def exchange_code_for_token(code: str) -> Optional[Dict[str, Any]]:
    """
    Authorization code'u access token ile değiştirir.
    
    Args:
        code: TikTok'tan gelen authorization code
        
    Returns:
        dict: Token response veya None
    """
    # TikTok token endpoint
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    
    # Request body
    data = {
        "client_key": settings.TIKTOK_CLIENT_KEY,
        "client_secret": settings.TIKTOK_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.TIKTOK_REDIRECT_URI
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    print(f"\n{Colors.CYAN}[info] Authorization code ile token değişimi yapılıyor...{Colors.ENDC}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                token_url,
                data=data,
                headers=headers
            )
            
            if response.status_code == 200:
                print(f"{Colors.GREEN}[success] Token başarıyla alındı!{Colors.ENDC}")
                return response.json()
            else:
                print(f"{Colors.RED}[error] Token alınamadı. Status: {response.status_code}{Colors.ENDC}")
                print(f"{Colors.RED}Response: {response.text}{Colors.ENDC}")
                return None
                
        except httpx.RequestError as e:
            print(f"{Colors.RED}[error] İstek hatası: {e}{Colors.ENDC}")
            return None


def display_token_info(token_data: Dict[str, Any]):
    """
    Token bilgilerini terminalde gösterir.
    
    Args:
        token_data: TikTok token response
    """
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== TikTok Token Response ==={Colors.ENDC}")
    print(f"\n{Colors.CYAN}┌─────────────────────────────┬─────────────────────────────────────────────────┐{Colors.ENDC}")
    print(f"{Colors.CYAN}│ Key                         │ Value                                           │{Colors.ENDC}")
    print(f"{Colors.CYAN}├─────────────────────────────┼─────────────────────────────────────────────────┤{Colors.ENDC}")
    
    # open_id
    open_id = token_data.get("open_id", "N/A")
    print(f"│ open_id                     │ {open_id[:47]:47} │")
    if len(open_id) > 47:
        print(f"│                             │ {open_id[47:]:47} │")
    
    # scope
    scope = token_data.get("scope", "N/A")
    print(f"│ scope                       │ {scope[:47]:47} │")
    
    # access_token (kısaltılmış gösterim)
    access_token = token_data.get("access_token", "N/A")
    token_preview = f"{access_token[:20]}...{access_token[-20:]}" if len(access_token) > 50 else access_token
    print(f"│ access_token                │ {token_preview[:47]:47} │")
    
    # expires_in
    expires_in = token_data.get("expires_in", 0)
    print(f"│ expires_in                  │ {str(expires_in) + ' seconds':47} │")
    
    # refresh_token (kısaltılmış gösterim)
    refresh_token = token_data.get("refresh_token", "N/A")
    refresh_preview = f"{refresh_token[:20]}...{refresh_token[-20:]}" if len(refresh_token) > 50 else refresh_token
    print(f"│ refresh_token               │ {refresh_preview[:47]:47} │")
    
    # refresh_expires_in
    refresh_expires = token_data.get("refresh_expires_in", 0)
    print(f"│ refresh_expires_in          │ {str(refresh_expires) + ' seconds':47} │")
    
    # token_type
    token_type = token_data.get("token_type", "N/A")
    print(f"│ token_type                  │ {token_type[:47]:47} │")
    
    print(f"{Colors.CYAN}└─────────────────────────────┴─────────────────────────────────────────────────┘{Colors.ENDC}")
    
    # Ek bilgiler
    print(f"\n{Colors.YELLOW}📝 Not: Bu değerleri backend'inizde saklamanız gerekmektedir.{Colors.ENDC}")
    print(f"{Colors.YELLOW}⏰ Access token {expires_in} saniye ({expires_in//3600} saat) geçerlidir.{Colors.ENDC}")
    print(f"{Colors.YELLOW}🔄 Refresh token {refresh_expires//86400} gün geçerlidir.{Colors.ENDC}")


async def get_tiktok_analytics(token: str) -> Dict[str, Any]:
    """
    TikTok analytics verilerini çeker ve işler.
    
    Args:
        token: TikTok access token (sistem JWT'si değil!)
        
    Returns:
        dict: İşlenmiş analytics verileri
    """
    # Önce bu TikTok token'ı kullanarak sisteme giriş yapmalıyız
    # Bunun için backend'e TikTok token'ı göndereceğiz
    
    print(f"\n{Colors.CYAN}[info] TikTok verileri çekiliyor...{Colors.ENDC}")
    
    analytics_data = {
        "user_info": {},
        "videos": [],
        "total_metrics": {
            "video_count": 0,
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "follower_count": 0,
            "following_count": 0,
            "likes_count": 0
        },
        "errors": []
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # TikTok API'ye doğrudan istek at
            # 1. Kullanıcı bilgilerini al
            print(f"{Colors.CYAN}[info] Kullanıcı bilgileri alınıyor...{Colors.ENDC}")
            
            user_response = await client.get(
                "https://open.tiktokapis.com/v2/user/info/",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                params={
                    "fields": "open_id,union_id,avatar_url,display_name,bio_description,profile_deep_link,is_verified,follower_count,following_count,likes_count,video_count"
                }
            )
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                user_info = user_data.get("data", {}).get("user", {})
                analytics_data["user_info"] = user_info
                analytics_data["total_metrics"]["follower_count"] = user_info.get("follower_count", 0)
                analytics_data["total_metrics"]["following_count"] = user_info.get("following_count", 0)
                analytics_data["total_metrics"]["likes_count"] = user_info.get("likes_count", 0)
                print(f"{Colors.GREEN}[success] Kullanıcı bilgileri alındı: {user_info.get('display_name', 'N/A')}{Colors.ENDC}")
            else:
                analytics_data["errors"].append(f"Kullanıcı bilgileri alınamadı: {user_response.status_code}")
            
            # 2. Video listesini al
            print(f"{Colors.CYAN}[info] Video listesi alınıyor...{Colors.ENDC}")
            
            videos_response = await client.post(
                "https://open.tiktokapis.com/v2/video/list/",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"max_count": 20}
            )
            
            if videos_response.status_code == 200:
                videos_data = videos_response.json()
                videos = videos_data.get("data", {}).get("videos", [])
                analytics_data["videos"] = videos
                analytics_data["total_metrics"]["video_count"] = len(videos)
                
                # Video metriklerini topla
                for video in videos:
                    analytics_data["total_metrics"]["total_views"] += video.get("view_count", 0)
                    analytics_data["total_metrics"]["total_likes"] += video.get("like_count", 0)
                    analytics_data["total_metrics"]["total_comments"] += video.get("comment_count", 0)
                    analytics_data["total_metrics"]["total_shares"] += video.get("share_count", 0)
                
                print(f"{Colors.GREEN}[success] {len(videos)} video bulundu.{Colors.ENDC}")
            else:
                analytics_data["errors"].append(f"Video listesi alınamadı: {videos_response.status_code}")
                
        except Exception as e:
            analytics_data["errors"].append(f"Beklenmeyen hata: {str(e)}")
            print(f"{Colors.RED}Hata detayı: {e}{Colors.ENDC}")
    
    return analytics_data


def display_analytics(analytics_data: Dict[str, Any]):
    """
    Analytics verilerini terminalde tablo formatında gösterir.
    
    Args:
        analytics_data: İşlenmiş analytics verileri
    """
    print("\n" + "="*65)
    print(f"{Colors.BOLD}{Colors.HEADER}📊 TikTok Hesap Analiz Raporu{Colors.ENDC}")
    print("="*65)
    
    # Kullanıcı bilgileri
    user_info = analytics_data.get("user_info", {})
    if user_info:
        print(f"\n{Colors.CYAN}👤 Kullanıcı: {user_info.get('display_name', 'N/A')}{Colors.ENDC}")
        print(f"{Colors.CYAN}🆔 Open ID: {user_info.get('open_id', 'N/A')}{Colors.ENDC}")
    
    # Hatalar varsa göster
    if analytics_data["errors"]:
        print(f"\n{Colors.RED}⚠️  Hatalar:{Colors.ENDC}")
        for error in analytics_data["errors"]:
            print(f"{Colors.YELLOW}• {error}{Colors.ENDC}")
        print()
    
    # Metrikler tablosu
    metrics = analytics_data["total_metrics"]
    
    print(f"\n{Colors.CYAN}┌─────────────────────────────┬─────────────────────────────────┐{Colors.ENDC}")
    print(f"{Colors.CYAN}│ Metrik                      │ Değer                           │{Colors.ENDC}")
    print(f"{Colors.CYAN}├─────────────────────────────┼─────────────────────────────────┤{Colors.ENDC}")
    
    # Hesap metrikleri
    print(f"│ Takipçi Sayısı              │ {metrics['follower_count']:>31,} │")
    print(f"│ Takip Edilen                │ {metrics['following_count']:>31,} │")
    print(f"│ Toplam Beğeni (Hesap)       │ {metrics['likes_count']:>31,} │")
    
    print(f"{Colors.CYAN}├─────────────────────────────┼─────────────────────────────────┤{Colors.ENDC}")
    
    # Video metrikleri
    print(f"│ Toplam Video Sayısı         │ {metrics['video_count']:>31,} │")
    print(f"│ Toplam Görüntülenme         │ {metrics['total_views']:>31,} │")
    print(f"│ Toplam Beğeni (Videolar)    │ {metrics['total_likes']:>31,} │")
    print(f"│ Toplam Yorum                │ {metrics['total_comments']:>31,} │")
    print(f"│ Toplam Paylaşım             │ {metrics['total_shares']:>31,} │")
    
    print(f"{Colors.CYAN}└─────────────────────────────┴─────────────────────────────────┘{Colors.ENDC}")
    
    # En popüler videolar
    if analytics_data["videos"]:
        print(f"\n{Colors.CYAN}🎬 En Popüler 3 Video:{Colors.ENDC}")
        sorted_videos = sorted(analytics_data["videos"], key=lambda x: x.get("view_count", 0), reverse=True)[:3]
        for i, video in enumerate(sorted_videos, 1):
            desc = video.get("video_description", "Açıklama yok")[:50] + "..." if len(video.get("video_description", "")) > 50 else video.get("video_description", "Açıklama yok")
            print(f"{i}. {desc} - {video.get('view_count', 0):,} görüntülenme")
    
    # Analiz zamanı
    print(f"\n{Colors.BLUE}Analiz zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")


async def main():
    """Ana fonksiyon - tüm akışı yönetir"""
    print(f"{Colors.BOLD}{Colors.CYAN}TikTok Analytics CLI{Colors.ENDC}")
    print("=" * 50)
    print(f"\n{Colors.YELLOW}Bu araç TikTok OAuth akışını takip eder:{Colors.ENDC}")
    print(f"1. Authorization code → Access token dönüşümü")
    print(f"2. Access token ile TikTok verilerini çekme\n")
    
    # Adım 1: Authorization Code'u al
    print(f"{Colors.CYAN}📝 Adım 1: Authorization Code{Colors.ENDC}")
    print(f"{Colors.YELLOW}TikTok OAuth callback URL'inden 'code' parametresini kopyalayın.{Colors.ENDC}")
    print(f"{Colors.YELLOW}Örnek: ?code=DE05kUU29z_VqbqdIJO...{Colors.ENDC}")
    print(f"\n{Colors.CYAN}Authorization Code'u girin:{Colors.ENDC}")
    code = input("> ").strip()
    
    # URL decode yap (eğer encode edilmişse)
    code = unquote(code)
    
    if not code:
        print(f"\n{Colors.RED}❌ Code boş olamaz. Program sonlandırılıyor.{Colors.ENDC}")
        return
    
    # Adım 2: Code'u token ile değiştir
    print(f"\n{Colors.CYAN}📝 Adım 2: Token Exchange{Colors.ENDC}")
    token_data = await exchange_code_for_token(code)
    
    if not token_data:
        print(f"\n{Colors.RED}❌ Token alınamadı. Program sonlandırılıyor.{Colors.ENDC}")
        return
    
    # Token bilgilerini göster
    display_token_info(token_data)
    
    # Adım 3: Access token ile veri çek
    print(f"\n{Colors.CYAN}📝 Adım 3: TikTok Verilerini Çekme{Colors.ENDC}")
    print(f"{Colors.YELLOW}Yukarıdaki access_token'ı kullanmak istiyor musunuz? (E/H){Colors.ENDC}")
    choice = input("> ").lower()
    
    if choice == 'e':
        access_token = token_data.get("access_token")
    else:
        print(f"\n{Colors.CYAN}Access Token'ı manuel olarak girin:{Colors.ENDC}")
        access_token = input("> ").strip()
    
    if not access_token:
        print(f"\n{Colors.RED}❌ Access token boş olamaz. Program sonlandırılıyor.{Colors.ENDC}")
        return
    
    # Analytics verilerini çek
    analytics_data = await get_tiktok_analytics(access_token)
    
    # Sonuçları göster
    display_analytics(analytics_data)
    
    # Çıkış mesajı
    print(f"\n{Colors.BLUE}Çıkmak için Enter'a basın...{Colors.ENDC}")
    input()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Program kullanıcı tarafından sonlandırıldı.{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}Beklenmeyen hata: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()