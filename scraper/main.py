import requests
from bs4 import BeautifulSoup
import selenium
import pandas as pd

r_obj = requests.Session()
url = "http://ers.basel.int/ERS-Extended/FeedbackServer/webreportprint.aspx?reportid=ce3701bd61c4a2ea8d1e8fb5cb14a1e&startdate=&enddate=&filterid=38&filterlanguage=&reportlanguage=" # i.e. http://bisegrw.edu.pk/
r_soup = r_obj.get(url)

soup = BeautifulSoup(r_soup.content , "html.parser")

spans = soup.findAll("span")

links = [x.findAll("a", href=True)[1] for x in spans]

countries = [x.contents[0] for x in links]

root = "http://ers.basel.int/ERS-Extended/FeedbackServer/"

urls = [f"{root}{x['href']}" for x in links]

