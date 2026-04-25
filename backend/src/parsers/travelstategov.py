import re
from crawl4ai import CrawlerRunConfig, CacheMode
from parsers.basewebparser import BaseWebParser
from urllib.parse import unquote
from typing import Optional

class TravelStateGov(BaseWebParser):

    _CLEANING_RULES = [
        (re.compile(r'\[([^\]]+)\]\([^\)]+\)'), r'\1'),
        (re.compile(r'^.*Last Updated:.*$', flags=re.IGNORECASE | re.MULTILINE), ''),
        (re.compile(r'\[\]\(javascript:void\\?\(0\\?\);?[^\)]*\)'), '')
    ]

    def __init__(self):
        super().__init__()
       
        excluded_selectors = [
            ".simplebutton",
            ".featurebox",
            ".SlideShow",
            ".fusion-builder-column-3",
            ".imageframe",
            ".fusion-button",
            ".wp-caption",
            ".tsg-rwd-accordion"
        ]

        self.run_config = CrawlerRunConfig(
            magic=True,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            exclude_internal_links=True,
            exclude_all_images=True,
            exclude_social_media_links=True,
            css_selector=".tsg-rwd-main-copy-body-frame, .post-content",
            excluded_tags=["nav", "footer", "header", "img"],
            excluded_selector=", ".join(excluded_selectors) if excluded_selectors else None
        )
    
    def extract_fallback_title(self, url: str) -> Optional[str]:
        """
        Metodo ereditato e sovrascritto. 
        Recupera il titolo dall'URL gestendo sia i link con .html sia quelli senza.
        """
        if url:
            # 1. Rimuove l'eventuale slash finale (es: "accommodations/" -> "accommodations")
            clean_url = url.rstrip("/")
            
            # 2. Prende l'ultimo blocco dell'URL
            raw_title = clean_url.split("/")[-1]
            
            # 3. Toglie l'eventuale .html, decodifica e sostituisce i trattini
            raw_title = unquote(raw_title).replace(".html", "").replace(".htm", "").replace("-", " ")
            
            # 4. Rende la prima lettera di ogni parola maiuscola per un aspetto più pulito
            return raw_title.title()
            
        return None
    
    def parse_offline_html(self, html_content: str) -> str:
        """Metodo per l'elaborazione offline (Gold Standard) delegato al parser."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        content = soup.select_one(".tsg-rwd-main-copy-body-frame, .post-content") or soup
        raw_text = content.get_text(separator="\n")
        return self.clean_markdown(raw_text)
    

    def clean_markdown(self, text: str) -> str:
        if not text:
            return ""
        
        for pattern, replacement in self._CLEANING_RULES:
            text = pattern.sub(replacement, text)
       
        return text.strip()