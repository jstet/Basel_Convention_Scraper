import os
import sys
import time
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
import chromedriver_autoinstaller
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from rich.console import Console
from rich.progress import track
from datetime import datetime

class NoData(Exception):
    pass

# initializing rich console
console = Console()

console.print("Hello :smiley:")
console.rule("")

# configuring selenium
## setting download folder
dl_folder = f"{os.getcwd()}/download"
## setting options
op = webdriver.ChromeOptions()
op.add_argument('--no-sandbox')
op.add_argument('--verbose')
op.add_argument("--disable-notifications")
op.add_experimental_option("prefs", {
    "download.default_directory": dl_folder,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True})
op.add_argument('--disable-gpu')
op.add_argument('--disable-software-rasterizer')
op.set_capability('unhandledPromptBehavior', 'accept')
op.add_argument('--headless')
## initializing chrome driver
chromedriver_autoinstaller.install()
driver = webdriver.Chrome(options=op)

# initializing requests session
r_obj = requests.Session()

def get_soup(url, r_obj):
    return r_obj.get(url)

# using beautiful soup to retreive country report overview pages for all years
# first page
url = "http://www.basel.int/Countries/NationalReporting/NationalReports/BC2021Reports/tabid/9379/Default.aspx"
# selector retreived with scrape mate plugin
css_selector = "#dnn_LeftColumn .Normal"
r_soup = r_obj.get(url)
soup = BeautifulSoup(r_soup.content, "html.parser")
result_set = soup.select(css_selector)
links = [x["href"] for x in result_set]

# looping over country report overview pages for all years
root = "http://ers.basel.int/ERS-Extended/FeedbackServer/"
national_reports_dcts = []
countries_all = []
years_all = []
submission_dates_all = []
report_links_all = []
for count,link in enumerate(links): 
    
    # extracting year
    s = result_set[count].contents[0]
    year = re.findall("\d*", s)[0] 

    console.log(f"Trying: {link}, which is {count+1}/{len(links)}. Year: {year}")  
    
    try:
        url = link
        r_soup = r_obj.get(url)
    # some links are not a real url but something like this: LinkClick.aspx?link=4751&tabid=9379&portalid=4&mid=13039 
    # so we have to manually build an url by extracting year and tab_id (whatever that is)
    except requests.exceptions.RequestException as e:    
        console.log(f"We need to build this url.")   
        tab_id = re.findall("(?<=tabid=)(.*)(?=&portal)", link)[0]
        url = f"http://www.basel.int/Countries/NationalReporting/NationalReports/BC{year}Reports/tabid/{tab_id}/Default.aspx"
        r_soup = r_obj.get(url)
    
    # the country reports are embedded in a iframe, so we cant retreive links directly with beautiful soup
    # we need to extract the source url of the iframe and navigate to it
    soup = BeautifulSoup(r_soup.content, "html.parser")
    iframe_url = soup.findAll("iframe")[1]["src"]
    
    r_soup = r_obj.get(iframe_url)
    soup = BeautifulSoup(r_soup.content, "html.parser")
    
    # extracting report links, corresponding countries and submission dates
    spans = soup.findAll("span")
    temp_links = [x.findAll("a", href=True)[1] for x in spans]
    report_links = [f"{root}{x['href']}" for x in temp_links]
    countries = [x.contents[0] for x in temp_links]
    css_selector = "td:nth-child(5)"
    # extracting and cleaning submission dates
    submission_dates = [x.contents[0].replace(u'\xa0', "") for x in soup.select(css_selector)]
    submission_dates = [datetime.strptime(x, "%d/%m/%Y %H:%M:%S") for x in submission_dates]
    
    national_reports_dcts.append({"report_links":report_links,"countries": countries, "submission_dates": submission_dates})
    
    countries_all = countries_all + countries
    years_all = years_all + [year] * len(countries)
    submission_dates_all = submission_dates_all + submission_dates
    report_links_all = report_links_all + report_links
    

console.log("Saving national repot meta data as data frame")
df = pd.DataFrame({"report_link":report_links_all,"country": countries_all, "submission_date": submission_dates_all, "year": years_all})
    
df.to_csv("../data/national_reports.csv", index=False)

root = "http://ers.basel.int/ERS-Extended/FeedbackServer/"

urls = [f"{root}{x['href']}" for x in links]

def get_df(url, driver, dl_folder, countries, count):
    print(f"trying url: {url} belonging to {countries[count]}")

    driver.get(url)

    id_ = "ctl06_RespondentAnswers_82_PageBoxPageNavigatorBehavior_PageNavigator1_12"

    driver.implicitly_wait(3)

    try:
        element = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, id_)))
    except TimeoutException:
        raise NoData("category button not clickable")

    element.click()

    id_ = "ctl06_RespondentAnswers_82_Question33379_SectionGrid33379_PrintAnswersLinkButton"

    try:
        categ_btn = driver.find_element(By.ID, id_)
    except NoSuchElementException:
        raise NoData("Couldn't find excel export button")
        
    try:
        element = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, id_)))
    except TimeoutException:
        raise NoData("Excel export button not clickable")

    element.click()
    
    time.sleep(4)
    
    try:
        ex_f = os.listdir(dl_folder)[0]
        temp_df = pd.read_excel(f"{dl_folder}/{ex_f}", index_col=0)  
    except Exception as e:
        raise NoData("Something went wrong with the file")
    
    temp_df["Exporting_Country"] = countries[count]
    
    for f in os.listdir(dl_folder):
        os.remove(os.path.join(dl_folder, f))
    
    return temp_df
    
frames = []
failed = []

for count, url in enumerate(urls):
    try:
        temp_df = get_df(url, driver, dl_folder, countries, count)
    except NoData as e:
        failed.append({"country": countries[count], "reason": e})
        print(e)
        print("skipping")
        continue
    frames.append(temp_df)

failed = pd.DataFrame(failed)

df = pd.concat(frames)

df.to_csv("result.csv")  
failed.to_csv("failed.csv")  

driver.close()
