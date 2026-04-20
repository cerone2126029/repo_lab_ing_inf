import json
import sys
import os
import re
import mistune
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import List, Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from bs4 import BeautifulSoup
import string

# Aggiungiamo 'src' al path per gli import dei moduli interni
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# =====================================================================
# 1. CLASSI PARSER (Monolite)
# =====================================================================
#=====BaseWebParser=====
class BaseWebParser:
    def __init__(self):

        # 1. Configurazione del browser comune a tutti i parser
        self.browser_config = BrowserConfig(
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"      
        )

        # 2. Configurazione base per il crawling.
        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            remove_overlay_elements=False,
            wait_for=5
        )


    async def parse_single(self, url: str) -> Dict[str, Any]:
        """
        FASE FINALE: Metodo usato dall'endpoint FastAPI per analizzare un solo URL.
        Avvia il crawler per una singola pagina e restituisce il dizionario.
        """
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(
                url=url,
                config=self.run_config
            )
            return self.extract_data(result)


    async def parse_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        FASE DI TESTING: Metodo usato dallo script locale per analizzare liste di URL
        (utile per confrontare con il Gold Standard).
        """
        results_list = []
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            crawl_results = await crawler.arun_many(
                urls=urls,
                config=self.run_config
            )


            for result in crawl_results:
                data = self.extract_data(result)
                results_list.append(data)


        return results_list


    def extract_data(self, result) -> Dict[str, Any]:
        """
        Metodo base per l'estrazione. Crea la struttura dati richiesta dall'esonero.
        Le classi figlie chiameranno super().extract_data(result) e applicheranno
        le rifiniture testuali su data["parsed_text"].
        """
        # Calcolo sicuro del dominio
        domain = urlparse(result.url).netloc if result.url else ""


        # Gestione del fallimento della richiesta
        if not result.success:
            return {
                "url": result.url,
                "domain": domain,
                "title": None,
                "html_text": "",
                "parsed_text": f"ERRORE: {result.error_message}"
            }


        # Estrazione sicura del titolo dai metadati
        title = result.metadata.get("title") if result.metadata else None


        # Estrazione del Markdown nativo generato da Crawl4AI
        # (Usa result.markdown o result.extracted_content a seconda della versione esatta che hai)
        raw_markdown = result.markdown if hasattr(result, 'markdown') and result.markdown else ""


        return {
            "url": result.url,
            "domain": domain,
            "title": title,
            "html_text": result.html or "",
            "parsed_text": raw_markdown.strip()
        }
    
#=====wikipedia=====
class WikipediaParser(BaseWebParser):
    
    # === PRE-COMPILAZIONE DELLE REGEX PER MASSIMIZZARE LE PRESTAZIONI ===
    
    _STOP_PATTERN = re.compile(
        r'^#+\s*(References?|Notes?|See also|External links?|Further reading|Bibliography|Citations?).*$',
        flags=re.IGNORECASE | re.MULTILINE
    )

    # Lista di tuple: (Pattern Regex Compilato, Stringa di Sostituzione)
    _CLEANING_RULES = [
        # 1. Distrugge i link delle note di Wikipedia
        (re.compile(r'\[[^\]]*\]\s*\([^\)]*#cite_note[^\)]*\)', flags=re.IGNORECASE), ''),
        # 2. Distrugge qualsiasi link vuoto rimasto
        (re.compile(r'\[\s*\]\([^\)]+\)'), ''),
        # 3. Elimina i [citation needed] e simili
        (re.compile(r'_?\[citation needed\]_?', flags=re.IGNORECASE), ''),
        (re.compile(r'\[Italian language\]', flags=re.IGNORECASE), ''),
        # 4. Elimina note puramente testuali (es: [18]) isolate
        (re.compile(r'(?<!\!)\[\d+\]'), ''),
        (re.compile(r'(?<!\!)\[\s*[a-z]\s*\]', flags=re.IGNORECASE), ''),
        # 5. Rimuove parentesi tonde vuote
        (re.compile(r'\(\s*\)'), ''),
        # 6. Didascalie residue e vecchi template
        (re.compile(r'^!.*$', flags=re.MULTILINE), ''),
        (re.compile(r'<sup[^>]*>.*?</sup>', flags=re.IGNORECASE | re.DOTALL), ''),
        (re.compile(r'\{\{\s*.*?\}\}', flags=re.DOTALL), ''),
        # 7. Frasi di servizio
        (re.compile(r'^\s*This article (is|needs|may).*?\.$', flags=re.MULTILINE | re.IGNORECASE), ''),
        (re.compile(r'^\s*This page (is|was).*?Wikipedia\.', flags=re.MULTILINE | re.IGNORECASE), ''),
        (re.compile(r'Coordinates?:\s*.*$', flags=re.MULTILINE | re.IGNORECASE), ''),
        # 8. Appiattisce i link validi rimasti `[Testo](url)` in puro `Testo`
        (re.compile(r'(?<!\!)\[([^\]]+)\]\([^\)]+\)'), r'\1'),
        # 9. Normalizzazione degli spazi e rimozione elenchi vuoti
        (re.compile(r'\n{3,}'), '\n\n'),
        (re.compile(r'^\s*[-*+]\s*$', flags=re.MULTILINE), '')
    ]

    def __init__(self):
        super().__init__()
       
        # Formattazione leggibile per i selettori CSS
        excluded_selectors = [
            ".infobox", ".infobox_v2", ".mw-editsection", ".navbox", "#toc", 
            ".ambox", ".hatnote", ".thumb", ".thumbinner", ".gallery", 
            ".shortdescription", ".tright", ".tleft", ".mw-halign-right", 
            ".mw-halign-left", ".mw-halign-center", ".reference"
        ]

        self.run_config = CrawlerRunConfig(
            magic=True,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            css_selector="#mw-content-text", 
            excluded_tags=["nav", "footer", "header", "aside", "figure"],
            excluded_selector=", ".join(excluded_selectors)
        )

    def extract_data(self, result) -> Dict[str, Any]:
        data = super().extract_data(result)
        
        self._extract_fallback_title(data)

        parsed_text = data.get("parsed_text", "")
        if result.success and parsed_text and not parsed_text.startswith("ERRORE"):
            data["parsed_text"] = self.clean_wikipedia_markdown(parsed_text)
       
        return data

    def _extract_fallback_title(self, data: Dict[str, Any]) -> None:
        """Recupera il titolo dall'URL in caso di fallimento dei selettori CSS."""
        url = data.get("url", "")
        if not data.get("title") and "/wiki/" in url:
            raw_title = url.split("/wiki/")[-1]
            data["title"] = unquote(raw_title).replace("_", " ")

    def clean_wikipedia_markdown(self, text: str) -> str:
        if not text:
            return ""

        # 1. Applica la ghigliottina finale
        match = self._STOP_PATTERN.search(text)
        if match:
            text = text[:match.start()]

        # 2. Applica sequenzialmente tutte le regole di pulizia
        for pattern, replacement in self._CLEANING_RULES:
            text = pattern.sub(replacement, text)
       
        return text.strip()
    
