import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper() # Returns a CloudScraper instance

def test_many():
    mpns = ["BX8071512400", "SNV3S-2000G", "BX8071512100F"]

    for mpn in mpns:
        r = scraper.get(f"https://www.scorptec.com.au/search/go?w={mpn}&cnt=1")
        soup = BeautifulSoup(r.text, 'lxml')
        print(soup.select_one("div.product-page-price.product-main-price"))
        print(soup.select_one("div.product-page-model"))
        print(r.url)

def test_single_scorptec(mpn):
    r = scraper.get(f"https://www.scorptec.com.au/search/go?w={mpn}&cnt=1")
    soup = BeautifulSoup(r.text, 'lxml')

    price_element = soup.select_one("div.product-page-price.product-main-price")
    model_element = soup.select_one("div.product-page-model")
    
    if model_element and model_element.get_text(strip=True) == mpn:
        print(f"MPN: {model_element.get_text(strip=True)}")
    else:
        print("MPN: Not found")
        return
    
    if price_element:
        print(f"Price: {price_element.get_text(strip=True)}")
    else:
        print("Price: Not found")

    print(f"URL: {r.url}")

def test_single_mwave(mpn):
    r = scraper.get(f"https://www.mwave.com.au/searchresult?button=go&w={mpn}&cnt=1")
    soup = BeautifulSoup(r.text, 'lxml')

    model_element = soup.select_one("span.sku")
    if model_element:
        model_number = model_element.get_text().split()[-1]
        print(model_number)
    else:
        print("MPN: Not found")
    
    price_element = soup.select_one("div.divPriceNormal")
    if price_element:
        price = price_element.get_text().strip().replace(",", "")[1:]
        print(price)
    else:
        print("Price: Not found")


if __name__ == "__main__":
    test_single_scorptec("100-300000077")
    test_single_mwave("100-300000077")