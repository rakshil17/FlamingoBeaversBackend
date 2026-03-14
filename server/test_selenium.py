from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def run():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    print("Setting up ChromeDriver...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    print("Fetching UNSW Handbook...")
    driver.get("https://www.handbook.unsw.edu.au/undergraduate/programs/2026/3778")
    
    try:
        # Wait for dynamic content to load, specifically the Core Courses section
        print("Waiting for courses to render...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Core Courses') or contains(text(), 'Structure')]"))
        )
        
        # Give React a second to finish painting
        time.sleep(2)
        
        # Let's try to find course codes on the page (matching 4 letters + 4 numbers)
        import re
        html = driver.page_source
        codes = set(re.findall(r'[A-Z]{4}[0-9]{4}', html))
        
        print(f"Found {len(codes)} unique course codes on the page!")
        print(f"Sample codes: {list(codes)[:10]}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run()