#=====scaruffi=====
class ScaruffiParser(BaseWebParser):

    def __init__(self):
        super().__init__()
        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            remove_overlay_elements=False
        )

    def extract_data(self, result) -> Dict[str, Any]:
        data = super().extract_data(result)
        if result.success and result.html:
            data["parsed_text"] = self.extract_scaruffi_text(result.html)
        return data
    
    def extract_scaruffi_text(self, html: str) -> str:
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")
        body = soup.find('body')
        
        if not body:
            return "Nessun tag <body> trovato."

        # 1. ELIMINAZIONE DEL RUMORE INVISIBILE E STRUTTURALE
        for tag in body.find_all(['script', 'style', 'nav', 'iframe', 'form']):
            tag.decompose()

        # 2. EURISTICA DELLA DENSITA' DEI LINK (Per eliminare le discografie e i menù grandi)
        for container in body.find_all(['table', 'ul']):
            links = container.find_all('a')
            if not links:
                continue
            
            text_in_links = sum(len(a.get_text(strip=True)) for a in links)
            total_text = len(container.get_text(strip=True))
            
            if total_text > 0 and (text_in_links / total_text) > 0.40:
                container.decompose()

        # 3. ESTRAZIONE DEL TESTO
        raw_text = body.get_text(separator="\n", strip=True)

        # 4. LA BLACKLIST (Sterminatore di Boilerplate di Scaruffi)
        # Un elenco di pattern Regex per disintegrare le frasi fastidiose ovunque siano
        spazzatura = [
            # --- Blocchi Multi-riga (Copyright) ---
            # Usiamo [\s\S]*? che cattura anche gli a capo in modo sicuro
            r'TM[\s\S]*?Copyright[\s\S]*?All\s+rights\s+reserved\.?',
            r'Copyright[\s\S]*?(?:Piero|Paolo|P\.)?\s*Scaruffi[\s\S]*?All\s+rights\s+reserved\.?',
            r'All\s+photographs\s+are\s+property\s+of[\s\S]*?provided\s+them',

            # --- CECCHINI DI RIGA (Colpiscono solo i rimasugli orfani) ---
            # ^ = inizio riga, $ = fine riga, [ \t]* = eventuali spazi orizzontali
            r'^[ \t]*(?:by[ \t]+)?(?:Piero|Paolo|P\.)?[ \t]*Scaruffi[ \t]*$',
            r'^[ \t]*(?:and|the|by)[ \t]*$',
            r'^[ \t]*[\|\.,\(\)\-][ \t]*$',
            r'^[ \t]*""?[ \t]*$',

            # --- Frasi esatte e Menù ---
            r'What\s+is\s+unique\s+about\s+this\s+music\s+database\??',    
            r'Terms\s+of\s+use',
            r'A\s+history\s+of\s+Jazz\s+Music',
            r'See\s+also\s+the',
            r'The\s+History\s+of\s+Rock\s+Music',
            r'The\s+History\s+of\s+Pop\s+Music',
            r'Main\s+jazz\s+page',
            r'Jazz\s+musicians?',
            r'To\s+purchase\s+the\s+book',
            r'\(?These\s+are\s+excerpts\s+from\s+my\s+book\)?',
            r'"?A\s+History\s+of\s+Jazz\s+Music"?',
            r'Next\s+chapter',
            r'Back\s+to\s+the\s+Index',
            r'Back\s+to\s+the\s+[A-Za-z\s]+',
            r'Links\s+to\s+other\s+sites',
            
            r'\(\s*(?:[Cc]lick|[Cc]licca|Translation|Translated|Tradotto)[^)]+\)',
            r'\(\s*Copyright[^)]+\)',
            
            # --- INCOLLA QUI LA NUOVA REGEX ---
            r'(?im)^[ \t]*(by|and|the|piero\s+scaruffi|paolo\s+scaruffi|all\s+rights\s+reserved\.?|[\(\)\"\|\.,\-]+)[ \t]*$',
            r'(?im)^[ \t]*(?:(?:by\s+)?(?:piero|paolo|p\.)\s+scaruffi|by|and|the|all\s+rights\s+reserved\.?|[\(\)\"\|\.,\-]+)[ \t]*$'
        ]

        # Applichiamo la blacklist: sostituiamo ogni frase trovata con il vuoto ("")
        for pattern in spazzatura:
            raw_text = re.sub(pattern, '', raw_text, flags=re.IGNORECASE)

        # 5. PULIZIA FINALE E IMPAGINAZIONE
        clean_lines = []
        for line in raw_text.split('\n'):
            line = line.strip()
            
            # Ignoriamo le righe vuote e i "rimasugli" grafici come la barra |
            if line and line != "|":
                clean_lines.append(line)

        final_text = "\n\n".join(clean_lines)

        return final_text
    
