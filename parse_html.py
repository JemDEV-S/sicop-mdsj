from bs4 import BeautifulSoup
import sys

with open("page_output.html", "r") as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
print(soup.get_text(separator='\n', strip=True))
