import asyncio
from parsers.travelstategov import TravelStateGov

async def main():
    # URL di test
    url_test = "https://careers.state.gov/career-paths/civil-service/"
    
    print(f"🚀 Inizializzo il parser TravelStateGov...")
    parser = TravelStateGov()
    
    print(f"📥 Scaricamento ed estrazione in corso per: {url_test}")
    # Chiamiamo direttamente parse_single. Farà tutto da solo!
    risultato = await parser.parse_single(url_test)
    
    # Verifica che non ci siano errori
    if "ERRORE:" in risultato.get("parsed_text", ""):
        print(f"\n❌ Si è verificato un errore:")
        print(risultato["parsed_text"])
        return

    print("\n✅ Parsing completato con successo!")
    
    # Stampiamo a schermo una sintesi
    print("\n" + "="*50)
    print(" SINTESI DATI ESTRATTI")
    print("="*50)
    print(f"Dominio: {risultato.get('domain')}")
    print(f"Titolo:  {risultato.get('title')}")
    
    testo = risultato.get("parsed_text", "")
    print(f"\nTesto pulito (Anteprima 1000 caratteri):\n{testo[:5000]}\n")
    print(f"Lunghezza totale testo estratto: {len(testo)} caratteri")
    



if __name__ == "__main__":
    asyncio.run(main())