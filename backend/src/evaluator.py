import re
import string
import mistune
from bs4 import BeautifulSoup
from collections import Counter

def remove_markdown(md: str) -> str:
    """
    Rimuove il Markdown da una stringa, restituendo solo il testo pulito.
    """
    if not md: 
        return ""
        
    # Converte il Markdown in HTML
    html = mistune.html(md)
    soup = BeautifulSoup(html, "html.parser")
    
    # get_text() estrae automaticamente tutto il testo eliminando i tag.
    # Usiamo lo spazio come separatore per evitare che parole adiacenti a tag si fondano.
    text = soup.get_text(separator=' ')
    
    # Collassa eventuali spazi multipli o nuove linee in un singolo spazio
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def tokenize(text: str) -> list:
    """Pulisce il testo e lo trasforma in una LISTA di token (mantenendo le ripetizioni)."""
    if not text:
        return []
    
    # Crea una tabella di traduzione per rimuovere la punteggiatura
    translator = str.maketrans('', '', string.punctuation)
    
    # Mette in minuscolo, rimuove la punteggiatura e divide in parole
    clean_text = text.lower().translate(translator)
    
    return clean_text.split()


def token_level_eval(parsed_text: str, gold_text: str) -> dict:
    """Calcola Precision, Recall e F1-Score tra due testi (privati del Markdown)."""
    
    # 1. Pulizia obbligatoria del Markdown (come richiesto dall'esonero)
    parsed_clean = remove_markdown(parsed_text)
    gold_clean = remove_markdown(gold_text)

    # 2. Tokenizzazione
    parsed_tokens = tokenize(parsed_clean)
    gold_tokens = tokenize(gold_clean)

    # 3. Gestione dei casi limite (testi vuoti)
    if not parsed_tokens and not gold_tokens:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not parsed_tokens or not gold_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    # 4. Calcolo dei True Positives tramite Counter (Multiset Intersection)
    # Esempio: se "gatto" compare 3 volte nel parser e 2 volte nel gold, il Counter
    # capisce che i match corretti per "gatto" sono 2.
    parsed_counts = Counter(parsed_tokens)
    gold_counts = Counter(gold_tokens)
    
    # L'operatore '&' tra Counter calcola proprio l'intersezione corretta (il minimo)
    common_counts = parsed_counts & gold_counts
    tp = sum(common_counts.values())

    # 5. Calcolo Metriche Finali
    precision = tp / len(parsed_tokens)
    recall = tp / len(gold_tokens)

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4)
    }
