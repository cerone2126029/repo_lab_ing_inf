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

        # 1. ELIMINAZIONE DEL RUMORE
        # Su Scaruffi spesso la navigazione è in tabelle all'inizio o alla fine.
        # Eliminiamo script, stili e le classiche "barre di navigazione" se presenti.
        for tag in body.find_all(['script', 'style', 'nav', 'iframe']):
            tag.decompose()

        # Molte pagine di Scaruffi hanno link di navigazione in fondo dentro tag <center> o <hr>
        # Un'euristica comune: se trovi un tag <hr> (linea orizzontale), spesso quello che c'è sotto è il footer.
        # (Nota: potresti dover affinare questo in base agli URL esatti che ti ha dato il prof).

        # 2. ESTRAZIONE DEL TESTO
        # Poiché usa molti tag <br> per andare a capo invece dei <p>, 
        # usiamo un separatore per evitare che le parole si incollino.
        raw_text = body.get_text(separator=" ", strip=True)

        # 3. PULIZIA DEL TESTO (REGEX)
        # Rimuoviamo i riferimenti classici di Scaruffi (es. se ci sono email o copyright strani)
        # e normalizziamo gli spazi multipli creati dal separatore
        clean_text = re.sub(r'\s+', ' ', raw_text)
        
        # Sostituiamo eventuale punteggiatura incollata per via di HTML malformato
        clean_text = re.sub(r'\s+([.,;:!?])', r'\1', clean_text)

        return clean_text.strip()