import re
from crawl4ai import CrawlerRunConfig, CacheMode
from parsers.basewebparser import BaseWebParser
from typing import Dict, Any
from urllib.parse import unquote

class TravelStateGov(BaseWebParser):

    # Regex per convertire eventuali [Testo del link](url) rimasti in semplice "Testo del link"
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
            ".wp-caption"
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

    def extract_data(self, result) -> Dict[str, Any]:
        data = super().extract_data(result)

        self._extract_fallback_title(data)

        parsed_text = data.get("parsed_text", "")
        if result.success and parsed_text and not parsed_text.startswith("ERRORE"):
            data["parsed_text"] = self.clean_travelstategov_markdown(parsed_text)
       
        return data
    #recupero del titolo dall'url, se fallisce l'estrapolazione da <title>
    def _extract_fallback_title(self, data: Dict[str, Any]) -> None:
        """Recupera il titolo dall'URL in caso di fallimento dei selettori CSS."""
        url = data.get("url", "")
        if not data.get("title") and ".html" in url:
            raw_title = url.split("/")[-1].replace(".html", "")
            data["title"] = unquote(raw_title).replace("-", " ")

    def clean_travelstategov_markdown(self, text: str) -> str:
        if not text:
            return ""
        
        # Applica sequenzialmente tutte le regole di pulizia testuale
        for pattern, replacement in self._CLEANING_RULES:
            text = pattern.sub(replacement, text)
       
        return text.strip()