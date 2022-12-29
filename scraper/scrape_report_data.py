import os
import sys
import time
import re
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
import chromedriver_autoinstaller
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from rich.console import Console
from rich.progress import track
from datetime import datetime
import warnings


class NoData(Exception):
    pass


# initializing rich console
console = Console()

console.print("Hello :smiley:")
console.rule("")

# configuring selenium
# setting download folder
dl_folder = f"download"
# setting options
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

# using selenium to automate clicking on the right parts of the navbar and downloading excel file


def get_dfs(url, driver, dl_folder, country, year, count, maxi):
    console.log(
        f"trying national report {count}/{maxi}. Url: {url} belonging to {country} in year {year}")

    results = []

    driver.get(url)
    driver.implicitly_wait(2)

    for i in ["Export", "Import"]:

        dct = {}
        dct["error"] = ""
        try:
            element = WebDriverWait(driver, 12).until(
                EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), '{i} of hazardous wastes and other wastes')]")))
        except TimeoutException:
            raise NoData("Category button not clickable")

        element.click()

        try:
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight)")
            ignored_exceptions = (NoSuchElementException,
                                  StaleElementReferenceException,)
            export_btn = WebDriverWait(driver, 12, ignored_exceptions=ignored_exceptions)\
                .until(expected_conditions.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Export to Excel')]")))
            export_btn.click()
        except Exception as e:
            console.log(e)
            dct["error"] = e
            results.append(dct)
            continue

        # wating some time for file dl
        time.sleep(2)

        lst = os.listdir(dl_folder)
        if lst != []:
            f = lst[0]
        else:
            console.log("Nothing downloaded")
            dct["error"] = "Nothing downloaded"
            results.append(dct)
            continue

        try:
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                temp_df = pd.read_excel(f"{dl_folder}/{f}")
        except Exception as e:
            console.log("Something went wrong with the file")
            console.log(e)
            dct["error"] = "Something went wrong with the file"
            results.append(dct)
            continue

        for f in os.listdir(dl_folder):
            os.remove(os.path.join(dl_folder, f))

        temp_df["country"] = country
        temp_df["year"] = year

        # sometimes the column names are not exported correctly
        # also chance to rename them

        if year >= 2015:
            zero = "annex_2_8_9_code"
            one = "annex_1_code"
            two = "national_code"
            three = "type_of_waste"
            four = "annex_3_code"
            five = "amount"
            six = "countries_of_transit "
            if i == "Export":
                seven = "country_of_destination"
            if i == "Import":
                seven = "country_of_origin"
            eight = "annex_4_a_code"
            nine = "annex_4_b_code"

            temp_df = temp_df.rename(columns={temp_df.columns[0]: zero,  temp_df.columns[1]: one,  temp_df.columns[2]: two,  temp_df.columns[3]: three,
                                              temp_df.columns[4]: four,  temp_df.columns[5]: five,  temp_df.columns[6]: six,  temp_df.columns[7]: seven,  temp_df.columns[8]: eight,  temp_df.columns[9]: nine})
            temp_df = temp_df.rename(columns=lambda x: x.replace('\n', ''))
        else:
            zero = "annex_1_code"
            one = "waste_constituents"
            two = "annex_8_code"
            three = "un_class"
            four = "h_code"
            five = "characteristics"
            six = "amount"
            seven = "countries_of_transit"
            if i == "Export":
                eight = "country_of_destination"
            if i == "Import":
                eight = "country_of_origin"
            nine = "final_disposal_operation"
            ten = "recovery_operation"
            temp_df = temp_df.rename(columns={temp_df.columns[0]: zero,  temp_df.columns[1]: one,  temp_df.columns[2]: two,  temp_df.columns[3]: three,
                                              temp_df.columns[4]: four,  temp_df.columns[5]: five,  temp_df.columns[6]: six,  temp_df.columns[7]: seven,  temp_df.columns[8]: eight,  temp_df.columns[9]: nine})
            temp_df = temp_df.rename(columns=lambda x: x.replace('\n', ''))

        dct["df"] = temp_df
        results.append(dct)

    return results[0], results[1]


def download(reports):
    # initializing chrome driver
    chromedriver_autoinstaller.install()
    driver = webdriver.Chrome(options=op)
    failed = []
    frames_exports = []
    frames_imports = []
    for i in range(len(reports)):
        year = reports.loc[i, "year"]
        country = reports.loc[i, "country"]
        link = reports.loc[i, "report_link"]

        try:
            exports, imports = get_dfs(
                link, driver, dl_folder, country, year, i+1, len(reports))

        except NoData as e:
            failed.append(
                {"year": year, "country": country, "link": link, "reason": e})
            print(e)
            continue

        for count, i in enumerate([exports, imports]):
            kind = ["exports", "imports"][count]
            if i["error"] != "":
                failed.append(
                    {"year": year, "country": country, "link": link, "reason": i["error"], "kind": kind})
            else:
                i["df"].to_csv(
                    f"../output/single/{kind}/{year}_{country.replace(' ','_')}_{kind}.csv")
                exec(f"frames_{kind}.append({kind}['df'])")

    for i in ["exports", "imports"]:
        if eval(f"frames_{i}") != []:
            df = eval(f"pd.concat(frames_{i})")
            df.to_csv(f"../output/{i}.csv", index=False)

    failed = pd.DataFrame(failed)
    failed.to_csv("../output/all_failed.csv")

    driver.close()


reports = pd.read_csv("../output/national_reports.csv")
download(reports)
