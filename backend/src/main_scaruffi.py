import asyncio
import os
import json
from pathlib import Path

# IMPORTIAMO IL NUOVO PARSER
from parsers.scaruffi import ScaruffiParser

async def main():
    # Inserisci qui i 5 URL di Scaruffi che ti ha assegnato il prof
    scaruffi_urls = [
        "https://www.scaruffi.com/vol1/beatles.html",
        "https://www.scaruffi.com/vol1/stones.html", 
        "https://www.scaruffi.com/vol7/hecker.html",
        "https://www.scaruffi.com/vol6/fennesz.html",
        "https://www.scaruffi.com/vol6/pansonic.html"
    ]

    print("=" * 80)
    print("🚀 AVVIO PIPELINE PARSING SCARUFFI")
    print("=" * 80)

    # Inizializziamo il nuovo parser
    parser = ScaruffiParser(urls=scaruffi_urls)

    results = await parser.run_parallel()
    
    # ... (Lascia intatta la parte centrale con le stampe a schermo) ...

    # ==================== SALVATAGGIO DATI ====================
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)
    
    # SALVIAMO IN UN FILE DIVERSO!
    output_path = output_dir / "scaruffi_results.json" 
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n💾 Dati salvati in: {output_path}")
    except IOError as e:
        print(f"\n❌ Errore durante il salvataggio: {e}")

if __name__ == "__main__":
    asyncio.run(main())