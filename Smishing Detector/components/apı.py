# app.py

import os
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

# .env dosyasından ortam değişkenlerini yükle
load_dotenv()

# GOOGLE_API_KEY değişkenini al
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("Hata: GOOGLE_API_KEY, .env dosyasında bulunamadı.")

# API anahtarını kullanarak istemciyi başlat
try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    print(f"Hata: Gemini İstemcisi başlatılamadı: {e}")
    exit()

# Kullanılacak model
MODEL_NAME = "gemini-2.5-pro"

# --- Model Çağrısı ---

def get_gemini_response(prompt: str):
    """
    Belirtilen prompt ile Gemini 2.5 Pro modelini çağırır.
    """
    print(f"Prompt gönderiliyor: '{prompt[:50]}...'")
    try:
        # Sohbet istemi oluşturma ve gönderme
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        return response

    except APIError as e:
        print(f"\nAPI Hatası oluştu: {e}")
        return None
    except Exception as e:
        print(f"\nBeklenmedik bir hata oluştu: {e}")
        return None

# Örnek kullanım
prompt_to_send = "Türkiye'deki 3 popüler tarihi yeri ve kısa açıklamalarını yazar mısın?"

gemini_response = get_gemini_response(prompt_to_send)

# Sonucu yazdırma
if gemini_response:
    print("\n--- Gemini 2.5 Pro Yanıtı ---\n")
    print(gemini_response.text)
    print("\n------------------------------\n")

   
  