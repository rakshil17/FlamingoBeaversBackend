from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://www.handbook.unsw.edu.au/undergraduate/programs/2026/3778?year=2026")
        page.wait_for_selector("text=Core Courses", timeout=10000)
        print("Page title:", page.title())
        html = page.content()
        print("Length of HTML:", len(html))
        browser.close()

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print("Error:", e)
