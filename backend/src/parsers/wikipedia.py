import re
from bs4 import BeautifulSoup
from crawl4ai import CrawlerRunConfig, CacheMode
from parsers.basewebparser import BaseWebParser
from typing import Dict, Any
from urllib.parse import unquote

class WikipediaParser(BaseWebParser):

    def __init__(self):
        super().__init__()
       
        self.run_config = CrawlerRunConfig (
            magic=True,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            css_selector="#mw-content-text", 
            excluded_tags=["nav", "footer", "header", "aside", "figure"],
            excluded_selector=".infobox, .infobox_v2, .mw-editsection, .navbox, #toc, .ambox, .hatnote, .thumb, .thumbinner, .gallery, .shortdescription, .tright, .tleft, .mw-halign-right, .mw-halign-left, .mw-halign-center, .reference"
        )

    def extract_data(self, result) -> Dict[str, Any]:
        data = super().extract_data(result)
        
        # === FIX 1: RECUPERO TITOLO DI EMERGENZA DALL'URL ===
        # Dato che il css_selector taglia l'h1, estraiamo il titolo direttamente dal link!
        if not data.get("title") and data.get("url"):
            url = data["url"]
            if "/wiki/" in url:
                # Prende la parte finale (es: Giuseppe_Compagnoni)
                raw_title = url.split("/wiki/")[-1]
                # Decodifica caratteri speciali (es: %20) e toglie gli underscore
                data["title"] = unquote(raw_title).replace("_", " ")

        # === FIX 2: APPLICAZIONE PULIZIA TESTO ===
        testo_grezzo = data.get("parsed_text", "")
       
        if result.success and testo_grezzo and not testo_grezzo.startswith("ERRORE"):
            data["parsed_text"] = self.clean_wikipedia_markdown(testo_grezzo)
       
        return data

    def clean_wikipedia_markdown(self, text: str) -> str:
        if not text:
            return ""

        # 1. LA GHIGLIOTTINA FINALE SUPER-BLINDATA
        # Il simbolo '^' abbinato a re.MULTILINE cerca a inizio di ogni riga.
        # È infallibile, indipendentemente dagli spazi o dagli a capo invisibili.
        stop_pattern = r'^#+\s*(References?|Notes?|See also|External links?|Further reading|Bibliography|Citations?).*$'
        match = re.search(stop_pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            text = text[:match.start()]

        # === Pulizia Specifica per Wikipedia ===
        
        # 1. Distrugge i link delle note di Wikipedia
        text = re.sub(r'\[[^\]]*\]\s*\([^\)]*#cite_note[^\)]*\)', '', text, flags=re.IGNORECASE)
        
        # 2. Distrugge qualsiasi link vuoto rimasto (es. [](url) )
        text = re.sub(r'\[\s*\]\([^\)]+\)', '', text)
        
        # 3. Elimina i [citation needed] 
        text = re.sub(r'_?\[citation needed\]_?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[Italian language\]', '', text, flags=re.IGNORECASE)

        # 4. Elimina note puramente testuali (es: [18]) isolate 
        text = re.sub(r'(?<!\!)\[\d+\]', '', text)
        text = re.sub(r'(?<!\!)\[\s*[a-z]\s*\]', '', text, flags=re.IGNORECASE)
        
        # 5. Rimuove parentesi tonde vuote
        text = re.sub(r'\(\s*\)', '', text)

        # 6. Didascalie residue e vecchi template
        text = re.sub(r'^!.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'<sup[^>]*>.*?</sup>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'\{{\s*.*?}}', '', text, flags=re.DOTALL)
       
        # 7. Frasi di servizio
        text = re.sub(r'^\s*This article (is|needs|may).*?\.$', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'^\s*This page (is|was).*?Wikipedia\.', '', text, flags=re.MULTILINE | re.IGNORECASE)
        text = re.sub(r'Coordinates?:\s*.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)

        # 8. Appiattisce i link validi rimasti `[Testo](url)` in puro `Testo`
        text = re.sub(r'(?<!\!)\[([^\]]+)\]\([^\)]+\)', r'\1', text)
       
        # 9. Normalizzazione degli spazi
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'^\s*[-*+]\s*$', '', text, flags=re.MULTILINE)
       
        return text.strip()