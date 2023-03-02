import pycountry
import numpy as np


def normalize_country_names(x):
    # -- Cleaning and formatting country name strings to get recognized by pycountry --
    # removing whitespace from beginning and end so country names get recognized properly
    temp = x.strip()
    # e.g. "Venezuela (Bolivarian Republic of) -> "Venezuela, Bolivarian Republic of"
    temp = temp.replace(" (",", ").replace(")","")
    # Côte d´Ivoire --> Côte d'Ivoire
    temp = temp.replace("´", "'")
    # Handling
    if temp == "United Kingdom of Great Britain and Northern Ireland":
        temp = "United Kingdom"
    if temp == "Türkiye":
        temp = "Turkey"
    if temp == "Swaziland":
        temp = "Eswatini"
    if temp == "Republic of Moldova":
        temp = "Moldova, Republic of"
    if temp == "Democratic Republic of the Congo" or temp == "Congo, Democratic Republic of the" or temp == "Congo, Republic of the":
        temp = "Congo, The Democratic Republic of the"
    if temp == "State of Palestine":
        temp = "Palestine, State of"
    if temp == "Bolivia":
        temp = "Bolivia, Plurinational State of"
    if temp == "Hong Kong, China, SAR":
        temp = "Hong Kong"
    if temp == "Eswatini, Kingdom of":
        temp = "Eswatini"
    if temp == "Korea, Democratic People's Rep. of":
        temp = "Korea, Democratic People's Republic of"
    # -- Converting country name to alpha_2 code, which is what the other columns use --
    return pycountry.countries.get(name=temp).alpha_2.lower()