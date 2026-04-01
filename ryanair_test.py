from scrapers.ryanair import RyanairScraper

scraper = RyanairScraper()
results = scraper.search("MAD")
print(f"\nFound {len(results)} flights:\n")
for f in results:
    print(f"  {f.destination_city} — €{f.price:.0f} ({f.outbound_date} to {f.return_date}, {f.nights}n) {f.duration}")
