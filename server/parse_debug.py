from bs4 import BeautifulSoup
with open("course_debug.html", "r") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

print("Title:", soup.title.string if soup.title else "No title")
h1s = soup.find_all("h1")
print("H1 tags:")
for h in h1s:
    print(f" - {h.text}")

print("Pre-reqs:")
for p in soup.find_all(string=lambda t: t and 'Prerequisite' in t):
    print(p.parent.text)
    
print("Fees:")
for p in soup.find_all(string=lambda t: t and 'Fee' in t):
    print(p.parent.text)

