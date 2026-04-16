from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .basewebparser import BaseWebParser
from crawl4ai import CacheMode, CrawlerRunConfig
from typing import Dict, Any
import re

class ScaruffiParser(BaseWebParser):

    def __init__(self, urls):
        super().__init__(urls)
        # Niente wait_for, il sito di Scaruffi è statico e leggerissimo
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
            r'\(\s*Copyright[^)]+\)',                                         # Copyright con o senza parentesi
            r'What is unique about this music database\??',                   # La frase specifica del database
            r'\([Cc]lick[^)]+(version|qua|here)[^)]+\)',                      # Il link della traduzione
            r'Terms of use',                                                  # Frasi legali
            r'Back to the\s+[A-Za-z\s]+',                                     # Link di ritorno (es. "Back to the index")
            r'Links to other sites',
            r'\(\s*(Translation\s+by|Translated\s+by|Tradotto\s+da)[^)]+\)'   # Intestazioni di link
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