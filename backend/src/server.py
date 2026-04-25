import json
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Rimosso BeautifulSoup: il server fa solo il server!
from parsers.wikipediaparser import WikipediaParser
from parsers.scaruffiparser import ScaruffiParser
from parsers.travelstategov import TravelStateGov 
from evaluator import token_level_eval


BASE_DIR = Path(__file__).resolve().parent.parent.parent
GS_DIR = BASE_DIR / "gs_data"
DOMAINS_FILE = BASE_DIR / "domains.json"

class ParseRequest(BaseModel):
    url: str
    html_text: str

class EvaluateRequest(BaseModel):
    parsed_text: str
    gold_text: str

def load_supported_domains():
    if DOMAINS_FILE.exists():
        with open(DOMAINS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return ["en.wikipedia.org", "it.wikipedia.org", "www.scaruffi.com"]

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

app = FastAPI(
    title="Web Scraper & Evaluator API",
    description="API ufficiale per l'esonero di Laboratorio di Ingegneria Informatica",
    version="1.0.0"
)

def get_parser_instance(domain_type: str):
    """Factory helper per instanziare il parser corretto"""
    if domain_type == "wikipedia": return WikipediaParser()
    if domain_type == "scaruffi": return ScaruffiParser()
    if domain_type == "travelstategov": return TravelStateGov()
    raise HTTPException(status_code=400, detail="Parser non implementato per questo dominio.")


@app.get("/domains")
def get_domains():
    return {"domains": SUPPORTED_DOMAINS}

@app.get("/parse")
async def get_parse(url: str = Query(..., description="URL da analizzare")):
    domain_type, _ = get_domain_config(url)
    if not domain_type: raise HTTPException(status_code=400, detail="Dominio non supportato.")
    
    parser = get_parser_instance(domain_type)
    
    try:
        results = await parser.parse_batch(urls=[url])
        if not results: raise HTTPException(status_code=404, detail="Impossibile recuperare l'URL.")
        
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

@app.post("/parse")
async def post_parse(request: ParseRequest):
    domain_type, _ = get_domain_config(request.url)
    if not domain_type: raise HTTPException(status_code=400, detail="Dominio non supportato.")

    parser = get_parser_instance(domain_type)
    fake_url_for_crawler = f"raw:{request.html_text}"

    try:
        results = await parser.parse_batch(urls=[fake_url_for_crawler])
        if not results: raise HTTPException(status_code=500, detail="Il crawler ha fallito l'estrazione raw.")
            
        data = results[0]
        titolo = data.get("title", "")
        if not titolo and hasattr(parser, "extract_fallback_title"):
            titolo = parser.extract_fallback_title(request.url) or ""

        return {
            "url": request.url, 
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
    if not gs_file: raise HTTPException(status_code=400, detail="Dominio non supportato.")
    
    path = GS_DIR / gs_file
    if not path.exists(): raise HTTPException(status_code=404, detail="File GS non trovato.")

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
    if not gs_file: raise HTTPException(status_code=400, detail="Dominio non supportato.")

    path = GS_DIR / gs_file
    with open(path, "r", encoding="utf-8") as f: gs_entries = json.load(f)

    return {"gold_standard": [{"url": e["url"], "domain": domain, "title": e.get("title", ""), "html_text": e.get("html_text", ""), "gold_text": e.get("gold_text", "")} for e in gs_entries]}

@app.post("/evaluate")
def evaluate(request: EvaluateRequest):
    metrics = token_level_eval(request.parsed_text, request.gold_text)
    return {"token_level_eval": metrics, "x_eval": {}}

@app.get("/full_gs_eval")
def full_gs_eval(domain: str = Query(..., description="Dominio per evaluation totale")):
    domain_type, gs_file = get_domain_config(domain, is_url=False)
    if not domain_type: raise HTTPException(status_code=400, detail="Dominio non supportato.")

    path = GS_DIR / gs_file
    with open(path, "r", encoding="utf-8") as f: gs_entries = json.load(f)

    parser = get_parser_instance(domain_type)
    total_metrics = {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    count = 0

    for entry in gs_entries:
        html = entry.get("html_text", "")
        gold = entry.get("gold_text", "")
        if not html or html == "INSERISCI_QUI_L_HTML_DA_CRAWL4AI" or not gold: continue

        # ECCO LA MAGIA: Il server delega il parsing dell'HTML al parser corretto
        parsed = parser.parse_offline_html(html)
            
        m = token_level_eval(parsed, gold)
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