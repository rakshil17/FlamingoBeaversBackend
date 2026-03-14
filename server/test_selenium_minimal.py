from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
url = "https://www.handbook.unsw.edu.au/undergraduate/programs/2026/3778"
print(f"Loading {url}")
driver.get(url)

try:
    print("Waiting for page body...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(5) # Hard sleep for dynamic content
    html = driver.page_source
    print(f"Loaded HTML length: {len(html)}")
    
    # Check for course codes explicitly
    codes = set(re.findall(r'[A-Z]{4}[0-9]{4}', html))
    print(f"Found {len(codes)} unique course codes.")
    if len(codes) > 0:
        print(f"Sample: {list(codes)[:5]}")
        
    titles = set(re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE))
    print(f"H1 Tags: {titles}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    driver.quit()
