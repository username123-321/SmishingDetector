import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
# Değerlendirme için gerekli metrikler
from sklearn.metrics import classification_report, accuracy_score, make_scorer, f1_score
from sklearn.preprocessing import LabelEncoder
import joblib
import time
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
def preprocess_sms(text: str) -> str:
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

# --- 1. Data Loading and Filtering ---
FILE_PATH = 'model/sms_data_corrected.csv'
try:
    df = pd.read_csv(FILE_PATH)
except FileNotFoundError:
    print(f"Hata: Dosya '{FILE_PATH}' bulunamadı.")
    exit()

# Gelişmiş Ön İşlemeyi Uygulama
df['TEXT'] = df['TEXT'].apply(preprocess_sms)

# Filtreleme
df = df[df['TEXT'].str.len() > 0]
valid_labels = ['ham', 'spam', 'smishing']
df = df[df['LABEL'].isin(valid_labels)]

# --- 2. Feature Engineering and Data Split ---
le = LabelEncoder()
df['LABEL_ENCODED'] = le.fit_transform(df['LABEL'])
target_names = le.classes_ # Değerlendirme raporu için sınıf isimleri

X = df['TEXT']
y = df['LABEL_ENCODED']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42, stratify=y
)

# TF-IDF Vektörleştirici
tfidf_vectorizer = TfidfVectorizer(
    max_features=5000,
    min_df=5,
    ngram_range=(1, 2)
)

X_train_tfidf = tfidf_vectorizer.fit_transform(X_train)
X_test_tfidf = tfidf_vectorizer.transform(X_test)


# --- 3. Model Eğitimi ve Optimizasyonu (SADECE LINEAR SVM) ---
f1_macro_scorer = make_scorer(f1_score, average='macro', zero_division=0)

# Model tanımı: class_weight='balanced' dengesizliği gidermek için KRİTİKTİR.
svc_model = SVC(random_state=42, kernel='linear', class_weight='balanced')
svc_param_grid = {
    'C': [0.1, 1, 10, 50] 
}

gs_svc = GridSearchCV(
    estimator=svc_model, 
    param_grid=svc_param_grid, 
    cv=5, 
    scoring=f1_macro_scorer, 
    verbose=0,
    n_jobs=-1
)

start_time_grid = time.time()
gs_svc.fit(X_train_tfidf, y_train)
training_time_total = time.time() - start_time_grid

# En iyi modeli al
best_svc = gs_svc.best_estimator_
best_C = best_svc.get_params()['C']

# --- 4. MODEL TESTİ VE SONUÇLARIN VERİLMESİ ---
print("\n" + "=" * 80)
print("--- LİNEAR SVM (OPTIMİZE EDİLMİŞ) TEST SONUÇLARI ---")
print(f"Toplam Eğitim ve Optimizasyon Süresi: {training_time_total:.2f} saniye")
print(f"En İyi C Parametresi: {best_C}")
print(f"5-Katmanlı Çapraz Doğrulama (CV) En İyi F1-Macro Skoru: {gs_svc.best_score_:.4f}")
print("=" * 80)

# Test Seti Tahmini
y_pred = best_svc.predict(X_test_tfidf)

# Test Metrikleri
accuracy = accuracy_score(y_test, y_pred)
report = classification_report(y_test, y_pred, target_names=target_names, zero_division=0)

print(f"Genel Doğruluk (Accuracy): {accuracy:.4f}\n")
print("Sınıflandırma Raporu (Precision, Recall, F1-Score):")
print(report)
print("=" * 80)


# --- 5. Model ve Vektörleştiricinin Kaydedilmesi ---
model_filename = 'model/sms_model.joblib'
vectorizer_filename = 'model/tfidf_vectorizer.joblib'

joblib.dump(best_svc, model_filename)
joblib.dump(tfidf_vectorizer, vectorizer_filename)

print("\n--- MODEL KALICILIĞI ---")
print(f"Nihai Linear SVM Modeli kaydedildi: {model_filename}")
print(f"TF-IDF Vektörleştirici kaydedildi: {vectorizer_filename}")