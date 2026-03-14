import requests
from bs4 import BeautifulSoup

url = "https://www.handbook.unsw.edu.au/undergraduate/programs/2024/3778"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
soup = BeautifulSoup(response.content, 'html.parser')
print(f"Title: {soup.title.string if soup.title else 'No title'}")

# Look for program structure or core courses
core_courses = soup.find_all('div', string=lambda t: t and 'Core' in t)
print(f"Found {len(core_courses)} elements with 'Core'")
