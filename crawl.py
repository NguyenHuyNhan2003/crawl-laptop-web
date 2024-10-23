import os
import re
import csv
import time
import shutil
import random
import requests
import pandas as pd
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC


from csv_function import save_brands_to_csv, save_product_links_to_csv, read_brand_links_from_csv, read_product_links_from_csv, save_product_info_to_csv

webpage_url = 'https://cellphones.com.vn/laptop.html'

def random_sleep():
    sleep(random.randint(2, 5))
    
def element_xpath_exists(driver, xpath):
    try:
        driver.find_element(By.XPATH, xpath)
        return True  # Element exists
    except NoSuchElementException:
        return False  # Element does not exist
    
def element_class_name_exists(driver, class_name):
    try:
        driver.find_element(By.CLASS_NAME, class_name)
        return True  # Element exists
    except NoSuchElementException:
        return False  # Element does not exist

# main functions
def get_brands(driver):
    brand_list = crawl_brands(driver)
    print(f"Got a total of {len(brand_list)} brands")
    
    save_brands_to_csv(brand_list)
    
def get_brand_product_links(driver):
    brand_list = read_brand_links_from_csv()
    total = 0
    
    for brand in brand_list:
        brand_link = brand['brand_link']
        brand_name = brand['brand_name']
        
        # get products of each brand
        print(f"Getting products of {brand_name}")
        product_link_list = crawl_brand_product_links(driver, brand_link, brand_name)
        print(f"Got a total of {len(product_link_list)} product links from {brand_name}")
        total += len(product_link_list)
        
        # save products to CSV
        save_product_links_to_csv(product_link_list, brand_name)
        random_sleep()
        
    print(f"Got a total of {total} products")

def process_product_link(driver, brand_name, links):
    product_info_list = []
    for link in links:
        print(f"Processing link for {brand_name}: {link}")

        product_info = crawl_product_info(driver, link)
        product_info_list.append(product_info)
        
        random_sleep()
        
    save_product_info_to_csv(product_info_list, brand_name)

def process_each_brand_links(driver, product_link):
    for brand_name, links in product_link.items():
        print(f"{brand_name}: {len(links)}")
        
        process_product_link(driver, brand_name, links)
       
def get_product_info(driver):
    product_links = read_product_links_from_csv()
    
    for product_link in product_links:
        process_each_brand_links(driver, product_link)

# webdriver functions
def initDriverProfile():
    # Đường dẫn đến thư mục chứa file python hiện tại
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # Đường dẫn đến file chromedriver.exe
    CHROMEDRIVER_PATH = current_directory + "\chromedriver.exe"
    Service = webdriver.chrome.service.Service(CHROMEDRIVER_PATH)
    Options = webdriver.ChromeOptions()
    Options.add_argument('--no-sandbox')
    Options.add_argument("--disable-blink-features=AutomationControllered")
    Options.add_experimental_option('useAutomationExtension', False)
    prefs = {"profile.default_content_setting_values.notifications": 2}
    Options.add_experimental_option("prefs", prefs)
    Options.add_argument("--disable-dev-shm-usage")
    Options.add_experimental_option("excludeSwitches", ["enable-automation"])
    Options.add_argument("--ignore-certificate-errors")
    Options.add_argument("--disable-web-security")
    Options.add_argument("--allow-running-insecure-content")
    # Ẩn chrome
    Options.add_argument('--disable-headless')
    # không hiển thị thông báo đăng nhập chrome
    Options.add_argument("--disable-infobars")
    # Hiển thị lớn nhất trình duyệt
    Options.add_argument("--start-minimized")
    # không hiển thị thông báo extensions
    Options.add_argument("--disable-extensions")
    driver = webdriver.Chrome(service=Service, options=Options,keep_alive=True)
    return driver

def crawl_brands(driver):
    brand_list = []
    
    driver.get(webpage_url)
    
    wait = WebDriverWait(driver, 10)
    brands = wait.until(EC.presence_of_all_elements_located((
        By.XPATH, '//*[@id="layout-desktop"]/div[3]/div[2]/div/div[4]/div[1]/div/a'
    )))
    
    for brand in brands:
        try:
            # link to brand laptop
            brand_link = brand.get_attribute('href')
            
            # brand logo link
            img_tag = brand.find_element(By.TAG_NAME, 'img')
            brand_img_link = img_tag.get_attribute('src')
            
            # brand name
            brand_name = img_tag.get_attribute('alt')
            
            # append to list
            brand_list.append({
                'brand_name': brand_name, 
                'brand_link': brand_link, 
                'brand_img_link': brand_img_link
            })
        except Exception as e:
            print(f"Error processing brand: {e}")
            continue
        
    return brand_list

