import asyncio
import os
import json
from pathlib import Path

# Import del parser specifico
# Assicurati che la struttura delle cartelle sia:
# project_root/
# ├── main.py
# └── parsers/
#     ├── __init__.py
#     ├── base.py
#     └── wikipedia.py
from parsers.wikipedia import WikipediaParser

async def main():
    # ==================== CONFIGURAZIONE ====================
    wiki_urls = [
        "https://en.wikipedia.org/wiki/Artificial_intelligence",
        "https://en.wikipedia.org/wiki/Proto-Romance_language",
        "https://en.wikipedia.org/wiki/Sapienza_University_of_Rome",
        "https://en.wikipedia.org/wiki/Trod"
    ]

    print("=" * 80)
    print("🚀 AVVIO PIPELINE PARSING WIKIPEDIA")
    print("=" * 80)

    # Inizializziamo il parser con la lista di URL
    parser = WikipediaParser(urls=wiki_urls)

    print(f"📡 Scaricamento di {len(wiki_urls)} pagine in parallelo...\n")

    # Esecuzione principale del crawling e parsing
    results = await parser.run_parallel()

    if not results:
        print("❌ Nessun risultato ottenuto. Controlla la connessione o i selettori.")
        return

    print(f"\n✅ Parsing completato! {len(results)} pagine elaborate correttamente.\n")

    # ==================== ANTEPRIMA A TERMINALE ====================
    print("=" * 80)
    print("👀 ANTEPRIMA DEI TESTI PARSATI (Primi 800 caratteri)")
    print("=" * 80)

    for i, page in enumerate(results, 1):
        url = page.get('url', 'URL sconosciuto')
        title = page.get('title', 'N/A')
        parsed_text = page.get('parsed_text', '').strip()
        
        print(f"\n[{i}/{len(results)}] 🔗 {url}")
        print(f"📌 Titolo: {title}")
        print("-" * 60)

        if parsed_text:
            # Calcolo numero parole per monitorare la densità del testo
            word_count = len(parsed_text.split())
            
            # Preview troncata per leggibilità
            preview = parsed_text[:800] + ("..." if len(parsed_text) > 800 else "")
            print(preview)
            print(f"\n[Conteggio parole totale: {word_count}]")
        else:
            print("⚠️ << parsed_text vuoto: verifica i selettori HTML della pagina >>")
        
        print("\n" + "*" * 80)

    # ==================== SALVATAGGIO DATI ====================
    output_dir = Path("gs_data")
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "wikipedia_gs.json"
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        print(f"\n💾 Dati salvati con successo!")
        print(f"   → Percorso: {output_path.absolute()}")
        print(f"   → Record totali: {len(results)}")
    except IOError as e:
        print(f"\n❌ Errore durante il salvataggio del file: {e}")

if __name__ == "__main__":
    # Avvio del loop asincrono
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Esecuzione interrotta manualmente dall'utente (CTRL+C).")
    except Exception as e:
        print(f"\n❌ Errore critico imprevisto: {e}")