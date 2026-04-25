import asyncio
from parsers.wikipediaparser import WikipediaParser

async def main():
    # Scegli un URL di Wikipedia da testare
    url = "https://en.wikipedia.org/wiki/Sapienza_University_of_Rome"
    print(f"Avviando il parsing di Wikipedia per: {url}\nAttendere...")
    
    # Inizializza il parser
    parser = WikipediaParser()
    
    # Esegui il parsing (metodo asincrono)
    risultato = await parser.parse_single(url)
    
    # Stampa i risultati
    print("\n" + "="*50)
    print(f"📌 URL: {risultato.get('url')}")
    print(f"🏷️ TITOLO ESTRATTO: {risultato.get('title')}")
    
    testo_pulito = risultato.get('parsed_text', '')
    print(f"📏 LUNGHEZZA TESTO ESTRATTO: {len(testo_pulito)} caratteri")
    
    print("\n--- INIZIO TESTO (prime 1000 battute) ---")
    # Stampa le prime 1000 battute per non intaccare il terminale
    print(testo_pulito[:1000])
    print("...\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(main())