import json
from pathlib import Path

# Adatta questi import in base all'esatta posizione dei tuoi file
from src.parsers.wikipedia import WikipediaParser
from src.evaluator import token_level_eval

def run_evaluation():
    # 1. Carica il file del Gold Standard
    gs_file = Path("gs_data/dominio_wikipedia_gs.json")
    
    if not gs_file.exists():
        print(f"❌ Errore: Il file {gs_file} non esiste.")
        return

    with open(gs_file, "r", encoding="utf-8") as f:
        gold_standard = json.load(f)

    print("=" * 60)
    print(f"🚀 INIZIO VALUTAZIONE: Dominio Wikipedia ({len(gold_standard)} URL)")
    print("=" * 60)
    
    # 2. Inizializza il parser (passiamo una lista vuota perché non faremo crawling)
    parser = WikipediaParser(urls=[]) 
    
    total_f1 = 0.0
    total_precision = 0.0
    total_recall = 0.0
    
    # 3. Eseguiamo il test per ogni pagina salvata
    for i, entry in enumerate(gold_standard, 1):
        url = entry["url"]
        html_text = entry["html_text"]
        gold_text = entry["gold_text"]
        
        # Saltiamo l'estrazione se l'HTML è vuoto (es. se hai dimenticato di compilarlo)
        if not html_text or html_text == "INSERISCI_QUI_L_HTML_DA_CRAWL4AI":
            print(f"[{i}] ⚠️ SALTA: HTML mancante per {url}")
            continue

        # Usiamo il parser per estrarre il testo dall'HTML salvato
        parsed_text = parser.extract_wikipedia_text(html_text)
        
        # Calcoliamo le metriche
        metrics = token_level_eval(parsed_text=parsed_text, gold_text=gold_text)
        
        total_precision += metrics['precision']
        total_recall += metrics['recall']
        total_f1 += metrics['f1']
        
        print(f"[{i}] {url}")
        print(f"    ├─ Precision: {metrics['precision']:.4f} (Quanto del testo estratto è corretto?)")
        print(f"    ├─ Recall:    {metrics['recall']:.4f} (Quanto del Gold Standard è stato trovato?)")
        print(f"    └─ F1-Score:  {metrics['f1']:.4f}")
        print("-" * 60)
        
    # 4. Calcolo e stampa delle medie finali
    valid_urls = len([e for e in gold_standard if e.get("html_text") and e["html_text"] != "INSERISCI_QUI_L_HTML_DA_CRAWL4AI"])
    
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