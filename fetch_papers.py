import json
import urllib.request
import urllib.parse
import os
from datetime import datetime, timedelta

# ---------- НАСТРОЙКИ ----------
DAYS_BACK = 30          # за сколько дней назад искать (30 = за последний месяц)
MAX_RESULTS = 100       # максимум статей за один запуск

# Ключевые слова: если хотя бы одно встретилось в названии или аннотации — статья попадает в список
KEYWORDS = [
    "театр", "микросоциология", "социология повседневности",
    "качественная методология", "качественная социология",
    "артист театра", "актёр театра", "эмоциональный труд",
    "theatre", "theater", "microsociology", "sociology of everyday life",
    "qualitative methodology", "qualitative sociology",
    "theatre actor", "theater actor", "stage actor",
    "emotional labour", "emotional labor"
]

OUTPUT_FILE = "papers.json"
# --------------------------------

def load_journals():
    with open("journals.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    issns = []
    for group in data.values():
        for j in group:
            issns.append(j["issn"])
    return issns

def matches_keywords(text):
    if not text:
        return False
    low = text.lower()
    return any(kw.lower() in low for kw in KEYWORDS)

def fetch_from_crossref(issn, from_date):
    base = "https://api.crossref.org/works"
    params = {
        "filter": f"issn:{issn},from-pub-date:{from_date}",
        "rows": MAX_RESULTS,
        "select": "DOI,title,author,container-title,abstract,URL,published",
        "mailto": "your-email@example.com"  # Crossref просит указать email, можно оставить так
    }
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "SociologyPapersBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("message", {}).get("items", [])
    except Exception as e:
        print(f"Ошибка при запросе ISSN {issn}: {e}")
        return []

def main():
    issns = load_journals()
    from_date = (datetime.utcnow() - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")

    all_papers = []
    seen_dois = set()

    for issn in issns:
        items = fetch_from_crossref(issn, from_date)
        for item in items:
            doi = item.get("DOI", "")
            if doi in seen_dois:
                continue
            title = " ".join(item.get("title", [""]))
            abstract = item.get("abstract", "") or ""
            # убираем HTML-теги из аннотации, если они есть
            import re
            abstract = re.sub(r"<[^>]+>", "", abstract).strip()

            if not matches_keywords(title + " " + abstract):
                continue

            authors = []
            for a in item.get("author", []):
                name = (a.get("given", "") + " " + a.get("family", "")).strip()
                if name:
                    authors.append(name)

            journal = " ".join(item.get("container-title", [""]))
            published = item.get("published", {}).get("date-parts", [[""]])[0]
            pub_str = "-".join(str(x) for x in published if x)

            all_papers.append({
                "title": title,
                "authors": ", ".join(authors) if authors else "Автор не указан",
                "journal": journal,
                "abstract": abstract if abstract else "Аннотация отсутствует",
                "url": item.get("URL", f"https://doi.org/{doi}"),
                "published": pub_str
            })
            seen_dois.add(doi)

    # сортируем по дате (новые сверху)
    all_papers.sort(key=lambda p: p["published"], reverse=True)

    # сохраняем в papers.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_papers, f, ensure_ascii=False, indent=2)

    print(f"Найдено статей: {len(all_papers)}")

if __name__ == "__main__":
    main()
