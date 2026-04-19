import json
import sys
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

# --- RISOLUZIONE DEL PATH ---
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir / "src"))

from src.parsers.wikipedia import WikipediaParser
from src.evaluator import token_level_eval

# --- FUNZIONE PER RIMUOVERE IL MARKDOWN (Come da Slide 29) ---
def remove_markdown(text: str) -> str:
    if not text:
        return ""
    # Rimuove grassetti e corsivi
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
    # Rimuove i link tenendo il testo [Testo](url) -> Testo
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Rimuove gli hashtag dei titoli
    text = re.sub(r'#+\s*', '', text)
    # Rimuove le barre e i trattini delle tabelle e liste
    text = re.sub(r'\||---|:---:|^-\s*', ' ', text, flags=re.MULTILINE)
    return text.strip()

def run_evaluation():
    # Carica il file del Gold Standard
    gs_file = Path(__file__).resolve().parent.parent / "gs_data" / "dominio_wikipedia_gs.json"
    
    if not gs_file.exists():
        print(f"❌ Errore: Il file {gs_file} non esiste. Controlla il percorso: {gs_file}")
        return

    with open(gs_file, "r", encoding="utf-8") as f:
        gold_standard = json.load(f)

    print("=" * 60)
    print(f"🚀 INIZIO VALUTAZIONE: Dominio Wikipedia ({len(gold_standard)} URL)")
    print("=" * 60)
    
    # Inizializza il parser senza parametri
    parser = WikipediaParser() 
    
    total_f1 = 0.0
    total_precision = 0.0
    total_recall = 0.0
    
    # Eseguiamo il test per ogni pagina salvata
    for i, entry in enumerate(gold_standard, 1):
        url = entry["url"]
        html_text = entry.get("html_text", "")
        gold_text = entry.get("gold_text", "")
        
        # Saltiamo l'estrazione se l'HTML è vuoto
        if not html_text or html_text == "INSERISCI_QUI_L_HTML_DA_CRAWL4AI":
            print(f"[{i}] ⚠️ SALTA: HTML mancante per {url}")
            continue

        # --- SIMULAZIONE PERFETTA DI CRAWL4AI (Estrazione offline) ---
        soup = BeautifulSoup(html_text, "html.parser")
        
        # 1. Distruggiamo i tag ignorati (identici alla tua CrawlerRunConfig)
        for tag in soup.find_all(['nav', 'footer', 'header', 'aside', 'figure']):
            tag.decompose()
            
        # 2. Distruggiamo le classi e le infobox
        junk_selectors = ".infobox, .infobox_v2, .mw-editsection, .navbox, #toc, .ambox, .hatnote, .thumb, .thumbinner, .gallery, .shortdescription, .tright, .tleft, .mw-halign-right, .mw-halign-left, .mw-halign-center, .reference"
        for junk in soup.select(junk_selectors):
            junk.decompose()
            
        # 3. Simuliamo la conversione Markdown dei titoli (per far funzionare le tue Regex!)
        for h2 in soup.find_all('h2'):
            h2.insert(0, "## ")
        for h3 in soup.find_all('h3'):
            h3.insert(0, "### ")

        # 4. Estraiamo il testo puro dal container principale
        content = soup.select_one("#mw-content-text") or soup
        raw_text = content.get_text(separator="\n")
        
        # --- PULIZIA E VALUTAZIONE ---
        # Passiamo il testo alla tua funzione reale di pulizia Regex
        parsed_md = parser.clean_wikipedia_markdown(raw_text)
        
        # Rimuoviamo il markdown per il calcolo dell'F1-Score
        clean_parsed = remove_markdown(parsed_md)
        clean_gold = remove_markdown(gold_text)
        
        # Calcoliamo le metriche
        metrics = token_level_eval(parsed_text=clean_parsed, gold_text=clean_gold)
        
        total_precision += metrics['precision']
        total_recall += metrics['recall']
        total_f1 += metrics['f1']
        
        print(f"[{i}] {url}")
        print(f"    ├─ Precision: {metrics['precision']:.4f}")
        print(f"    ├─ Recall:    {metrics['recall']:.4f}")
        print(f"    └─ F1-Score:  {metrics['f1']:.4f}")
        print("-" * 60)
        
    # --- STAMPA DEI RISULTATI FINALI ---
    valid_urls = len([e for e in gold_standard if e.get("html_text") and e.get("html_text") != "INSERISCI_QUI_L_HTML_DA_CRAWL4AI"])
    
    if valid_urls > 0:
        avg_precision = total_precision / valid_urls
        avg_recall = total_recall / valid_urls
        avg_f1 = total_f1 / valid_urls
        
        print("\n🏆 RISULTATI FINALI MEDI:")
        print(f"Precision Media: {avg_precision:.4f}")
        print(f"Recall Media:    {avg_recall:.4f}")
        print(f"F1-SCORE MEDIO:  {avg_f1:.4f}")
        
        print("\n📊 GIUDIZIO DEL PROFESSORE (Basato su F1-Score):")
        if avg_f1 > 0.8:
            print("🟢 OTTIMO! Il parser funziona benissimo.")
        elif avg_f1 > 0.6:
            print("🟡 MEDIO. Si può migliorare (controlla se estrai troppo rumore o perdi paragrafi).")
        else:
            print("🔴 SCARSO. C'è un problema logico nell'estrazione.")
    else:
        print("Nessun URL valido valutato.")

if __name__ == "__main__":
    run_evaluation()