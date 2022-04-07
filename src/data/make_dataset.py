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
import pandas as pd
import os
import glob
from datetime import datetime
from datetime import date as dtdate


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


def dfs_to_csv(
    year_start, year_end, outdir="../../data/processed/", outfile="rankings_data.csv"
):

    month_list = [
        "JANUARY",
        "FEBRUARY",
        "MARCH",
        "APRIL",
        "MAY",
        "JUNE",
        "JULY",
        "AUGUST",
        "SEPTEMBER",
        "OCTOBER",
        "NOVEMBER",
        "DECEMBER",
    ]

    data_agg = pd.DataFrame()

    for year in range(year_start, year_end + 1):

        for month in month_list:

            try:
                YM_data = get_rankings_data(year, month)
                data_agg = data_agg.append(YM_data, ignore_index=True)
            except AttributeError:
                pass

    data_agg.to_csv(outdir + outfile)

    return


def get_rankings_data(year, month, datadir="../../data/raw/"):

    fname = "".join([datadir, "rankings_data_", str(year), ".html"])

    with open(fname, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    for x in soup.find_all("a"):
        if x.get("name") == month:
            break

    table_description = x.next_sibling
    table_content = table_description.next_sibling

    team_list = []
    rankings_list = []
    ratings_list = []
    for row in table_content.contents:
        rowtext = row.text
        team = rowtext.strip("0123456789")
        ranklen = len(rowtext.rstrip("0123456789")) - len(team)
        try:
            rank = int(rowtext[:ranklen])
            rating = float(rowtext[len(rowtext.rstrip("0123456789")) :])
            team_list.append(team)
            rankings_list.append(rank)
            ratings_list.append(rating)
        except ValueError:
            pass

    month_list = len(team_list) * [month]
    year_list = len(team_list) * [year]

    output_dict = {
        "year": year_list,
        "month": month_list,
        "team": team_list,
        "ranking": rankings_list,
        "rating": ratings_list,
    }

    df = pd.DataFrame(data=output_dict)
    return df


def get_match_data(
    filename,
    venue_file="../../data/processed/venue_info.csv",
):

    with open(filename, "r") as f:
        lines = f.readlines()

    team_count = 0
    teams = ["a", "b"]
    for line in lines:

        if "info,team," in line:
            team = line.split(",")[2]
            teams[team_count] = team.strip()
            team_count += 1

        if "info,date" in line:
            dateraw = line.split(",")[2].strip()

        if "info,winner," in line:
            result = line.split(",")[2].strip()
        elif "info,outcome," in line:
            result = line.split(",")[2].strip()

        if "info,toss_winner," in line:
            toss_winner = line.split(",")[2].strip()

        if "info,venue," in line:
            venue = "".join(line.split(",")[2:])
            venue = venue.strip()
            df_venues = pd.read_csv(venue_file)
            home_team = df_venues.loc[venue].country

    teams.remove(home_team)
    away_team = teams[0]

    if result == home_team:
        result = "home"
    elif result == away_team:
        result = "away"
    if toss_winner == home_team:
        toss_winner = "home"
    elif toss_winner == away_team:
        toss_winner = "away"

    return [dateraw, home_team, away_team, result, toss_winner]


def merge_match_ranking_data(
    filename, date_min, date_max, rank_data_dir="../../data/processed/rankings_data.csv"
):

    match_data = get_match_data(filename)

    dateraw = match_data[0]
    home_team = match_data[1]
    away_team = match_data[2]

    date = datetime.strptime(dateraw, "%Y/%m/%d")

    if date.date() < date_min or date.date() > date_max:
        return pd.DataFrame()

    month_num = date.month
    month_str = date.strftime("%B").upper()
    year = date.year

    df_rankings = pd.read_csv(rank_data_dir)

    while month_num > 0:
        print(month_num)
        month_str = date.strftime("%B").upper()
        try:
            home_info = df_rankings.loc[
                (df_rankings["month"] == month_str)
                & (df_rankings["year"] == year)
                & (df_rankings["team"] == home_team)
            ]

            away_info = df_rankings.loc[
                (df_rankings["month"] == month_str)
                & (df_rankings["year"] == year)
                & (df_rankings["team"] == away_team)
            ]

            home_rank = int(home_info.ranking)
            home_rating = float(home_info.rating)
            away_rank = int(away_info.ranking)
            away_rating = float(away_info.rating)
        except TypeError:
            month_num -= 1
            date = date.replace(month=month_num)
            continue
        break

    data_dict = {
        "date": dateraw,
        "home_team": home_team,
        "away_team": away_team,
        "result": match_data[3],
        "toss": match_data[4],
        "home_rank": home_rank,
        "home_rating": home_rating,
        "away_rank": away_rank,
        "away_rating": away_rating,
    }
    df_out = pd.DataFrame(data=data_dict, index=[0])

    return df_out


def agg_data_to_csv(
    datadir="../../data/raw/match_data/",
    outdir="../../data/processed/",
    outfile="aggregate_data.csv",
):

    date_min = dtdate(2004, 3, 1)
    date_max = dtdate(2013, 3, 31)
    data_agg = pd.DataFrame()

    # list of all info files
    info_files = glob.glob(datadir + "*_info.csv")

    for info_file in info_files:
        print(info_file)

        match_rank_data = merge_match_ranking_data(info_file, date_min, date_max)
        data_agg = data_agg.append(match_rank_data, ignore_index=True)

    data_agg.to_csv(outdir + outfile)

    return


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

# print(get_rankings_data(year, month))

start_year = 2003
end_year = 2013

# download_rankings_data(start_year, end_year)
# dfs_to_csv(start_year, end_year)
# print(merge_match_ranking_data("258459_info.csv"))
print(agg_data_to_csv())
