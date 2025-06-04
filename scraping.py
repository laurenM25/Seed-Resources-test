import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import csv
import time

#access HTML content from Johhny's Seeds Webpage

seeds = []
driver = webdriver.Chrome()

def get_product_count(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content,"html.parser")
    product_count = soup.find('span',class_='results-counter').text.strip().split()[0].strip()
    product_count = product_count.replace(",","")
    try:
        product_count = int(product_count)
    except ValueError as e:
        print(f"Error: {e}")
    return product_count


def create_soup(url, use_selenium = False):
    url += f"?start=0&sz={get_product_count(url)}" #show all entries on page

    if use_selenium == True: #gives me fully rendered DOM
        driver.get(url)
        time.sleep(3)  # let the JS load
        soup = BeautifulSoup(driver.page_source,"html.parser")
    else:
        response = requests.get(url)
        soup = BeautifulSoup(response.content,"html.parser")
    return soup
    
def scrape_generic_variety(soup): 
    new_list = []
    table = soup.find('div',attrs = {'class': 'row cat-grid'})
    for item in table.find_all('div', attrs= {'class': 'region col-6 col-lg-4'}):
        generic_seed = {}
        generic_seed['name'] = item.h2.text.strip()
        url = item.a['href'].strip()
        generic_seed['url'] = url
        generic_seed['specific-varieties'] = scrape_specific_varieties(url) #get specific varieties, their QR and photo urls
        new_list.append(generic_seed)
    return new_list
    
def scrape_specific_varieties(url):
    soup = create_soup(url, use_selenium=True)
    new_list = []
    table = soup.find('div',attrs = {'class': 'row product-grid'})
    for item in table.find_all('div', attrs={'class': 'product-tile'}):
        seed_specifics = {}
        seed_specifics['variety-name'] = item.find('div', class_='tile-name product-name').text.strip()
        seed_specifics["QR-url"] = item.find('a', class_='tile-name-link')['href']
        seed_specifics["plant-photo-url"] = item.find('img')['src']
        new_list.append(seed_specifics)
    return new_list

# now scrape for herbs
soup = create_soup('https://www.johnnyseeds.com/herbs/')
seeds.extend(scrape_generic_variety(soup))

time.sleep(5) #give break
# veggies
soup = create_soup('https://www.johnnyseeds.com/vegetables/')
seeds.extend(scrape_generic_variety(soup))

# fruits
soup = create_soup('https://www.johnnyseeds.com/fruits/')
seeds.extend(scrape_generic_variety(soup))

# flower
soup = create_soup('https://www.johnnyseeds.com/flowers/')
seeds.extend(scrape_generic_variety(soup))

# farm seed
soup = create_soup('https://www.johnnyseeds.com/farm-seed/')
seeds.extend(scrape_generic_variety(soup))

filename = 'scraped_seeds.csv'
with open(filename, 'w', newline='') as f:
    w = csv.DictWriter(f,['name','url','specific-varieties'])
    w.writeheader()
    for seed in seeds:
        w.writerow(seed)

