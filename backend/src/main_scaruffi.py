import asyncio
from parsers.scaruffi import ScaruffiParser

async def main():
    print("Inizializzazione del ScaruffiParser...")
    parser = ScaruffiParser()

    test_url = "https://www.scaruffi.com/vol1/beatles.html"
    
    print(f"Avvio crawling asincrono per: {test_url}\n")
    
    result = await parser.parse_single(test_url)
    
    if result["parsed_text"].startswith("ERRORE:"):
        print("Si è verificato un errore durante il crawling:")
        print(result["parsed_text"])
        return

    print("=== RISULTATI ESTRAZIONE ===")
    print(f"URL Originale: {result['url']}")
    print(f"Dominio:       {result['domain']}")
    print(f"Titolo:        {result['title']}")
    print("============================\n")
    
    print("=== ANTEPRIMA TESTO PULITO (primi 20000 caratteri) ===")
    print(result["parsed_text"][:20000])
    print("\n[...] (testo troncato per l'anteprima)")
    
    # Controllo lunghezza totale
    print(f"\nLunghezza totale del testo estratto: {len(result['parsed_text'])} caratteri")

if __name__ == "__main__":
    # Esegue il loop asincrono
    asyncio.run(main())