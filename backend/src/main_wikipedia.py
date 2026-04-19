import asyncio
import json
import sys
import os
from pathlib import Path

# Aggiungiamo la cartella src al path per evitare errori di import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsers.wikipedia import WikipediaParser

async def main():
    # 1. Definiamo gli URL da parsare PRIMA di chiamare la classe
    wikipedia_urls = [
        "https://en.wikipedia.org/wiki/Giuseppe_Compagnoni",
        "https://en.wikipedia.org/wiki/Lake_Bracciano",
        "https://en.wikipedia.org/wiki/Emblem_of_Italy",
        "https://en.wikipedia.org/wiki/Prince_of_Piedmont",
        "https://en.wikipedia.org/wiki/SS_Alba-Audace_Roma"
    ]

    print("=" * 80)
    print("🏛️ AVVIO PIPELINE PARSING WIKIPEDIA")
    print("=" * 80)

    # 2. Passiamo gli URL alla classe per evitare il TypeError
    parser = WikipediaParser()

    # 3. Eseguiamo il parsing in parallelo
    results = await parser.parse_batch(urls=wikipedia_urls)
    
    # 4. Salvataggio sicuro nella cartella backend/results
    base_dir = Path(__file__).resolve().parent.parent  # Punta a backend/
    output_dir = base_dir / "results"
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "wikipedia_results.json" 
    
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