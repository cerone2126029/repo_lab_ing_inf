import json
from pathlib import Path

# Importiamo il parser di Scaruffi e l'Evaluator
from src.parsers.scaruffi import ScaruffiParser
from src.evaluator import token_level_eval

def run_scaruffi_evaluation():
    # 1. Carica il file del Gold Standard di Scaruffi
    gs_file = Path("gs_data/dominio_scaruffi_gs.json")
    
    if not gs_file.exists():
        print(f"❌ Errore: Il file {gs_file} non esiste. Assicurati di aver creato il Gold Standard!")
        return

    with open(gs_file, "r", encoding="utf-8") as f:
        gold_standard = json.load(f)

    print("=" * 60)
    print(f"🎸 INIZIO VALUTAZIONE: Dominio Scaruffi ({len(gold_standard)} URL)")
    print("=" * 60)
    
    # 2. Inizializza il parser di Scaruffi
    parser = ScaruffiParser(urls=[]) 
    
    total_f1 = 0.0
    total_precision = 0.0
    total_recall = 0.0
    
    # 3. Eseguiamo il test per ogni pagina salvata
    for i, entry in enumerate(gold_standard, 1):
        url = entry["url"]
        html_text = entry.get("html_text", "")
        gold_text = entry.get("gold_text", "")
        
        # Saltiamo se manca HTML o Gold Text
        if not html_text or html_text == "INSERISCI_QUI_L_HTML_DA_CRAWL4AI" or not gold_text:
            print(f"[{i}] ⚠️ SALTA: HTML o Gold Text mancante per {url}")
            continue

        # Usiamo il metodo specifico di Scaruffi!
        parsed_text = parser.extract_scaruffi_text(html_text)
        
        # Calcoliamo le metriche
        metrics = token_level_eval(parsed_text=parsed_text, gold_text=gold_text)
        
        total_precision += metrics['precision']
        total_recall += metrics['recall']
        total_f1 += metrics['f1']
        
        print(f"[{i}] {url}")
        print(f"    ├─ Precision: {metrics['precision']:.4f}")
        print(f"    ├─ Recall:    {metrics['recall']:.4f}")
        print(f"    └─ F1-Score:  {metrics['f1']:.4f}")
        print("-" * 60)
        
    # 4. Calcolo e stampa delle medie finali
    valid_urls = len([e for e in gold_standard if e.get("html_text") and e.get("gold_text") and e["html_text"] != "INSERISCI_QUI_L_HTML_DA_CRAWL4AI"])
    
    if valid_urls > 0:
        avg_precision = total_precision / valid_urls
        avg_recall = total_recall / valid_urls
        avg_f1 = total_f1 / valid_urls
        
        print("\n🏆 RISULTATI FINALI MEDI (SCARUFFI):")
        print(f"Precision Media: {avg_precision:.4f}")
        print(f"Recall Media:    {avg_recall:.4f}")
        print(f"F1-SCORE MEDIO:  {avg_f1:.4f}")
        
        print("\n📊 GIUDIZIO SUL PARSER:")
        if avg_f1 > 0.8:
            print("🟢 OTTIMO! Il parser domina anche l'HTML degli anni '90.")
        elif avg_f1 > 0.6:
            print("🟡 MEDIO. Controlla la Precision: forse c'è una nuova frase di boilerplate da aggiungere alla Blacklist.")
        else:
            print("🔴 SCARSO. Forse l'euristica dei link sta cancellando parti utili (Recall bassa).")
    else:
        print("Nessun URL valido valutato.")

if __name__ == "__main__":
    run_scaruffi_evaluation()