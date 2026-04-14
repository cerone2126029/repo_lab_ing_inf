import string

def tokenize(text: str) -> set:
    """Pulisce il testo e lo trasforma in un set di token (parole)."""
    if not text:
        return set()
    
    # Crea una tabella di traduzione per rimuovere la punteggiatura
    translator = str.maketrans('', '', string.punctuation)
    
    # Mette in minuscolo e rimuove la punteggiatura
    clean_text = text.lower().translate(translator)
    
    # Divide il testo in parole. Usiamo set() per avere un insieme univoco di token
    return set(clean_text.split())

def token_level_eval(parsed_text: str, gold_text: str) -> dict:
    """Calcola Precision, Recall e F1-Score tra due testi."""
    parsed_tokens = tokenize(parsed_text)
    gold_tokens = tokenize(gold_text)

    # Gestione dei casi limite (testi vuoti)
    if not parsed_tokens and not gold_tokens:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not parsed_tokens or not gold_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    # True Positives: parole presenti in entrambi i set
    common_tokens = parsed_tokens.intersection(gold_tokens)
    tp = len(common_tokens)

    # Precision = Parole Corrette / Totale Parole Estratte
    precision = tp / len(parsed_tokens)

    # Recall = Parole Corrette / Totale Parole nel Gold Standard
    recall = tp / len(gold_tokens)

    # F1-Score = Media armonica tra Precision e Recall
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4)
    }