import requests
import json

# UNSW Handbook often uses an internal API like this for its search
# Let's try to query the curriculum structure directly
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json, text/plain, */*',
}

try:
    # First, let's try the public course search API to see if it responds
    url = "https://www.handbook.unsw.edu.au/api/content/render/false/query/+contentType:unsw_psubject%20+unsw_psubject.studyLevelURL:undergraduate%20+unsw_psubject.implementationYear:2026%20+unsw_psubject.code:COMP*/orderby/unsw_psubject.code%20asc/limit/10/offset/0"
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {data.get('contentlets', []).__len__()} courses")
    if data.get('contentlets'):
        course = data['contentlets'][0]
        print(f"Sample: {course.get('title')} ({course.get('code')})")
        print(f"Description snippet: {course.get('description', '')[:100]}...")
except Exception as e:
    print(f"Failed to access API: {e}")
