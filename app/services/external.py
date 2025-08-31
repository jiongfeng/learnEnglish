import os, requests
from urllib.parse import quote_plus

DICT_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
LIBRETRANSLATE_URL = os.getenv('LIBRETRANSLATE_URL', '').strip()

def fetch_dictionary(word: str):
    try:
        r = requests.get(DICT_API.format(word), timeout=10)
        if r.status_code != 200:
            return {}
        data = r.json()
        if not isinstance(data, list) or not data:
            return {}
        entry = data[0]
        phonetic = entry.get('phonetic') or ''
        audio = ''
        for ph in entry.get('phonetics', []) or []:
            if ph.get('audio'):
                audio = ph['audio']
                if not phonetic:
                    phonetic = ph.get('text', '')
                break
        meaning_text = ''
        example = ''
        for m in entry.get('meanings', []) or []:
            defs = m.get('definitions') or []
            if defs:
                meaning_text = defs[0].get('definition', '')
                example = defs[0].get('example', '') or ''
                if meaning_text:
                    break
        return {"definition_en": meaning_text, "example_en": example, "phonetic": phonetic, "audio": audio}
    except Exception:
        return {}

def translate_to_zh(text: str) -> str:
    text = (text or '').strip()
    if not text:
        return ''

    # 1) 优先：LibreTranslate（如果配置了）
    if LIBRETRANSLATE_URL:
        try:
            url = LIBRETRANSLATE_URL.rstrip('/') + '/translate'
            payload = {"q": text, "source": "en", "target": "zh", "format": "text"}
            r = requests.post(url, json=payload, timeout=10)
            if r.status_code == 200:
                out = r.json()
                zh = (out.get('translatedText') or '').strip()
                if zh:
                    return zh
        except Exception:
            pass  # 继续尝试兜底

    # 2) 兜底：MyMemory 免费接口（无需 Key，有速率限制）
    try:
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": "en|zh-CN"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            zh = (data.get("responseData", {}).get("translatedText") or '').strip()
            if zh:
                return zh
    except Exception:
        pass

    # 3) 全部失败：返回英文（占位）
    return text


def _pixabay_image(word: str) -> str:
    key = os.getenv('PIXABAY_KEY', '52058123-c0d27e4b82768ef0480e6d9e1').strip()
    if not key:
        return ''
    try:
        params = {'key': key, 'q': word, 'image_type': 'photo', 'per_page': 3, 'safesearch': 'true'}
        r = requests.get('https://pixabay.com/api/', params=params, timeout=10)
        if r.status_code == 200:
            hits = r.json().get('hits', [])
            if hits:
                return hits[0].get('webformatURL') or hits[0].get('previewURL') or ''
        return ''
    except Exception:
        return ''

def fetch_image(word: str) -> str:
    # 1) 先试 Pixabay（若配置了 KEY 并且有结果）
    img = _pixabay_image(word)
    if img:
        return img
    # 2) 回退：Unsplash Source（无需 Key，构造直链）
    #    该端点每次请求可能返回不同图片，但 URL 可直接作为 <img src> 使用
    return f"https://source.unsplash.com/featured/?{quote_plus(word)}"
