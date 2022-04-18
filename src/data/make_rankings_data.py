import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd
import glob
from datetime import datetime
from datetime import date as dtdate
import numpy as np


def download_series_data():

    baseurl = "http://www.howstat.com/cricket/Statistics/Series/SeriesList.asp?"
    yranges = [
        "2010010120191231&Range=2010%20to%202019",
        "2020010120291231&Range=2010%20to%202019",
    ]
    yrange_labs = ["2010_19", "2020_29"]

    for i, yrange in enumerate(yranges):

        url = baseurl + yrange
        data_page = requests.get(url)
        soup = BeautifulSoup(data_page.content, "html.parser")
        soup.prettify()

        fname = "".join(["series_data_", yrange_labs[i], ".html"])

        with open(fname, "w") as f:
            f.write(str(soup))

    return


def series_data_to_csv():

    yrange_labs = ["2010_19", "2020_29"]

    df = pd.DataFrame()

    for yrange in yrange_labs:

        fname = "".join(["series_data_", yrange, ".html"])

        with open(fname, "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        for x in soup.find_all("a"):
            classname = x.get("class")

            if classname == ["LinkTable"]:
                teams = x.text.strip()
                date = x.find_next("td")
                date_text = date.text.strip()
                N_matches = date.find_next("td")
                N_matches_text = int(N_matches.text.strip())
                result = N_matches.find_next("td").text.strip()

                team_list = teams.split("v.")
                team_A = " ".join(team_list[0].split()[1:])
                team_B = team_list[1].lstrip()

                if "Drawn" in result:
                    [team_A_pts, team_B_pts] = list(
                        map(int, result.lstrip("Drawn").split("-"))
                    )
                elif team_A in result:
                    [team_A_pts, team_B_pts] = list(
                        map(int, result.lstrip(team_A).split("-"))
                    )
                elif team_B in result:
                    [team_B_pts, team_A_pts] = list(
                        map(int, result.lstrip(team_B).split("-"))
                    )
                else:
                    pass

                output_dict = {
                    "date": date_text,
                    "home_team": team_A,
                    "away_team": team_B,
                    "num_matches": N_matches_text,
                    "home_team_pts": team_A_pts,
                    "away_team_pts": team_B_pts,
                }

                df_tmp = pd.DataFrame(data=output_dict, index=[0])
                df = pd.concat([df, df_tmp], ignore_index=True)

    df.to_csv("../../data/interim/series_data.csv")

    return


def init_ratings_data():

    rank_df = pd.read_csv("../../data/processed/rankings_data.csv")

    rankings_init = rank_df[-9:]
    test_teams = rankings_init.team.to_list()
    test_rankings = rankings_init.rating.to_list()

    # get the number of matches played since May 2010
    main_df = pd.read_csv("../../data/processed/aggregate_data.csv")
    main_df.date = pd.to_datetime(main_df.date)

    date_start = pd.to_datetime("2010/05/01")
    date_end = pd.to_datetime("2013/03/01")

    N_team_matches = {team: 0 for team in test_teams}

    for date in main_df.date:
        if date > date_start and date < date_end:
            N_row = main_df.loc[main_df.date == date]
            home_team = N_row.home_team.values[0]
            away_team = N_row.away_team.values[0]

            N_team_matches[home_team] += 1
            N_team_matches[away_team] += 1


if __name__ == "__main__":
    # download_series_data()
    # data = series_data_to_csv()

    init_ratings_data()
