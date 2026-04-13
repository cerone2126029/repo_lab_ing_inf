import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from urllib.parse import urlparse
from typing import List, Dict, Any

class BaseWebParser:

    def __init__(self, urls: List[str]):

        #Il parser riceve una lista di URL da visitare e parsare
        self.urls = urls

        #Configurazione del browser comune a tutti i parser
        self.browser_config = BrowserConfig(
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )

        #Configurazione base per il crawling
        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            remove_overlay_elements=True,
            wait_for=5,
        )
    #Funzione per l'estrazione dei dati necessari
    def extract_data(self, result) -> Dict[str, Any]:
        if not result.success:
            return {
                "url": result.url,
                "domain": urlparse(result.url).netloc,
                "title":None,
                "html_text":"",
                "parsed_text": f"ERRORE: {result.error_message}"
            }
        
        domain = urlparse(result.url).netloc
        html_text = result.html
        parsed_text = result.markdown or "Errore nel markdown"

        return {
            "url": result.url,
            "domain": domain,
            "title": result.metadata.get("title") if result.metadata else None,
            "html_text": html_text,
            "parsed_text": parsed_text.strip()
        }
    
    async def run_parallel(self) -> List[Dict[str, Any]]:
        results_list = []
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            # arun_many è molto più affidabile per liste di URL
            crawl_results = await crawler.arun_many(
                urls=self.urls,
                config=self.run_config,
                bypass_cache=True
            )

            for result in crawl_results:
                # Qui viene chiamato extract_data di WikipediaParser (se istanziato quello)
                data = self.extract_data(result)
                results_list.append(data)

        self.save_results(results_list)
        return results_list
        
    def save_results(self, data_list: List[Dict[str, Any]]):
        #Salviamo i risultati in un file JSON
        with open("results.json", "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=4)
        print(f"Salvati {len(data_list)} risultati in risults.json")