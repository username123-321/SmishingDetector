# feature_extraction.py
import re

# Patterns
URL_PATTERN = r"(https?://[^\s]+|www\.[^\s]+)"
PHONE_PATTERN = r"\+?\d[\d\s().-]{6,}\d"
DOMAIN_PATTERN = r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b"
EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"

# Functions
def detect_urls(text):
    return re.findall(URL_PATTERN, text)

def detect_emails(text):
    return re.findall(EMAIL_PATTERN, text)

def detect_phone_numbers(text):
    # returns raw matches; may include separators
    return re.findall(PHONE_PATTERN, text)

def detect_domains(text):
    # remove full URLs & emails so we don't double-detect
    t = re.sub(URL_PATTERN, " ", text)
    t = re.sub(EMAIL_PATTERN, " ", t)
    return re.findall(DOMAIN_PATTERN, t)