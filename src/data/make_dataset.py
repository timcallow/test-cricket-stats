# # -*- coding: utf-8 -*-
# import click
# import logging
# from pathlib import Path
# from dotenv import find_dotenv, load_dotenv


# @click.command()
# @click.argument('input_filepath', type=click.Path(exists=True))
# @click.argument('output_filepath', type=click.Path())
# def main(input_filepath, output_filepath):
#     """ Runs data processing scripts to turn raw data from (../raw) into
#         cleaned data ready to be analyzed (saved in ../processed).
#     """
#     logger = logging.getLogger(__name__)
#     logger.info('making final data set from raw data')


# if __name__ == '__main__':
#     log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#     logging.basicConfig(level=logging.INFO, format=log_fmt)

#     # not used in this stub but often useful for finding various files
#     project_dir = Path(__file__).resolve().parents[2]

#     # find .env automagically by walking up directories until it's found, then
#     # load up the .env entries as environment variables
#     load_dotenv(find_dotenv())

#     main()

import requests
from bs4 import BeautifulSoup


def download_rankings_data(year_start, year_end, outdir="../../data/raw/"):

    baseurl = (
        "https://web.archive.org/web/20130320093711/"
        + "http://www.icc-cricket.com/match_zone/test_ranking.php?year="
    )

    for year in range(year_start, year_end + 1):
        print("downloading rankings data for year ", year)
        url = baseurl + str(year)
        data_page = requests.get(url)
        soup = BeautifulSoup(data_page.content, "html.parser")
        soup.prettify()
        fname = "".join([outdir, "rankings_data_", str(year), ".html"])
        with open(fname, "w") as f:
            f.write(str(soup))

    return


def get_rankings_data(year, month, datadir="../../data/raw/"):

    team_names = {}
    team_rankings = {}
    team_ratings = {}
    
    fname = "".join([datadir, "rankings_data_", str(year), ".html"])

    with open(fname, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for x in soup.find_all("a"):
        if x.get("name") == month:
            break

    table_description = x.next_sibling
    table_content = table_description.next_sibling

    for row in table_content.contents:
        rowtext = row.text
        team = rowtext.strip("0123456789")
        ranklen = len(rowtext.rstrip("0123456789")) - len(team)
        try:
            rank = int(rowtext[:ranklen])
            rating = float(rowtext[len(rowtext.rstrip("0123456789")) :])
            test_team_data[team] = (rank, rating)
        except ValueError:
            pass

    #        tail = rowtext[len(head) :]
    #        print(head, tail)

    return test_team_data


# tests
test_teams = [
    "Australia",
    "England",
    "India",
    "Pakistan",
    "West Indies",
    "Sri Lanka",
    "New Zealand",
    "Bangladesh",
    "South Africa",
    "Zimbabwe",
]
year = 2004
month = "MAY"

print(get_rankings_data(year, month))

start_year = 2004
end_year = 2006


# download_rankings_data(start_year, end_year)
