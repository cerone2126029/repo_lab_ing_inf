import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://pypi.org/project/crawl4ai/")

        if result.success:
            print("\n Funziona! Ecco il contenuto:")
            print(result.markdown[:500])
        else:
            print(f"Errore: {result.error_}")

if __name__ == "__main__":
    asyncio.run(main())