def crawl_brand_product_links(driver, brand_link, brand_name):
    product_link_list = []
    
    driver.get(brand_link)
    
    wait = WebDriverWait(driver, 10)
    
    # display full product page
    try_count = 0
    while(True):
        try:
            
            show_more_button = wait.until(EC.element_to_be_clickable((
                By.XPATH, '//*[@id="layout-desktop"]/div[3]/div[2]/div/div[4]/div[5]/div/div[2]/a'
            )))
            show_more_button.click()
            
            if try_count > 20:
                break
            
            try_count += 1
            random_sleep()
            
        except Exception as e:
            break
    
    # get all product containers
    product_container = driver.find_elements(
        By.CLASS_NAME, 
        'product-info-container'
    )

    for product in product_container:
        product_info = product.find_element(By.CLASS_NAME, 'product-info')
        
        # get product link
        product_link = product_info.find_element(By.TAG_NAME, 'a').get_attribute('href')
        product_link_list.append(product_link)
        
    return product_link_list

def crawl_product_info(driver, product_link):
    driver.get(product_link)
    wait = WebDriverWait(driver, 20)
    
    # initialize variables
    # name
    product_name = ''
    # price
    discount_price = None
    actual_price = None
    # specifications
    crawl_description = ''
    crawl_processor = ''
    crawl_ram = ''
    crawl_storage = ''
    crawl_graphic_card = ''
    crawl_display_size = ''
    crawl_battery = ''
    crawl_resolution = ''
    crawl_ports = ''
    crawl_operating_system = ''
    # image link
    crawl_image_link = ''

    # get product name
    product_name = wait.until(EC.presence_of_element_located((
        By.XPATH, '//*[@id="productDetailV2"]/section/div[1]/div[1]/h1'
    ))).text
    
    # get product price
    class_name = 'product__price--show'
    if element_class_name_exists(driver, class_name):
        actual_price = wait.until(EC.presence_of_element_located((By.CLASS_NAME, class_name))).text
        discount_price = actual_price
    
    class_name = 'product__price--through'
    if element_class_name_exists(driver, class_name):
        actual_price = wait.until(EC.presence_of_element_located((By.CLASS_NAME, class_name))).text
    
    class_name = 'tpt---sale-price'
    xpath = '//*[@id="trade-price-tabs"]/div/div/div[2]/p[1]'
    if element_xpath_exists(driver, xpath):
        actual_price = wait.until(EC.presence_of_element_located((By.XPATH, xpath))).text
        discount_price = actual_price
        
    class_name = 'tpt---price'
    if element_class_name_exists(driver, class_name):
        actual_price = wait.until(EC.presence_of_element_located((By.CLASS_NAME, class_name))).text
    
    # description
    xpath = '//*[@id="cpsContent"]/div[1]/div/ul'
    if element_xpath_exists(driver, xpath):
        description_container = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        description_list = description_container.find_elements(By.TAG_NAME, 'li')
        
        for description in description_list:
            crawl_description = crawl_description + description.text + '\n'
    
    # get product specifications

    # get image link
    
    # get image count
    # xpath = '//*[@id="productDetailV2"]/section/div[2]/div[1]/div[1]/div[1]/div[2]/div'
    # image_slider = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    # image_div_list = image_slider.find_elements(By.TAG_NAME, 'div')
    # image_count = len(image_div_list)
    
    
    return {
        'product_name': product_name,
        'actual_price': actual_price,
        'discount_price': discount_price,
        'description': crawl_description,
        'processor': crawl_processor, # CPU
        'ram': crawl_ram, # Dung lượng RAM
        'storage': crawl_storage, # Ổ cứng
        'graphic_card': crawl_graphic_card, # Loại card đồ họa
        'display_size': crawl_display_size, # Kích thước màn hình
        'battery': crawl_battery, # Pin
        'resolution': crawl_resolution, # Độ phân giải màn hình
        'ports': crawl_ports, # Cổng giao tiếp
        'operating_system': crawl_operating_system, # Hệ điều hành
        'image_link': crawl_image_link,
        'product_link': product_link
    }
    
def test():
    driver = initDriverProfile()
    product_link =[
    'https://cellphones.com.vn/laptop-msi-gaming-gf63-thin-12uc-803vn.html',
    'https://cellphones.com.vn/macbook-pro-14-inch-m3-max-96gb-512gb-sac-96w.html',
    'https://cellphones.com.vn/laptop-dell-xps-15-9520.html',
    'https://cellphones.com.vn/laptop-dell-inspiron-15-3530-n5i5407w1.html'   
    ] 
    
    info = crawl_product_info(driver, product_link[2])
    
    driver.quit()
    
    # print(info)

def start(option):
    driver = initDriverProfile()
    
    match option:
        case 1: # get brands
            get_brands(driver)
        case 2: # get products per brand
            get_brand_product_links(driver)
        case 3:# get product info
            get_product_info(driver)   
        case _:
            print("Invalid option")
    
    driver.quit()

if __name__ == "__main__":
    start(3)
    # test()
    
# py crawl.py   .venv/Scripts/activate