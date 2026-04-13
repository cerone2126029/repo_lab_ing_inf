from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .basewebparser import BaseWebParser
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from typing import List, Dict, Any
import re

class WikipediaParser(BaseWebParser):

    def __init__(self, urls):
        super().__init__(urls)

        # Configurazione specifica: rimosso remove_overlay_elements che distruggeva il DOM
        self.run_config = CrawlerRunConfig(
            wait_for="css:#mw-content-text",
            delay_before_return_html=2.0, # 5 secondi sono eccessivi, 2 bastano
            cache_mode=CacheMode.BYPASS,
            exclude_external_links=True,
            remove_overlay_elements=False 
        )

    def extract_data(self, result) -> Dict[str, Any]:
        data = super().extract_data(result) # Prende i dati base
        
        if result.success and result.html:
            wiki_text = self.extract_wikipedia_text(result.html)
            data["parsed_text"] = wiki_text
        else:
            print(f"Salto estrazione per {result.url}: Success={result.success}")
            
        return data
    
    def extract_wikipedia_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        content = soup.select_one("#mw-content-text .mw-parser-output") or soup.select_one(".mw-parser-output")
        if not content:
            return "Nessun contenuto in #mw-content-text"
        
        # RIMOSSI "script" e "style" per evitare bug fatali di decodifica
        for selector in [
            "sup.reference", ".mw-references-wrap", ".reference",
            ".infobox", ".ambox", ".navbox", ".metadata", ".mw-editsection",
            ".hatnote", ".mw-empty-elt"
        ]:
            for tag in content.select(selector):
                tag.decompose()

        elements = content.find_all(['h2', 'h3', 'p', 'ul', 'ol', 'table'])
        text_parts = []
        
        # FLAG fondamentale per saltare i paragrafi delle sezioni indesiderate
        skip_section = False

        for el in elements:
            if el.name in ('h2', 'h3'):
                text = el.get_text(" ", strip=True).strip()
                lower = text.lower()

                # Se troviamo una sezione di servizio, attiviamo lo skip e passiamo oltre
                if any(skip in lower for skip in [
                    "note", "references", "external links", "see also", "bibliography", "further reading"
                ]):
                    skip_section = True
                    continue
                else:
                    # Se troviamo una sezione utile (es. History), disattiviamo lo skip
                    skip_section = False

                level = 2 if el.name == 'h2' else 3
                text_parts.append(f"\n{'#'*level} {text}\n")

            # Se siamo dentro una sezione da saltare (es. sotto "References"), ignoriamo il tag
            elif skip_section:
                continue

            elif el.name == 'p':
                text = el.get_text(" ", strip=True)
                text = re.sub(r"\[\d+\]|\[\w+\]", "", text)
                text = re.sub(r"\s+([.,;:!?])", r"\1", text)
                text = re.sub(r"\s{2,}", " ", text)
                if text: # Aggiungiamo solo se c'è effettivamente del testo
                    text_parts.append(text.strip())

            elif el.name in ('ul', 'ol'):
                list_items = []
                for li in el.find_all('li', recursive=False):
                    item_text = li.get_text(" ", strip=True)
                    if item_text:
                        item_text = re.sub(r"\[\d+\]|\[\w+\]", "", item_text)
                        item_text = re.sub(r"\s{2,}", " ", item_text)
                        prefix = "- " if el.name == 'ul' else f"{len(list_items)+1}. "
                        list_items.append(f"{prefix}{item_text.strip()}")
                if list_items:
                    text_parts.append("\n".join(list_items))
                    
            elif el.name == 'table':
                table_md = self._table_to_markdown(el)
                if table_md and len(table_md.strip()) > 20:   
                    text_parts.append(table_md)

        final_text = "\n\n".join(text_parts).strip()
        final_text = re.sub(r"\n{3,}", "\n\n", final_text)   
        return final_text

    def _table_to_markdown(self, table) -> str:
        rows = table.find_all('tr')
        if not rows:
            return ""

        markdown_rows = []

        for row in rows:
            cells = row.find_all(['th', 'td'])
            if cells:
                cell_texts = [cell.get_text(" ", strip=True) for cell in cells]
                markdown_rows.append("| " + " | ".join(cell_texts) + " |")

        if not markdown_rows:
            return ""

        if markdown_rows:
            header = markdown_rows[0]
            separator = "|" + "---|" * (header.count("|") - 1)
            markdown_rows.insert(1, separator)

        return "\n".join(markdown_rows)