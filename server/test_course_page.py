from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

print("Starting driver...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
url = "https://www.handbook.unsw.edu.au/undergraduate/courses/2026/COMP2511"
print(f"Loading {url}")
driver.get(url)
time.sleep(10) # Let it settle
print(f"Page Title: {driver.title}")
try:
    h1 = driver.find_element(By.CSS_SELECTOR, "h1")
    print(f"H1 Text: '{h1.text}'")
except Exception as e:
    print(f"No H1 found: {e}")

html = driver.page_source
with open("course_debug.html", "w") as f:
    f.write(html)
print(f"Dumped HTML. Length: {len(html)}")
driver.quit()
