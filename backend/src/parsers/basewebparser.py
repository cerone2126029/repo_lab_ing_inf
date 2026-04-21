from urllib.parse import urlparse, unquote
from typing import List, Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

#=====BaseWebParser=====
class BaseWebParser:
    def __init__(self):

        # 1. Configurazione del browser comune a tutti i parser
        self.browser_config = BrowserConfig(
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"      
        )

        # 2. Configurazione base per il crawling.
        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            remove_overlay_elements=False,
            wait_for=5
        )


    async def parse_single(self, url: str) -> Dict[str, Any]:
        """
        FASE FINALE: Metodo usato dall'endpoint FastAPI per analizzare un solo URL.
        Avvia il crawler per una singola pagina e restituisce il dizionario.
        """
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(
                url=url,
                config=self.run_config
            )
            return self.extract_data(result)


    async def parse_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        FASE DI TESTING: Metodo usato dallo script locale per analizzare liste di URL
        (utile per confrontare con il Gold Standard).
        """
        results_list = []
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            crawl_results = await crawler.arun_many(
                urls=urls,
                config=self.run_config
            )


            for result in crawl_results:
                data = self.extract_data(result)
                results_list.append(data)


        return results_list


    def extract_data(self, result) -> Dict[str, Any]:
        """
        Metodo base per l'estrazione. Crea la struttura dati richiesta dall'esonero.
        Le classi figlie chiameranno super().extract_data(result) e applicheranno
        le rifiniture testuali su data["parsed_text"].
        """
        # Calcolo sicuro del dominio
        domain = urlparse(result.url).netloc if result.url else ""


        # Gestione del fallimento della richiesta
        if not result.success:
            return {
                "url": result.url,
                "domain": domain,
                "title": None,
                "html_text": "",
                "parsed_text": f"ERRORE: {result.error_message}"
            }


        # Estrazione sicura del titolo dai metadati
        title = result.metadata.get("title") if result.metadata else None


        # Estrazione del Markdown nativo generato da Crawl4AI
        # (Usa result.markdown o result.extracted_content a seconda della versione esatta che hai)
        raw_markdown = result.markdown if hasattr(result, 'markdown') and result.markdown else ""


        return {
            "url": result.url,
            "domain": domain,
            "title": title,
            "html_text": result.html or "",
            "parsed_text": raw_markdown.strip()
        }