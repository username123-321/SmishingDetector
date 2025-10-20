import re
import string
import unicodedata
import spacy
from nltk.corpus import stopwords 

# --- GEREKLİ NLTK KAYNAKLARI ---
try:
    english_stopwords = set(stopwords.words('english'))
except LookupError:
    import nltk
    nltk.download('stopwords')
    english_stopwords = set(stopwords.words('english'))

# --- spaCy Modelini Yükleme ---
try:
    nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "textcat"])
except OSError:
    print("[HATA] Lütfen komut satırında 'python -m spacy download en_core_web_sm' komutunu çalıştırın.")
    raise

# --- PREPROCESSING FUNCTION ---
def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()

    # 2. Unicode Normalizasyonu ve Aksan Giderme (De-accenting)
    try:
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    except:
        pass

    # 3. YENİ EKLEME: Non-ASCII ve HTML Karakterlerini Temizleme
    # Amacı: SMS'lerde kalabilen gereksiz kodlama artıkları (örn: ÃƒÂ¯Ã‚Â¿Ã‚Â½) ve HTML etiketlerini kaldırmak.
    text = re.sub(r'[^a-zA-Z0-9\s<>$£₺]+', ' ', text)
    text = re.sub(r'<.*?>', ' ', text) # HTML etiketlerini kaldır
    text = re.sub(r'(\s\s+)', ' ', text).strip()
    
    # 4. YENİ EKLEME: Tekrar Eden Noktalama İşaretlerini Normalleştirme ('!!!' -> '!')
    text = re.sub(r'([!?])\1+', r'\1', text) 

    # 5. Tekrarlanan Karakterleri Azaltma ('cooool' -> 'cool')
    text = re.sub(r'(.)\1{2,}', r'\1\1', text) 
    
    # Şüpheli Anahtar Kelimeleri Etiketleme
    suspicious_keywords = [
        "account", "password", "verify", "login", "update", "confirm", "reward", "won", "bank", "security", "id", "delivery", "payment", "suspend", "locked", "urgent",
        "click", "link", "free", "immediate", "now", "alert", "warning", "change", "win", "prize", "billing", "invoice", "card", "credit", "action required", "respond",
        "claim", "suspicious", "fraud", "limited time", "expires", "personal", "confidential", "unauthorized", "access", "reset", "secure", "transaction", "balance", "due",
        "overdue", "pending", "failed", "declined", "package", "tracking", "shipment", "offer", "deal", "discount", "gift", "voucher", "coupon", "exclusive", 
        "verify your identity", "update your information", "account verification", "login attempt", "security breach", "unusual activity", "contact us", "call now", 
        "text back", "reply", "subscription", "membership", "trial", "expiration", "renew", "funds", "transfer", "deposit", "withdrawal", "review", "confirm payment", 
        "validate", "authentication", "pin", "code", "OTP", "urgent action", "last chance", "time-sensitive", "act now", "don’t miss", "failure to respond", 
        "account closure", "verify now", "click here", "short link", "download", "install", "app", "survey", "bonus", "cash", "lottery", "sweepstakes", "charity", 
        "donation", "tax", "refund", "government", "IRS", "legal", "lawsuit", "warrant", "arrest", "debt", "collection", "pay now", "secure link", 
        "personal information", "SSN", "account number", "bank details", "password reset", "urgent update", "limited offer", "exclusive offer", "contact immediately"
    ]
    for word in suspicious_keywords:
        if word in text:
            text += f" <ALERT_{word.upper()}> " 

    # Anonimleştirme
    text = re.sub(r'http\S+|www\S+', ' <URL> ', text)
    text = re.sub(r'\S+@\S+', ' <EMAIL> ', text)
    text = re.sub(r'(\+?\d[\d\s\-\(\)]{4,}\d)', ' <PHONE> ', text) 
    text = re.sub(r'\b[a-z0-9.-]+\.[a-z]{2,}\b', ' <DOMAIN> ', text) 
    text = re.sub(r'\d+\s*(usd|eur|\$|£|tl|₺)', ' <MONEY> ', text)
    text = re.sub(r'\d+', ' <NUM> ', text)
    
    # Noktalama Temizliği
    text = text.translate(str.maketrans('', '', string.punctuation.replace("'", "")))
    
    # Ek Temizlik
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Lemmatizasyon ve Stop Word Kaldırma
    doc = nlp(text)
    tokens = []
    for token in doc:
        lemma = token.lemma_
        if lemma not in english_stopwords and len(lemma) > 1:
            tokens.append(lemma)
            
    return ' '.join(tokens)