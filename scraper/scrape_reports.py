import os
import sys
import time
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
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

# initializing requests session
r_obj = requests.Session()

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
countries_all = []
years_all = []
submission_dates_all = []
report_links_all = []
for count, link in enumerate(links):

    # extracting year
    s = result_set[count].contents[0]
    year = re.findall("\d*", s)[0]

    console.log(
        f"Trying: {link}, which is {count+1}/{len(links)}. Year: {year}")

    try:
        url = link
        r_soup = r_obj.get(url)
    # some links are not a real url but something like this: LinkClick.aspx?link=4751&tabid=9379&portalid=4&mid=13039
    # so we have to manually build an url by extracting year and link parameter (whatever that is)
    except requests.exceptions.RequestException as e:
        console.log(f"We need to build this url.")
        tab_id = re.findall("(?<=link=)(.*)(?=&tabid)", link)[0]
        url = f"http://www.basel.int/Countries/NationalReporting/NationalReports/BC{year}Reports/tabid/{tab_id}/Default.aspx"
        console.log(f"url: {url}")
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
    years = [year] * len(countries)
    css_selector = "td:nth-child(5)"
    # extracting and cleaning submission dates
    submission_dates = [x.contents[0].replace(
        u'\xa0', "") for x in soup.select(css_selector)]
    submission_dates = [datetime.strptime(
        x, "%d/%m/%Y %H:%M:%S") for x in submission_dates]

    countries_all = countries_all + countries
    years_all = years_all + years
    submission_dates_all = submission_dates_all + submission_dates
    report_links_all = report_links_all + report_links


console.log("Saving national repot meta data as data frame")
df = pd.DataFrame({"report_link": report_links_all, "country": countries_all,
                  "submission_date": submission_dates_all, "year": years_all})

df.to_csv("../output/national_reports.csv", index=False)


