import re
from bs4 import BeautifulSoup
from typing import Optional
from crawl4ai import CrawlerRunConfig, CacheMode
from parsers.basewebparser import BaseWebParser

class ScaruffiParser(BaseWebParser):

    _SPAZZATURA = [
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

    def __init__(self):
        super().__init__()
        
        # Anche qui manteniamo le impostazioni base vitali!
        self.run_config = CrawlerRunConfig(
            delay_before_return_html=2,
            remove_overlay_elements=False, # Ereditato dal padre
            cache_mode=CacheMode.BYPASS,   # Specifico
            exclude_external_links=True
        )

    # 1. SOVRASCRIVIAMO IL FALLBACK DEL TITOLO (Leggiamo l'HTML, non l'URL)
    def extract_fallback_title(self, url: str) -> Optional[str]:
        """
        Emergenza finale per Scaruffi.
        Ricava il titolo dall'URL in modo neutro.
        """
        if url:
            # Prende l'ultimo pezzo dell'URL (es. "beatles.html" o "cpt12.html")
            raw_title = url.split("/")[-1]
            
            # Toglie l'estensione e sostituisce eventuali trattini/underscore con spazi
            clean_title = raw_title.replace(".html", "").replace(".htm", "").replace("_", " ").replace("-", " ")
            
            # Formatta il titolo con le iniziali maiuscole (es. "beatles" -> "Beatles")
            return clean_title.title()
            
        return None

    def parse_offline_html(self, html_content: str) -> str:
        """Metodo per l'elaborazione offline (Gold Standard) delegato al parser."""
        # Simuliamo internamente l'oggetto di Crawl4AI per riutilizzare la tua logica
        class MockResult:
            def __init__(self, html):
                self.html = html
                self.success = True
        
        return self.extract_and_clean_text(MockResult(html_content))

    # 2. SOVRASCRIVIAMO L'ESTRAZIONE DEL TESTO (Bypassiamo il markdown, usiamo BS4 sull'HTML)
    def extract_and_clean_text(self, result) -> str:
        if not result.success or not result.html:
            return ""

        soup = BeautifulSoup(result.html, "html.parser")
        body = soup.find('body')
        
        if not body:
            return "Nessun tag <body> trovato."

        # 1. ELIMINAZIONE DEL RUMORE INVISIBILE E STRUTTURALE
        for tag in body.find_all(['script', 'style', 'nav', 'iframe', 'form']):
            tag.decompose()

        # Rimuove i titoli enormi e le scritte enormi (Them)
        for tag in body.find_all(['h1', 'h2']):
            tag.decompose()
        for tag in body.find_all('font', size=lambda value: value in ['5', '6', '7']):
            tag.decompose()

        # 2. EURISTICA DELLA DENSITA' DEI LINK
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

        # 4. LA BLACKLIST (Sterminatore di Boilerplate)
        for pattern in self._SPAZZATURA:
            raw_text = re.sub(pattern, '', raw_text, flags=re.IGNORECASE)

        # 5. PULIZIA FINALE E IMPAGINAZIONE
        clean_lines = []
        for line in raw_text.split('\n'):
            line = line.strip()
            if line and line != "|":
                clean_lines.append(line)

        return "\n\n".join(clean_lines)

    # Non ci serve sovrascrivere clean_markdown, perché abbiamo aggirato la base!