# =====================================================================
# 2. SISTEMA DI VALUTAZIONE
# =====================================================================
def tokenize(text: str) -> set:
    """Pulisce il testo e lo trasforma in un set di token (parole)."""
    if not text:
        return set()
    
    # Crea una tabella di traduzione per rimuovere la punteggiatura
    translator = str.maketrans('', '', string.punctuation)
    
    # Mette in minuscolo e rimuove la punteggiatura
    clean_text = text.lower().translate(translator)
    
    # Divide il testo in parole. Usiamo set() per avere un insieme univoco di token
    return set(clean_text.split())

def token_level_eval(parsed_text: str, gold_text: str) -> dict:
    """Calcola Precision, Recall e F1-Score tra due testi."""
    parsed_tokens = tokenize(parsed_text)
    gold_tokens = tokenize(gold_text)

    # Gestione dei casi limite (testi vuoti)
    if not parsed_tokens and not gold_tokens:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not parsed_tokens or not gold_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    # True Positives: parole presenti in entrambi i set
    common_tokens = parsed_tokens.intersection(gold_tokens)
    tp = len(common_tokens)

    # Precision = Parole Corrette / Totale Parole Estratte
    precision = tp / len(parsed_tokens)

    # Recall = Parole Corrette / Totale Parole nel Gold Standard
    recall = tp / len(gold_tokens)

    # F1-Score = Media armonica tra Precision e Recall
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4)
    }
