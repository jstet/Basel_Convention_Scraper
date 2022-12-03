import os
import sys
import time
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

class NoData(Exception):
    pass

dl_folder = f"{os.getcwd()}/download"

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


r_obj = requests.Session()
url = "http://ers.basel.int/ERS-Extended/FeedbackServer/webreportprint.aspx?reportid=ce3701bd61c4a2ea8d1e8fb5cb14a1e&startdate=&enddate=&filterid=38&filterlanguage=&reportlanguage="  # i.e. http://bisegrw.edu.pk/
r_soup = r_obj.get(url)

soup = BeautifulSoup(r_soup.content, "html.parser")

spans = soup.findAll("span")

links = [x.findAll("a", href=True)[1] for x in spans]

countries = [x.contents[0] for x in links]

root = "http://ers.basel.int/ERS-Extended/FeedbackServer/"

urls = [f"{root}{x['href']}" for x in links]

chromedriver_autoinstaller.install()

driver = webdriver.Chrome(options=op)

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
