import sys
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import glob
from datetime import datetime
from datetime import date as dtdate
import numpy as np


def download_series_data():

    baseurl = "http://www.howstat.com/cricket/Statistics/Series/SeriesList.asp?"
    # yranges = [
    #     "2000010120091231&Range=2000%20to%202009",
    #     "2010010120191231&Range=2010%20to%202019",
    #     "2020010120291231&Range=2010%20to%202019",
    # ]
    yranges = ["2000010120091231&Range=2000%20to%202009"]
    # yrange_labs = ["2000_10", "2010_19", "2020_29"]
    yrange_labs = ["2010_19"]

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

    # yrange_labs = ["2000_10", "2010_19", "2020_29"]
    yrange_labs = ["2010_19"]

    df = pd.DataFrame()

    for yrange in yrange_labs:

        fname = "".join(["series_data_", yrange, ".html"])
        print(fname)

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

    # get the number of matches played since May 2010
    main_df = pd.read_csv("../../data/processed/aggregate_data.csv")
    main_df.date = pd.to_datetime(main_df.date)

    date_start = pd.to_datetime("2010/05/01")
    date_end = pd.to_datetime("2013/03/01")

    N_team_matches = {team: 0 for team in test_teams}
    team_ratings = N_team_matches

    for date in main_df.date:
        if date > date_start and date < date_end:
            N_row = main_df.loc[main_df.date == date]
            home_team = N_row.home_team.values[0]
            away_team = N_row.away_team.values[0]

            N_team_matches[home_team] += 1
            N_team_matches[away_team] += 1

    df_main = pd.DataFrame()
    for team in N_team_matches:

        rating = rankings_init.rating[rankings_init.team == team]
        ranking = rankings_init.ranking[rankings_init.team == team]

        df_tmp = pd.DataFrame(
            data={
                "date": date_end,
                "team": team,
                "ranking": ranking,
                "rating": rating,
                "tot_pts": rating * N_team_matches[team],
            }
        )

        df_main = df_main.append(df_tmp, ignore_index=True)

    return df_main


def get_end_series_date(start_date, num_matches, team_list):

    # reformat the date string
    day, month, year = start_date.split("/")
    start_date = "/".join([year, month, day])

    # get the name of the file
    os.chdir("/home/callow46/test_cricket_stats/data/raw/match_data/")
    os_cmd = "grep " + start_date + " *_info.csv"
    fname_tmp = os.popen(os_cmd).read().split("\n")

    if fname_tmp == [""]:
        return

    if len(fname_tmp) > 2:
        for file_ in fname_tmp:
            fname = file_.split("_")[0] + "_info.csv"
            with open(fname, "r") as f:
                lines = f.readlines()
                for line in lines:

                    if "info,team," in line:
                        team = line.split(",")[2].strip()
            if team in team_list:
                fname_final = fname.split("_")[0]
                break
    else:
        fname_final = fname_tmp[0].split("_")[0]

    # add the number of matches to the last character of the filename
    match_code = int(fname_final) + num_matches - 1
    while True:
        try:
            new_fname = str(match_code) + "_info.csv"
            open(new_fname)
            break
        except FileNotFoundError:
            match_code += 1

    # get the date of the final match
    with open(new_fname, "r") as f:
        lines = f.readlines()
        for line in lines:
            if "info,date" in line:
                end_date = line.split(",")[2].strip()

    return end_date


def aggregate_rankings_data():

    # get the initial data
    df = init_ratings_data()

    # loop through the series data
    series_df = pd.read_csv("../../data/interim/series_data.csv")
    ratings_df = pd.read_csv("../../data/processed/rankings_data.csv")

    for index, row in series_df.iterrows():

        date_end = get_end_series_date(
            row.date, row.num_matches, [row.home_team, row.away_team]
        )

        try:
            date = datetime.strptime(date_end, "%Y/%m/%d")
        except TypeError:
            break

        month_num = date.month
        month_str = date.strftime("%B").upper()
        year = date.year

        try:
            start_home_rating = float(
                ratings_df[
                    (ratings_df["year"] == year)
                    & (ratings_df["month"] == month_str)
                    & (ratings_df["team"] == row.home_team)
                ].rating
            )
        except TypeError:
            start_home_rating = 0.0

        try:
            start_away_rating = float(
                ratings_df[
                    (ratings_df["year"] == year)
                    & (ratings_df["month"] == month_str)
                    & (ratings_df["team"] == row.away_team)
                ].rating
            )
        except TypeError:
            start_away_rating = 0.0
        print(start_home_rating, start_away_rating)


if __name__ == "__main__":
    download_series_data()
    data = series_data_to_csv()

    # print(init_ratings_data())
    # get_end_series_date("06/03/2013", 3)

    # aggregate_rankings_data()
