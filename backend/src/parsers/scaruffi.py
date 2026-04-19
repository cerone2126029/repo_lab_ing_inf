from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .basewebparser import BaseWebParser
from crawl4ai import CacheMode, CrawlerRunConfig
from typing import Dict, Any
import re

class ScaruffiParser(BaseWebParser):

    def __init__(self):
        super().__init__()
        self.run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            remove_overlay_elements=False
        )

    def extract_data(self, result) -> Dict[str, Any]:
        data = super().extract_data(result)
        if result.success and result.html:
            data["parsed_text"] = self.extract_scaruffi_text(result.html)
        return data
    
    def extract_scaruffi_text(self, html: str) -> str:
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")
        body = soup.find('body')
        
        if not body:
            return "Nessun tag <body> trovato."

        # 1. ELIMINAZIONE DEL RUMORE INVISIBILE E STRUTTURALE
        for tag in body.find_all(['script', 'style', 'nav', 'iframe', 'form']):
            tag.decompose()

        # 2. EURISTICA DELLA DENSITA' DEI LINK (Per eliminare le discografie e i menù grandi)
        for container in body.find_all(['table', 'ul']):
            links = container.find_all('a')
            if not links:
                continue
            
            text_in_links = sum(len(a.get_text(strip=True)) for a in links)
            total_text = len(container.get_text(strip=True))
            
            if total_text > 0 and (text_in_links / total_text) > 0.40:
                container.decompose()

        # 3. ESTRAZIONE DEL TESTO
        raw_text = body.get_text(separator="\n", strip=True)

        # 4. LA BLACKLIST (Sterminatore di Boilerplate di Scaruffi)
        # Un elenco di pattern Regex per disintegrare le frasi fastidiose ovunque siano
        spazzatura = [
            # I blocchi Copyright (cattura tutto da TM/Copyright fino a reserved)
            r'(?is)TM.*?Copyright.*?All\s+rights\s+reserved\.?',
            r'(?is)Copyright.*?Piero\s+Scaruffi.*?All\s+rights\s+reserved\.?',
            r'(?is)All\s+photographs\s+are\s+property\s+of.*?provided\s+them',
            r'(?is)What\s+is\s+unique\s+about\s+this\s+music\s+database\??',    
            r'(?is)Terms\s+of\s+use',
            
            # I Menu spezzati su più righe
            r'(?is)A\s+history\s+of\s+Jazz\s+Music',
            r'(?is)See\s+also\s+the',
            r'(?is)The\s+History\s+of\s+Rock\s+Music',
            r'(?is)The\s+History\s+of\s+Pop\s+Music',
            r'(?is)Main\s+jazz\s+page',
            r'(?is)Jazz\s+musicians?',
            r'(?is)To\s+purchase\s+the\s+book',
            r'(?is)\(?These\s+are\s+excerpts\s+from\s+my\s+book\)?',
            r'(?is)"?A\s+History\s+of\s+Jazz\s+Music"?',
            r'(?is)Next\s+chapter',
            r'(?is)Back\s+to\s+the\s+Index',
            r'(?is)Back\s+to\s+the\s+[A-Za-z\s]+',
            r'(?is)Links\s+to\s+other\s+sites',
            
            # Utility e Click
            r'(?is)\(\s*(?:click|clicca|translation|translated|tradotto)[^)]+\)',
            r'(?is)\(\s*Copyright[^)]+\)'
        ]

        # Applichiamo la blacklist: sostituiamo ogni frase trovata con il vuoto ("")
        for pattern in spazzatura:
            raw_text = re.sub(pattern, '', raw_text, flags=re.IGNORECASE)

        # 5. PULIZIA FINALE E IMPAGINAZIONE
        clean_lines = []
        for line in raw_text.split('\n'):
            line = line.strip()
            
            # Ignoriamo le righe vuote e i "rimasugli" grafici come la barra |
            if line and line != "|":
                clean_lines.append(line)

        final_text = "\n\n".join(clean_lines)

        return final_text