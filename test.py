import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper() # Returns a CloudScraper instance
mpn = "GV-N3050OC-6GL"
r = scraper.get(f"https://www.scorptec.com.au/search/go?w={mpn}&cnt=1")
soup = BeautifulSoup(r.text, 'lxml')
print(soup.select_one("div.product-page-price.product-main-price"))
print(soup.select_one("div.product-page-model"))
print(r.url)