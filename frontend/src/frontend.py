import os
import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Configurazione della cartella per i template HTML
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Indirizzo del backend preso dalle variabili d'ambiente (impostato nel docker-compose.yaml)
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8003")

async def fetch_gold_standard_urls():
    """Recupera la lista dinamica degli URL del Gold Standard dal backend."""
    gs_urls = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            dom_resp = await client.get(f"{BACKEND_URL}/domains")
            if dom_resp.status_code == 200:
                domains = dom_resp.json().get("domains", [])
                for dom in domains:
                    gs_resp = await client.get(f"{BACKEND_URL}/full_gold_standard", params={"domain": dom})
                    if gs_resp.status_code == 200:
                        items = gs_resp.json().get("gold_standard", [])
                        for item in items:
                            if "url" in item:
                                gs_urls.append(item["url"])
    except Exception as e:
        print(f"Errore durante il recupero dei domini: {e}")
    return sorted(list(set(gs_urls)))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renderizza la pagina iniziale popolando la tendina del Gold Standard."""
    gs_urls = await fetch_gold_standard_urls()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "gold_standard_urls": gs_urls,
        "risultato": None
    })

@app.post("/analizza", response_class=HTMLResponse)
async def analizza(request: Request, url: str = Form(...)):
    """Gestisce il click sul bottone e interroga il backend per parser ed evaluator."""
    gs_urls = await fetch_gold_standard_urls()
    risultato = {
        "url": url,
        "errore": None,
        "html_text": "",
        "parsed_text": "",
        "gold_text": None,
        "metrica": None
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Chiamata al parser
            parse_resp = await client.get(f"{BACKEND_URL}/parse", params={"url": url})
            if parse_resp.status_code != 200:
                # Estrae il dettaglio dell'errore restituito dal tuo server.py
                try:
                    err_detail = parse_resp.json().get("detail", f"Errore {parse_resp.status_code}")
                except:
                    err_detail = f"Errore {parse_resp.status_code}"
                risultato["errore"] = f"Errore dal parser: {err_detail}"
            else:
                parse_data = parse_resp.json()
                risultato["html_text"] = parse_data.get("html_text", "")
                risultato["parsed_text"] = parse_data.get("parsed_text", "")
                
                # 2. Verifica se l'URL è presente nel Gold Standard
                gs_resp = await client.get(f"{BACKEND_URL}/gold_standard", params={"url": url})
                
                if gs_resp.status_code == 200:
                    gold_text = gs_resp.json().get("gold_text", "")
                    risultato["gold_text"] = gold_text
                    
                    # 3. Se abbiamo il Gold Standard, lanciamo la valutazione
                    eval_resp = await client.post(f"{BACKEND_URL}/evaluate", json={
                        "parsed_text": risultato["parsed_text"],
                        "gold_text": gold_text
                    })
                    if eval_resp.status_code == 200:
                        risultato["metrica"] = eval_resp.json().get("token_level_eval")
                        
    except Exception as e:
        risultato["errore"] = f"Impossibile comunicare con il backend: {str(e)}"

    # Ricarica la pagina passando i risultati
    return templates.TemplateResponse("index.html", {
        "request": request,
        "gold_standard_urls": gs_urls,
        "risultato": risultato
    })