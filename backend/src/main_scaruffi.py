import asyncio
import json
import sys
import os
from pathlib import Path

# Aggiungiamo la cartella src al path per evitare errori di import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsers.scaruffi import ScaruffiParser

async def main():
    # 1. Definiamo gli URL da parsare PRIMA di chiamare la classe
    scaruffi_urls = [
        "https://www.scaruffi.com/history/jazz17h.html",
        "https://www.scaruffi.com/vol1/them.html",
        "https://www.scaruffi.com/mind/ns.html",
        "https://www.scaruffi.com/science/courses.html",
        "https://www.scaruffi.com/history/calendar.html"
    ]

    print("=" * 80)
    print("🎸 AVVIO PIPELINE PARSING SCARUFFI")
    print("=" * 80)

    # 2. Inizializziamo il parser VUOTO 
    parser = ScaruffiParser()

    # 3. Passiamo gli URL alla funzione di esecuzione 
    results = await parser.parse_batch(urls=scaruffi_urls)
    
    # 4. Salvataggio sicuro nella cartella backend/results
    base_dir = Path(__file__).resolve().parent.parent  # Punta a backend/
    output_dir = base_dir / "results"
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "scaruffi_results.json" 
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n💾 Dati salvati con successo!")
        print(f"   → Percorso: {output_path}")
        print(f"   → Record totali: {len(results)}")
    except IOError as e:
        print(f"\n❌ Errore durante il salvataggio: {e}")

if __name__ == "__main__":
    asyncio.run(main())