#!/usr/bin/env python3
"""
TikTok OAuth ve API akışını test eden script
"""

import asyncio
import httpx
import webbrowser
from urllib.parse import urlparse, parse_qs

async def test_oauth_flow():
    """OAuth akışını test et"""
    base_url = "http://localhost:8000"  # veya ngrok URL'iniz
    
    async with httpx.AsyncClient() as client:
        # 1. Authorization URL'i al
        print("1. Getting authorization URL...")
        response = await client.get(f"{base_url}/api/v1/auth/tiktok/authorize")
        data = response.json()
        
        auth_url = data["authorization_url"]
        state = data["state"]
        
        print(f"Authorization URL: {auth_url}")
        print(f"State: {state}")
        
        # 2. Tarayıcıda aç
        print("\n2. Opening browser for TikTok login...")
        webbrowser.open(auth_url)
        
        # 3. Callback URL'i manuel olarak gir
        print("\n3. After authorizing, paste the callback URL here:")
        callback_url = input("Callback URL: ")
        
        # 4. Code'u parse et
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        returned_state = params.get("state", [None])[0]
        
        if not code:
            print("Error: No authorization code found in callback URL")
            return
        
        print(f"\n4. Authorization code received: {code[:20]}...")
        
        # 5. Callback endpoint'ini çağır
        print("\n5. Exchanging code for token...")
        # Önce login olmalıyız
        # Test kullanıcısı oluştur veya var olan ile giriş yap
        
        return code, state

async def test_api_endpoints(access_token: str):
    """API endpoint'lerini test et"""
    base_url = "http://localhost:8000"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        # 1. User info
        print("\n1. Testing user info endpoint...")
        response = await client.get(
            f"{base_url}/api/v1/tiktok/user/info",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"User info: {response.json()}")
        
        # 2. Videos
        print("\n2. Testing videos endpoint...")
        response = await client.get(
            f"{base_url}/api/v1/tiktok/videos",
            headers=headers,
            params={"max_count": 5}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            videos = response.json()["videos"]
            print(f"Found {len(videos)} videos")
            
            # 3. Video insights
            if videos:
                video_ids = [v["id"] for v in videos[:3]]
                print(f"\n3. Testing video insights for {video_ids}...")
                
                response = await client.post(
                    f"{base_url}/api/v1/tiktok/videos/fetch-insights",
                    headers=headers,
                    params={"video_ids": video_ids}
                )
                print(f"Status: {response.status_code}")
                print(f"Response: {response.json()}")

if __name__ == "__main__":
    print("TikTok API Integration Test")
    print("=" * 50)
    asyncio.run(test_oauth_flow())