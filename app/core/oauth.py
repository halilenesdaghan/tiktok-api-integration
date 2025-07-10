# app/core/oauth.py

import httpx
import base64
import hashlib
import secrets
import json
from typing import Tuple, Dict, Any, Optional
from urllib.parse import urlencode

from app.config.settings import settings
from app.core.cache import cache_manager


class TikTokOAuth2:
    """
    TikTok OAuth 2.0 akışını PKCE ile yöneten sınıf.
    """
    def __init__(self, client_key: str, client_secret: str, redirect_uri: str):
        self.client_key = client_key
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorization_base_url = "https://www.tiktok.com/v2/auth/authorize"
        self.token_url = "https://open.tiktokapis.com/v2/oauth/token/"

    def generate_pkce_pair(self) -> Tuple[str, str]:
        """PKCE code_verifier ve code_challenge üretir"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('utf-8')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).rstrip(b'=').decode('utf-8')
        return code_verifier, code_challenge

    def get_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str, str]:
    
        code_verifier, code_challenge = self.generate_pkce_pair()
    
        if not state:
            state = base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b'=').decode('utf-8')

        # Scope'ları BOŞLUKLA birleştir
        scopes = "user.info.basic"  # Başlangıç için bu ikisi yeterli
        

        params = {
            "client_key": self.client_key,  # client_id değil!
            "scope": scopes,      # Boşlukla birleştir
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    
        authorization_url = f"{self.authorization_base_url}?{urlencode(params)}"
    
        return authorization_url, state, code_verifier

    async def get_access_token(self, code: str, code_verifier: str) -> Dict[str, Any]:
        """Access token al"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_key": self.client_key,      # client_id değil!
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                    "code_verifier": code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
        
        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"Token error: {error_data}")
            
        return response.json()


# Global client
tiktok_oauth_client = TikTokOAuth2(
    client_key=settings.TIKTOK_CLIENT_KEY,
    client_secret=settings.TIKTOK_CLIENT_SECRET,
    redirect_uri=settings.TIKTOK_REDIRECT_URI,
)