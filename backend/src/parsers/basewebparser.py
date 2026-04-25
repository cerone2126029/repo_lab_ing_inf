from urllib.parse import urlparse
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from typing import Optional
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


class BaseWebParser:
    def __init__(self):

        self.browser_config = BrowserConfig(
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"      
        )

        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,

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
    

    def _extract_html_title(self, html_content: str) -> Optional[str]:
        """Emergenza universale: Cerca il tag <title>, meta og:title o <h1> nell'HTML."""
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 1. Il tuo metodo originale (ottimo)
        title_tag = soup.find('title')
        if title_tag and title_tag.get_text(strip=True):
            return title_tag.get_text(strip=True)
            
        # 2. Aggiunta: cerca nei metadati Open Graph (per i siti moderni)
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
            
        # 3. Aggiunta: cerca il primo <h1> (per i siti senza meta tag)
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
            
        return None
    
    def extract_data(self, result) -> Dict[str, Any]:
        """
        Metodo base per l'estrazione. Crea la struttura dati richiesta dall'esonero.
        Le classi figlie chiameranno super().extract_data(result) e applicheranno
        le rifiniture testuali su data["parsed_text"].
        """

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


        # 1° tentativo di estrazione del titolo
        title = result.metadata.get("title") if result.metadata else None

        # 2° tentativo di estrazione del titolo
        if not title and result.html:
            title = self._extract_html_title(result.html)

        # 3° tentativo di estrazione del titolo (CORRETTO)
        if not title:
            title = self.extract_fallback_title(result.url)

        # Estrazione del Markdown nativo generato da Crawl4AI
        cleaned_text = self.extract_and_clean_text(result)

        return {
            "url": result.url,
            "domain": domain,
            "title": title,
            "html_text": result.html or "",
            "parsed_text": cleaned_text
        }
    
    def extract_and_clean_text(self, result) -> str:
        """
        Di base: usa il Markdown di Crawl4AI e chiama clean_markdown.
        (TravelState e Wikipedia useranno questo comportamento di base).
        """
        raw_markdown = result.markdown if hasattr(result, 'markdown') and result.markdown else ""
        return self.clean_markdown(raw_markdown.strip())
    
    def clean_markdown(self, text: str) -> str:
        """
        Pulizia del testo.
        Di base restituisce il testo intatto. Le classi figlie devono 
        sovrascriverlo per applicare le loro Regex di pulizia.
        """
        return text
    
    def extract_fallback_title(self, url: str) -> Optional[str]:
        """
        Emergenza finale: Estrazione dall'URL. 
        Di base restituisce None. Le classi figlie devono sovrascriverlo 
        """
        return None