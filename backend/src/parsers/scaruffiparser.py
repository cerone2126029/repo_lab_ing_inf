import re
from typing import Dict, Any
from urllib.parse import unquote
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from parsers.basewebparser import BaseWebParser

#=====scaruffi=====
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
        
        # Fallback di emergenza per il titolo ---
        if not data.get("title") and result.html:
            soup_title = BeautifulSoup(result.html, "html.parser")
            # Cerca il primo tag title, h1, o h2
            titolo_tag = soup_title.find(['title', 'h1', 'h2'])
            if titolo_tag:
                data["title"] = titolo_tag.get_text(strip=True)
            else:
                data["title"] = "" 

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

        # Rimuove i titoli enormi dal corpo del testo ---
        # Uccide i normali h1 e h2
        for tag in body.find_all(['h1', 'h2']):
            tag.decompose()
        # Uccide le scritte enormi fatte con il tag <font> (come nel caso dei Them)
        for tag in body.find_all('font', size=lambda value: value in ['5', '6', '7']):
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
            r'TM[\s\S]*?Copyright[\s\S]*?All\s+rights\s+reserved\.?',
            r'Copyright[\s\S]*?(?:Piero|Paolo|P\.)?\s*Scaruffi[\s\S]*?All\s+rights\s+reserved\.?',
            r'All\s+photographs\s+are\s+property\s+of[\s\S]*?provided\s+them',
            r'^[ \t]*(?:by[ \t]+)?(?:Piero|Paolo|P\.)?[ \t]*Scaruffi[ \t]*$',
            r'^[ \t]*(?:and|the|by)[ \t]*$',
            r'^[ \t]*[\|\.,\(\)\-][ \t]*$',
            r'^[ \t]*""?[ \t]*$',
            r'What\s+is\s+unique\s+about\s+this\s+music\s+database\??',    
            r'Terms\s+of\s+use',
            r'A\s+history\s+of\s+Jazz\s+Music',
            r'See\s+also\s+the',
            r'The\s+History\s+of\s+Rock\s+Music',
            r'The\s+History\s+of\s+Pop\s+Music',
            r'Main\s+jazz\s+page',
            r'Jazz\s+musicians?',
            r'To\s+purchase\s+the\s+book',
            r'\(?These\s+are\s+excerpts\s+from\s+my\s+book\)?',
            r'"?A\s+History\s+of\s+Jazz\s+Music"?',
            r'Next\s+chapter',
            r'Back\s+to\s+the\s+Index',
            r'Back\s+to\s+the\s+[A-Za-z\s]+',
            r'Links\s+to\s+other\s+sites',
            r'\(\s*(?:[Cc]lick|[Cc]licca|Translation|Translated|Tradotto)[^)]+\)',
            r'\(\s*Copyright[^)]+\)',
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