# =====================================================================
# 3. CONFIGURAZIONE E MODELLI (PYDANTIC)
# =====================================================================

app = FastAPI(
    title="Web Scraper & Evaluator API",
    description="API ufficiale per l'esonero di Laboratorio di Ingegneria Informatica",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GS_DIR = BASE_DIR / "gs_data"

SUPPORTED_DOMAINS = [
    "en.wikipedia.org", 
    "www.scaruffi.com"
]

class EvaluateRequest(BaseModel):
    parsed_text: str
    gold_text: str

# NUOVO MODELLO PER POST /parse (Slide 2)
class ParseRequest(BaseModel):
    url: str
    html_text: str

# =====================================================================
# 4. UTILITY FUNCTIONS
# =====================================================================

def get_domain_config(url_or_domain: str, is_url: bool = True):
    domain = urlparse(url_or_domain).netloc.lower() if is_url else url_or_domain.lower()
    
    if "wikipedia.org" in domain:
        return "wikipedia", "dominio_wikipedia_gs.json"
    elif "scaruffi.com" in domain:
        return "scaruffi", "dominio_scaruffi_gs.json"
    return None, None

def remove_markdown(md: str) -> str:
    """
    Rimuove il Markdown da una stringa, restituendo solo il testo pulito.
    Usa la libreria mistune per convertire il Markdown in HTML, poi BeautifulSoup per estrarre solo il testo.
    """
    if not md: 
        return ""
        
    html = mistune.html(md)
    soup = BeautifulSoup(html, "html.parser")
    
    # rimuove i tag lasciando il testo esattamente in-place (nessun separatore aggiunto, mantiene punteggiatura)
    for tag in soup.find_all(True):
        tag.unwrap()
        
    text = re.sub(r'[ \t]+', ' ', str(soup))    # collassa spazi orizzontali (non \n)
    text = re.sub(r'\n+', '\n', text)           # collassa nuove linee multiple in una sola
    
    return text.strip()

# =====================================================================
# 5. ENDPOINT API
# =====================================================================

@app.get("/domains")
def get_domains():
    return {"domains": SUPPORTED_DOMAINS}

@app.get("/parse")
async def get_parse(url: str = Query(..., description="URL da analizzare")):
    domain_type, _ = get_domain_config(url)
    if not domain_type:
        raise HTTPException(status_code=400, detail="Dominio non supportato.")

    parser = WikipediaParser() if domain_type == "wikipedia" else ScaruffiParser()
    
    try:
        results = await parser.parse_batch(urls=[url])
        if not results:
            raise HTTPException(status_code=404, detail="Impossibile recuperare l'URL.")
        
        data = results[0]
        if "ERRORE:" in str(data.get("parsed_text", "")):
            raise HTTPException(status_code=400, detail=data["parsed_text"])

        return {
            "url": data.get("url", url),
            "domain": urlparse(url).netloc,
            "title": data.get("title", ""),
            "html_text": data.get("html_text", ""),
            "parsed_text": data.get("parsed_text", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# NUOVO ENDPOINT: POST /parse (Aggiornato con il trucco "raw:" di Crawl4AI)
@app.post("/parse")
async def post_parse(request: ParseRequest):
    """Esegue il parser per un documento da html diretto usando il prefisso raw:"""
    domain_type, _ = get_domain_config(request.url)
    if not domain_type:
        raise HTTPException(status_code=400, detail="Dominio non supportato.")

    # Seleziona il parser corretto in base all'URL passato
    parser = WikipediaParser() if domain_type == "wikipedia" else ScaruffiParser()
    
    # IL TRUCCO DELLA SLIDE: Aggiungiamo "raw:" davanti all'HTML incollato
    fake_url_for_crawler = f"raw:{request.html_text}"

    try:
        # Chiamiamo il parser esattamente come faremmo online!
        results = await parser.parse_batch(urls=[fake_url_for_crawler])
        
        if not results:
            raise HTTPException(status_code=500, detail="Il crawler ha fallito l'estrazione raw.")
            
        data = results[0]

        # Estrazione titolo di emergenza se Crawl4AI restituisce null
        titolo = data.get("title")
        if not titolo:
            if domain_type == "wikipedia" and "/wiki/" in request.url:
                titolo = unquote(request.url.split("/wiki/")[-1]).replace("_", " ")
            else:
                titolo = ""

        # Restituiamo il JSON esattamente come chiede la specifica
        return {
            "url": request.url,  # Usiamo l'URL vero, non quello con "raw:"
            "domain": urlparse(request.url).netloc,
            "title": titolo,
            "html_text": request.html_text,
            "parsed_text": data.get("parsed_text", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gold_standard")
def get_gs_entry(url: str = Query(..., description="URL di cui cercare il GS")):
    _, gs_file = get_domain_config(url)
    if not gs_file:
        raise HTTPException(status_code=400, detail="Dominio non supportato.")
    
    path = GS_DIR / gs_file
    if not path.exists():
        raise HTTPException(status_code=404, detail="File GS non trovato.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for entry in data:
        if entry["url"] == url:
            return {
                "url": entry["url"],
                "domain": urlparse(url).netloc,
                "title": entry.get("title", ""),
                "html_text": entry.get("html_text", ""),
                "gold_text": entry.get("gold_text", "")
            }
    raise HTTPException(status_code=404, detail="URL non presente nel Gold Standard.")

@app.get("/full_gold_standard")
def get_full_gs(domain: str = Query(..., description="Dominio completo")):
    _, gs_file = get_domain_config(domain, is_url=False)
    if not gs_file:
        raise HTTPException(status_code=400, detail="Dominio non supportato.")

    path = GS_DIR / gs_file
    with open(path, "r", encoding="utf-8") as f:
        gs_entries = json.load(f)

    return {
        "gold_standard": [
            {
                "url": e["url"],
                "domain": domain,
                "title": e.get("title", ""),
                "html_text": e.get("html_text", ""),
                "gold_text": e.get("gold_text", "")
            } for e in gs_entries
        ]
    }

@app.post("/evaluate")
def evaluate(request: EvaluateRequest):
    clean_p = remove_markdown(request.parsed_text)
    clean_g = remove_markdown(request.gold_text)
    metrics = token_level_eval(clean_p, clean_g)
    return {"token_level_eval": metrics, "x_eval": {}}

@app.get("/full_gs_eval")
def full_gs_eval(domain: str = Query(..., description="Dominio per evaluation totale")):
    domain_type, gs_file = get_domain_config(domain, is_url=False)
    if not domain_type:
        raise HTTPException(status_code=400, detail="Dominio non supportato.")

    path = GS_DIR / gs_file
    with open(path, "r", encoding="utf-8") as f:
        gs_entries = json.load(f)

    parser = WikipediaParser() if domain_type == "wikipedia" else ScaruffiParser()
    total_metrics = {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    count = 0

    for entry in gs_entries:
        html = entry.get("html_text", "")
        gold = entry.get("gold_text", "")
        if not html or html == "INSERISCI_QUI_L_HTML_DA_CRAWL4AI" or not gold: continue

        if domain_type == "wikipedia":
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all(['nav', 'footer', 'header', 'aside', 'figure']): tag.decompose()
            for junk in soup.select(".infobox, .infobox_v2, .mw-editsection, .navbox, #toc, .ambox, .hatnote, .thumb, .thumbinner, .gallery, .shortdescription, .tright, .tleft, .mw-halign-right, .mw-halign-left, .mw-halign-center, .reference"): junk.decompose()
            for h2 in soup.find_all('h2'): h2.insert(0, "## ")
            for h3 in soup.find_all('h3'): h3.insert(0, "### ")
            content = soup.select_one("#mw-content-text") or soup
            parsed = parser.clean_wikipedia_markdown(content.get_text(separator="\n"))
        else:
            parsed = parser.extract_scaruffi_text(html)

        m = token_level_eval(remove_markdown(parsed), remove_markdown(gold))
        for k in total_metrics: total_metrics[k] += m[k]
        count += 1

    if count == 0: return {"token_level_eval": {"precision": 0, "recall": 0, "f1": 0}, "x_eval": {}}
    
    return {
        "token_level_eval": {k: round(v/count, 4) for k, v in total_metrics.items()},
        "x_eval": {}
    }

if __name__ == "__main__":
    print("🚀 Server in ascolto sulla porta 8003...")
    uvicorn.run("server:app", host="0.0.0.0", port=8003, reload=True)