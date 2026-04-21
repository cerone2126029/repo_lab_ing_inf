import json
import sys
import os
from pathlib import Path
from urllib.parse import urlparse, unquote
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from bs4 import BeautifulSoup
from parsers.wikipediaparser import WikipediaParser
from parsers.scaruffiparser import ScaruffiParser
from parsers.travelstategov import TravelStateGov # <-- Assicurati che la classe si chiami esattamente così nel tuo file!
from evaluator import token_level_eval, remove_markdown

# Aggiungiamo 'src' al path per gli import dei moduli interni
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GS_DIR = BASE_DIR / "gs_data"
DOMAINS_FILE = BASE_DIR / "domains.json"

class ParseRequest(BaseModel):
    """Modello per la richiesta POST /parse"""
    url: str
    html_text: str

class EvaluateRequest(BaseModel):
    """Modello per la richiesta POST /evaluate"""
    parsed_text: str
    gold_text: str


# =====================================================================
# 4. UTILITY FUNCTIONS
# =====================================================================
def load_supported_domains():
    """Legge la lista dei domini dal file JSON nella root del progetto."""
    if DOMAINS_FILE.exists():
        with open(DOMAINS_FILE, "r", encoding="utf-8") as f:
            # Carica la lista dal file JSON
            return json.load(f)
    # Fallback di emergenza se il file non esiste ancora
    return ["en.wikipedia.org", "it.wikipedia.org", "www.scaruffi.com"]

# DEFINIZIONE DELLA VARIABILE MANCANTE
SUPPORTED_DOMAINS = load_supported_domains()

def get_domain_config(url_or_domain: str, is_url: bool = True):
    domain = urlparse(url_or_domain).netloc.lower() if is_url else url_or_domain.lower()
    
    if "wikipedia.org" in domain:
        return "wikipedia", "dominio_wikipedia_gs.json"
    elif "scaruffi.com" in domain:
        return "scaruffi", "dominio_scaruffi_gs.json"
    elif "travel.state.gov" in domain:
        return "travelstategov", "dominio_travelstategov_gs.json"
    return None, None

# =====================================================================
# 5. ENDPOINT API
# =====================================================================
app = FastAPI(
    title="Web Scraper & Evaluator API",
    description="API ufficiale per l'esonero di Laboratorio di Ingegneria Informatica",
    version="1.0.0"
)

@app.get("/domains")
def get_domains():
    return {"domains": SUPPORTED_DOMAINS}

@app.get("/parse")
async def get_parse(url: str = Query(..., description="URL da analizzare")):
    domain_type, _ = get_domain_config(url)
    if not domain_type:
        raise HTTPException(status_code=400, detail="Dominio non supportato.")

    if domain_type == "wikipedia":
        parser = WikipediaParser()
    elif domain_type == "scaruffi":
        parser = ScaruffiParser()
    elif domain_type == "travelstategov":
        parser = TravelStateGov()
    else:
        raise HTTPException(status_code=400, detail="Parser non implementato per questo dominio.")
    
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
    if domain_type == "wikipedia":
        parser = WikipediaParser()
    elif domain_type == "scaruffi":
        parser = ScaruffiParser()
    elif domain_type == "travelstategov":
        parser = TravelStateGov()
    else:
        raise HTTPException(status_code=400, detail="Parser non implementato per questo dominio.")
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

    if domain_type == "wikipedia":
        parser = WikipediaParser()
    elif domain_type == "scaruffi":
        parser = ScaruffiParser()
    elif domain_type == "travelstategov":
        parser = TravelStateGov()
    else:
        raise HTTPException(status_code=400, detail="Parser non implementato per questo dominio.")

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
        elif domain_type=="scaruffi":
            parsed = parser.extract_scaruffi_text(html)
        elif domain_type == "travelstategov":
            # Per TravelStateGov, estraiamo il testo dal container principale dell'HTML
            soup = BeautifulSoup(html, "html.parser")
            content = soup.select_one(".tsg-rwd-main-copy-body-frame, .post-content") or soup
            raw_text = content.get_text(separator="\n")
            # E poi applichiamo le tue Regex di pulizia!
            parsed = parser.clean_travelstategov_markdown(raw_text)
            
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