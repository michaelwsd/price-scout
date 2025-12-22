import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper() # Returns a CloudScraper instance
r = scraper.get("https://www.scorptec.com.au/search/go?w=BX8071512100F")
soup = BeautifulSoup(r.text, 'lxml')
print(soup.select_one("div.product-page-price.product-main-price"))
print(soup.select_one("span.status_text"))
print(r.url)