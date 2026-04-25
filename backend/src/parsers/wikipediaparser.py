import re
from urllib.parse import unquote
from typing import Optional
from crawl4ai import CrawlerRunConfig, CacheMode
from parsers.basewebparser import BaseWebParser

class WikipediaParser(BaseWebParser):
    
    _STOP_PATTERN = re.compile(
        r'^#+\s*(References?|Notes?|See also|External links?|Further reading|Bibliography|Citations?).*$',
        flags=re.IGNORECASE | re.MULTILINE
    )

    _CLEANING_RULES = [
        (re.compile(r'\[[^\]]*\]\s*\([^\)]*#cite_note[^\)]*\)', flags=re.IGNORECASE), ''),
        (re.compile(r'\[\s*\]\([^\)]+\)'), ''),
        (re.compile(r'_?\[citation needed\]_?', flags=re.IGNORECASE), ''),
        (re.compile(r'\[Italian language\]', flags=re.IGNORECASE), ''),
        (re.compile(r'(?<!\!)\[\d+\]'), ''),
        (re.compile(r'(?<!\!)\[\s*[a-z]\s*\]', flags=re.IGNORECASE), ''),
        (re.compile(r'\(\s*\)'), ''),
        (re.compile(r'^!.*$', flags=re.MULTILINE), ''),
        (re.compile(r'<sup[^>]*>.*?</sup>', flags=re.IGNORECASE | re.DOTALL), ''),
        (re.compile(r'\{\{\s*.*?\}\}', flags=re.DOTALL), ''),
        (re.compile(r'^\s*This article (is|needs|may).*?\.$', flags=re.MULTILINE | re.IGNORECASE), ''),
        (re.compile(r'^\s*This page (is|was).*?Wikipedia\.', flags=re.MULTILINE | re.IGNORECASE), ''),
        (re.compile(r'Coordinates?:\s*.*$', flags=re.MULTILINE | re.IGNORECASE), ''),
        (re.compile(r'(?<!\!)\[([^\]]+)\]\([^\)]+\)'), r'\1'),
        (re.compile(r'\n{3,}'), '\n\n'),
        (re.compile(r'^\s*[-*+]\s*$', flags=re.MULTILINE), '')
    ]

    def __init__(self):
        super().__init__()
       
        excluded_selectors = [
            ".infobox", ".infobox_v2", ".mw-editsection", ".navbox", "#toc", 
            ".ambox", ".hatnote", ".thumb", ".thumbinner", ".gallery", 
            ".shortdescription", ".tright", ".tleft", ".mw-halign-right", 
            ".mw-halign-left", ".mw-halign-center", ".reference"
        ]

        self.run_config = CrawlerRunConfig(
            magic=True,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            css_selector="#mw-content-text", 
            excluded_tags=["nav", "footer", "header", "aside", "figure"],
            excluded_selector=", ".join(excluded_selectors)
        )


    def extract_fallback_title(self, url: str) -> Optional[str]:

        if url and "/wiki/" in url:
            raw_title = url.split("/wiki/")[-1]
            title = unquote(raw_title).replace("_", " ")
            
            if " - Wikipedia" not in title:
                title = f"{title} - Wikipedia"
                
            return title
            
        return None
    

    def clean_markdown(self, text: str) -> str:

        if not text:
            return ""

        match = self._STOP_PATTERN.search(text)
        if match:
            text = text[:match.start()]

        for pattern, replacement in self._CLEANING_RULES:
            text = pattern.sub(replacement, text)
       
        return text.strip()
    
    def parse_offline_html(self, html_content: str) -> str:
        """Metodo per l'elaborazione offline (Gold Standard) delegato al parser."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        for tag in soup.find_all(['nav', 'footer', 'header', 'aside', 'figure']): 
            tag.decompose()
        for junk in soup.select(".infobox, .infobox_v2, .mw-editsection, .navbox, #toc, .ambox, .hatnote, .thumb, .thumbinner, .gallery, .shortdescription, .tright, .tleft, .mw-halign-right, .mw-halign-left, .mw-halign-center, .reference"): 
            junk.decompose()
        for h2 in soup.find_all('h2'): h2.insert(0, "## ")
        for h3 in soup.find_all('h3'): h3.insert(0, "### ")
        
        content = soup.select_one("#mw-content-text") or soup
        return self.clean_markdown(content.get_text(separator="\n"))