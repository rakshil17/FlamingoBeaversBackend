import re
import json
import time
from typing import Dict, List, Set
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import argparse
import requests

# Base URLs for the target programs (Handbook)
URL_COMP_SCI = "https://www.handbook.unsw.edu.au/undergraduate/programs/2026/3778"
URL_SOFT_ENG = "https://www.handbook.unsw.edu.au/undergraduate/specialisations/2026/SENGAH"

# UNSW Timetable index pages — static HTML listing ALL courses by subject area
TIMETABLE_SUBJECT_URLS = [
    "https://timetable.unsw.edu.au/2026/COMPKENS.html",  # All COMP courses
    "https://timetable.unsw.edu.au/2026/SENGKENS.html",  # All SENG courses
]

def _setup_driver() -> webdriver.Chrome:
    """Configures and returns a headless Chrome webdriver."""
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
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def fetch_core_course_codes(driver: webdriver.Chrome, program_url: str) -> Set[str]:
    """Scrapes the program page to extract all unique course codes."""
    print(f"Fetching program structure from: {program_url}")
    driver.get(program_url)
    
    unique_codes = set()
    try:
        # The UNSW app takes a long time to hydrate. Wait up to 30 seconds for the body, then sleep just to let React inject elements.
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(8) 
        
        # Course codes uniquely match 4 uppercase letters + 4 digits in the text
        html = driver.page_source
        codes = re.findall(r'[A-Z]{4}[0-9]{4}', html)
        unique_codes.update(codes)
        print(f"Found {len(unique_codes)} unique course codes referenced on this page.")
    except Exception as e:
        print(f"Error fetching program structures from {program_url}: {e}")
        
    return unique_codes


def fetch_timetable_codes(subject_urls: List[str]) -> Set[str]:
    """Fetches all course codes from the static UNSW timetable index pages (no Selenium needed)."""
    all_codes = set()
    for url in subject_urls:
        print(f"Fetching timetable index from: {url}")
        try:
            res = requests.get(url, timeout=15)
            res.raise_for_status()
            codes = set(re.findall(r'[A-Z]{4}[0-9]{4}', res.text))
            all_codes.update(codes)
            print(f"Found {len(codes)} unique course codes from timetable.")
        except Exception as e:
            print(f"Warning: Could not fetch timetable page {url}: {e}")
    return all_codes


