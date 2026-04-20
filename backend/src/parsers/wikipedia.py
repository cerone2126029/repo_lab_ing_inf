import re
from typing import Dict, Any
from urllib.parse import unquote

from crawl4ai import CrawlerRunConfig, CacheMode
from parsers.basewebparser import BaseWebParser


class WikipediaParser(BaseWebParser):
    
    # === PRE-COMPILAZIONE DELLE REGEX PER MASSIMIZZARE LE PRESTAZIONI ===
    
    _STOP_PATTERN = re.compile(
        r'^#+\s*(References?|Notes?|See also|External links?|Further reading|Bibliography|Citations?).*$',
        flags=re.IGNORECASE | re.MULTILINE
    )

    # Lista di tuple: (Pattern Regex Compilato, Stringa di Sostituzione)
    _CLEANING_RULES = [
        # 1. Distrugge i link delle note di Wikipedia
        (re.compile(r'\[[^\]]*\]\s*\([^\)]*#cite_note[^\)]*\)', flags=re.IGNORECASE), ''),
        # 2. Distrugge qualsiasi link vuoto rimasto
        (re.compile(r'\[\s*\]\([^\)]+\)'), ''),
        # 3. Elimina i [citation needed] e simili
        (re.compile(r'_?\[citation needed\]_?', flags=re.IGNORECASE), ''),
        (re.compile(r'\[Italian language\]', flags=re.IGNORECASE), ''),
        # 4. Elimina note puramente testuali (es: [18]) isolate
        (re.compile(r'(?<!\!)\[\d+\]'), ''),
        (re.compile(r'(?<!\!)\[\s*[a-z]\s*\]', flags=re.IGNORECASE), ''),
        # 5. Rimuove parentesi tonde vuote
        (re.compile(r'\(\s*\)'), ''),
        # 6. Didascalie residue e vecchi template
        (re.compile(r'^!.*$', flags=re.MULTILINE), ''),
        (re.compile(r'<sup[^>]*>.*?</sup>', flags=re.IGNORECASE | re.DOTALL), ''),
        (re.compile(r'\{\{\s*.*?\}\}', flags=re.DOTALL), ''),
        # 7. Frasi di servizio
        (re.compile(r'^\s*This article (is|needs|may).*?\.$', flags=re.MULTILINE | re.IGNORECASE), ''),
        (re.compile(r'^\s*This page (is|was).*?Wikipedia\.', flags=re.MULTILINE | re.IGNORECASE), ''),
        (re.compile(r'Coordinates?:\s*.*$', flags=re.MULTILINE | re.IGNORECASE), ''),
        # 8. Appiattisce i link validi rimasti `[Testo](url)` in puro `Testo`
        (re.compile(r'(?<!\!)\[([^\]]+)\]\([^\)]+\)'), r'\1'),
        # 9. Normalizzazione degli spazi e rimozione elenchi vuoti
        (re.compile(r'\n{3,}'), '\n\n'),
        (re.compile(r'^\s*[-*+]\s*$', flags=re.MULTILINE), '')
    ]

    def __init__(self):
        super().__init__()
       
        # Formattazione leggibile per i selettori CSS
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

    def extract_data(self, result) -> Dict[str, Any]:
        data = super().extract_data(result)
        
        self._extract_fallback_title(data)

        parsed_text = data.get("parsed_text", "")
        if result.success and parsed_text and not parsed_text.startswith("ERRORE"):
            data["parsed_text"] = self.clean_wikipedia_markdown(parsed_text)
       
        return data

    def _extract_fallback_title(self, data: Dict[str, Any]) -> None:
        """Recupera il titolo dall'URL in caso di fallimento dei selettori CSS."""
        url = data.get("url", "")
        if not data.get("title") and "/wiki/" in url:
            raw_title = url.split("/wiki/")[-1]
            data["title"] = unquote(raw_title).replace("_", " ")

    def clean_wikipedia_markdown(self, text: str) -> str:
        if not text:
            return ""

        # 1. Applica la ghigliottina finale
        match = self._STOP_PATTERN.search(text)
        if match:
            text = text[:match.start()]

        # 2. Applica sequenzialmente tutte le regole di pulizia
        for pattern, replacement in self._CLEANING_RULES:
            text = pattern.sub(replacement, text)
       
        return text.strip()