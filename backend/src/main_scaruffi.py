import asyncio
from parsers.scaruffiparser import ScaruffiParser

async def main():
    # Scegli un URL di Scaruffi da testare
    url = "https://www.scaruffi.com/history/cpt12.html"
    print(f"Avviando il parsing di Scaruffi per: {url}\nAttendere...")
    
    # Inizializza il parser
    parser = ScaruffiParser()
    
    # Esegui il parsing (metodo asincrono)
    risultato = await parser.parse_single(url)
    
    # Stampa i risultati
    print("\n" + "="*50)
    print(f"📌 URL: {risultato.get('url')}")
    print(f"🏷️ TITOLO ESTRATTO: {risultato.get('title')}")
    
    testo_pulito = risultato.get('parsed_text', '')
    print(f"📏 LUNGHEZZA TESTO ESTRATTO: {len(testo_pulito)} caratteri")
    
    print("\n--- INIZIO TESTO (prime 1000 battute) ---")
    print(testo_pulito[:1000])
    print("...\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(main())