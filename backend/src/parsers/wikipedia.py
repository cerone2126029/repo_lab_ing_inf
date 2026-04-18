import re
from crawl4ai import CrawlerRunConfig, CacheMode
from parsers.basewebparser import BaseWebParser
from typing import Dict, Any


class WikipediaParser(BaseWebParser):

    def __init__(self):
        super().__init__()
       
        self.run_config = CrawlerRunConfig (
            magic=True,
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            css_selector="#mw-content-text", 
            excluded_tags=["nav", "footer", "header", "aside", "figure"],
            excluded_selector=".infobox, .infobox_v2, .mw-editsection, .navbox, #toc, .ambox, .hatnote, .thumb, .thumbinner, .gallery, .shortdescription, .tright, .tleft, .mw-halign-right, .mw-halign-left, .mw-halign-center"
        )

    def extract_data(self, result) -> Dict[str, Any]:
        data = super().extract_data(result)
       
        if result.success and result.markdown:
            clean_md = self.clean_wikipedia_markdown(result.markdown)
            data["parsed_text"] = clean_md
        else:
            data["parsed_text"] = f"ERRORE: {getattr(result, 'error_message', 'Unknown error')}"    
       
        return data


    def clean_wikipedia_markdown(self, text: str) -> str:
        if not text:
            return ""


        # Taglia tutte le sezioni di servizio
        stop_patterns = [
            r'##\s*References?',
            r'##\s*Notes?',
            r'##\s*See also',
            r'##\s*External links?',
            r'##\s*Further reading',
            r'##\s*Bibliography',
            r'##\s*Citations?',
        ]
       
        for pattern in stop_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                text = text[:match.start()]
                break


        # === Pulizia Specifica per Wikipedia ===
        
        # 1. Distrugge i link delle note di Wikipedia
        text = re.sub(r'\[[^\]]*\]\s*\([^\)]*#cite_note[^\)]*\)', '', text, flags=re.IGNORECASE)
        
        # 2. Distrugge qualsiasi link vuoto rimasto
        text = re.sub(r'\[\s*\]\s*\([^\)]+\)', '', text)
        
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