def scrape_course_details(driver: webdriver.Chrome, course_code: str) -> Dict:
    """Navigates to a specific course page and extracts its data."""
    # COMP9xxx are postgrad courses — use the postgraduate handbook URL
    course_num = int(course_code[4:])
    level = "postgraduate" if course_num >= 5000 else "undergraduate"
    url = f"https://www.handbook.unsw.edu.au/{level}/courses/2026/{course_code}"
    print(f"  -> Scraping: {course_code} ({level}) - {url}")
    driver.get(url)
    
    course_data = {
        "course_code": course_code,
        "title": "",
        "description": "",
        "department": "Computer Science and / or Software Eng",
        "instructor": "UNSW Faculty",
        "credits": 6,  # Default, will try to parse if possible
        "level": level,
        "semester": "",
        "tags": [],
        "prerequisites": [],
        "fees": {"domestic": "", "international": "", "hecs": ""}
    }
    
    try:
        # Wait specifically for the Course Title container to actually appear and have text
        WebDriverWait(driver, 15).until(
            lambda d: d.find_element(By.CSS_SELECTOR, "h2[data-testid='ai-header']").text.strip() != ""
        )
        time.sleep(1) # Extra buffer for elements popping in
        
        # 1. Title
        try:
            h2 = driver.find_element(By.CSS_SELECTOR, "h2[data-testid='ai-header']").text
            title = h2.replace(course_code, "").strip()
            course_data["title"] = title if title else f"Unknown Title ({course_code})"
        except Exception:
            course_data["title"] = f"Unknown Title ({course_code})"

        # 2. Description (Usually in a general info block)
        try:
            desc_elem = driver.find_element(By.CSS_SELECTOR, "div[data-testid='read-more-body'] p")
            desc_text = desc_elem.text.strip()
            course_data["description"] = desc_text
        except Exception:
            pass
            
        # 3. Credits (UOC)
        try:
            uoc_elem = driver.find_element(By.XPATH, "//h5[contains(text(), 'Units of Credit')]")
            num_match = re.search(r'\d+', uoc_elem.text)
            if num_match:
                course_data["credits"] = int(num_match.group())
        except Exception:
            pass
            
        # 4. Terms offered (Usually in an expanding "Offering Terms" block)
        try:
            terms_elem = driver.find_element(By.XPATH, "//h3[contains(text(), 'Offering Terms')]/following-sibling::div[@data-testid='AttrBody']/div[1]")
            course_data["semester"] = terms_elem.text.strip() or "Term 1, Term 2, Term 3"
        except Exception:
             course_data["semester"] = "Term 1, Term 2, Term 3"
             
        # 5. Prerequisites
        course_data["enrolment_rules"] = ""
        try:
            req_elem = driver.find_element(By.XPATH, "//*[@id='ConditionsforEnrolment']//div[contains(@class, 'CardBody')]")
            raw_req = req_elem.text.strip()
            raw_req = re.sub(r'^Prerequisite:\s*', '', raw_req)
            course_data["enrolment_rules"] = raw_req
            # Find all course codes in the prerequisite text
            course_data["prerequisites"] = list(set(re.findall(r'[A-Z]{4}[0-9]{4}', raw_req)))
        except Exception:
            pass
            
        # 6. Fees
        course_data["fees"] = {
            "domestic": "",
            "international": "",
            "hecs": ""
        }
        try:
            fee_rows = driver.find_elements(By.XPATH, "//table[@id='unswfeestable']//tbody/tr")
            for row in fee_rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) == 2:
                    fee_type = cols[0].text.strip().lower()
                    fee_amount = cols[1].text.strip()
                    if "commonwealth" in fee_type:
                        course_data["fees"]["hecs"] = fee_amount
                    elif "domestic" in fee_type:
                        course_data["fees"]["domestic"] = fee_amount
                    elif "international" in fee_type:
                        course_data["fees"]["international"] = fee_amount
        except Exception:
            pass
            
        # Basic tag generation based on title/desc
        combined_text = (course_data["title"] + " " + course_data["description"]).lower()
        base_tags = ["computer science", "software"]
        if "data" in combined_text: base_tags.append("data")
        if "algorithm" in combined_text: base_tags.append("algorithms")
        if "design" in combined_text: base_tags.append("design")
        if "system" in combined_text: base_tags.append("systems")
        course_data["tags"] = base_tags

    except Exception as e:
        print(f"    [!] Failed to fully scrape {course_code} (Might be 404 or missing data). Error: {type(e).__name__}")
        
    return course_data


import elastic_service

def push_to_elastic(course_data: Dict):
    """Pushes a scraped course dictionary directly to the local Elastic service."""
    try:
        res = elastic_service.add_course(course_data)
        if res.get("result") in ["created", "updated", "already_exists"]:
            print(f"    [+] Successfully deployed {course_data['course_code']} to Elastic Search.")
        else:
            print(f"    [!] Error deploying {course_data['course_code']}: {res}")
    except Exception as e:
        print(f"    [!] Connection error sending to backend: {e}")


def main():
    parser = argparse.ArgumentParser(description="UNSW Course Scraper")
    parser.add_argument("--limit", type=int, default=300, help="Max number of courses to scrape (-1 for all)")
    parser.add_argument("--no-push", action="store_true", help="Disable automatic pushing to ElasticSearch")
    args = parser.parse_args()

    driver = _setup_driver()
    
    # 1a. Grab course codes from the Handbook program pages (CS + SE)
    all_codes = set()
    all_codes.update(fetch_core_course_codes(driver, URL_COMP_SCI))
    all_codes.update(fetch_core_course_codes(driver, URL_SOFT_ENG))
    
    # 1b. Also pull ALL COMP/SENG codes from the static UNSW timetable index
    all_codes.update(fetch_timetable_codes(TIMETABLE_SUBJECT_URLS))
    
    codes_list = sorted(all_codes)
    # Filter strictly for COMP/SENG/MATH/DESN/ENGG courses
    codes_list = [c for c in codes_list if c.startswith(("COMP", "SENG", "MATH", "DESN", "ENGG"))]
    print(f"\nTotal unique courses discovered: {len(codes_list)}")
    
    if args.limit > 0:
        codes_list = codes_list[:args.limit]
        print(f"Limiting to first {args.limit} courses...\n")
        
    results = []
    
    # 2. Iterate and deep-scrape each
    for code in codes_list:
        data = scrape_course_details(driver, code)
        results.append(data)
        
        if not args.no_push:
            push_to_elastic(data)
            
    driver.quit()
    
    # 3. Save to disk
    out_file = "scraped_courses.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nScraping complete! Dumped {len(results)} courses to {out_file}.")


if __name__ == "__main__":
    main()
