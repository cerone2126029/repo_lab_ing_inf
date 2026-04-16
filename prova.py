import asyncio
import json
from crawl4ai import AsyncWebCrawler

async def scarica_html_sicuro():
    url = "https://www.scaruffi.com/vol1/them.html"
    print(f"Scaricando: {url}...")
    
    # Avviamo Crawl4AI
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        
        if result.success:
            # Mettiamo l'HTML in un dizionario Python
            dati = {"html_text": result.html}
            
            # Salviamo il file usando json.dump: 
            # questo farà l'escape automatico di TUTTE le virgolette e gli a capo!
            with open("html_sicuro.json", "w", encoding="utf-8") as f:
                json.dump(dati, f, indent=4)
                
            print("Fatto! File 'html_sicuro.json' generato con successo.")
        else:
            print(f"Errore durante il download: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(scarica_html_sicuro())