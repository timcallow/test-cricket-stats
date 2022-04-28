import sys
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import glob
from datetime import datetime
from datetime import date as dtdate
import numpy as np
import urllib


def series_data_to_csv(raw_path, interim_path, proc_path):

    year_ranges = ["2000_09", "2010_19", "2020_29"]

    df = pd.DataFrame()

    for yrange in year_ranges:

        fname = "".join([raw_path, "series_data_", yrange, ".html"])

        with open(fname, "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # save a prettified version of the html file in interim data dir
        fname = "".join([interim_path, "series_data_", yrange, ".html"])
        soup.prettify()

        with open(fname, "w") as f:
            f.write(str(soup))

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

    # save the dataframe
    df.to_csv(proc_path + "series_data.csv")

    return


def init_ratings_data():

    rank_df = pd.read_csv("../../data/processed/rankings_data.csv")

    rankings_init = rank_df[-9:]
    test_teams = rankings_init.team.to_list()

    # get the number of matches played since May 2010
    main_df = pd.read_csv("../../data/processed/series_data.csv")
    main_df.date = pd.to_datetime(main_df.date, format="%d/%m/%Y")

    date_start = pd.to_datetime("2010/05/01")
    date_end = pd.to_datetime("2013/03/01")

    N_team_matches = {team: 0 for team in test_teams}
    team_ratings = N_team_matches

    for date in main_df.date:
        if date > date_start and date < date_end:
            N_row = main_df.loc[main_df.date == date]
            home_team = N_row.home_team.values[0]
            away_team = N_row.away_team.values[0]
            num_games = N_row.num_matches.values[0]

            if num_games > 1:
                N_team_matches[home_team] += num_games + 1
                N_team_matches[away_team] += num_games + 1

    df_main = pd.DataFrame()
    for team in N_team_matches:

        rating = rankings_init.rating[rankings_init.team == team].values[0]
        ranking = rankings_init.ranking[rankings_init.team == team].values[0]

        data = {
            "date": date_end,
            "team": team,
            "ranking": ranking,
            "rating": rating,
            "tot_pts": rating * N_team_matches[team],
        }

        df_tmp = pd.DataFrame(data, index=[0])
        df_main = pd.concat([df_main, df_tmp], ignore_index=True)

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
    # data = series_data_to_csv(
    #    "../../data/raw/series_data/", "../../data/interim/", "../../data/processed/"
    # )

    print(init_ratings_data())
    # get_end_series_date("06/03/2013", 3)

    # aggregate_rankings_data()


# def download_series_data(raw_data_path):

#     baseurl = "http://www.howstat.com/cricket/Statistics/Series/SeriesList.asp?"
#     # yranges = [
#     #     "2000010120091231&Range=2000%20to%202009",
#     #     "2010010120191231&Range=2010%20to%202019",
#     #     "2020010120291231&Range=2010%20to%202019",
#     # ]
#     yranges = ["2000010120091231&Range=2000%20to%202009"]
#     # yrange_labs = ["2000_10", "2010_19", "2020_29"]
#     yrange_labs = ["2010_19"]
#     user_agent = (
#         "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML"
#         + ", like Gecko) Chrome/99.0.4844.84 Safari/537.36"
#     )
#     accept_language = "en-US,en;q=0.9,es;q=0.8"
#     headers = {"user_agent": user_agent, "accept_language": accept_language}

#     for i, yrange in enumerate(yranges):

#         url = baseurl + yrange
#         data_page = requests.get(url, headers=headers)

#         # getting html
#         # req = urllib.request.Request(url, headers=headers)
#         # data_page = urllib.request.urlopen(req).read()
#         # print(data_page)
#         with open("test.html", "r") as f:
#             soup = BeautifulSoup(f, "html.parser")
#         soup.prettify()

#         fname = "".join(["series_data_", yrange_labs[i], ".html"])

#         with open(fname, "w") as f:
#             f.write(str(soup))

#     return
