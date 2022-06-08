"""
WIP: This file is intended to compute the rankings data for the missing
years (2013 - present), based on initial data about rankings and total
number of matches played.
"""

import os
from bs4 import BeautifulSoup
import pandas as pd
import datetime


def series_data_to_csv(raw_path, interim_path, proc_path):
    """
    Convert series data in html formats to single csv file.

    Parameters
    ----------
    raw_path : str
        raw data path
    interim_path : str
        interim data path
    proc_path : str
        processed data path

    Returns
    -------
    None
    """

    # each html file references a different decade
    year_ranges = ["2000_09", "2010_19", "2020_29"]

    df = pd.DataFrame()

    # loop over the html files
    for yrange in year_ranges:

        # read html file
        fname = "".join([raw_path, "series_data_", yrange, ".html"])
        with open(fname, "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # save a prettified version of the html file in interim data dir
        fname = "".join([interim_path, "series_data_", yrange, ".html"])
        soup.prettify()
        with open(fname, "w") as f:
            f.write(str(soup))

        # find the rows of the table with series information
        for x in soup.find_all("a"):
            classname = x.get("class")

            if classname == ["LinkTable"]:

                # names of teams from text
                teams = x.text.strip()

                # date from text
                date = x.find_next("td")
                date_text = date.text.strip()

                # match number from text
                N_matches = date.find_next("td")
                N_matches_text = int(N_matches.text.strip())

                # match result from text
                result = N_matches.find_next("td").text.strip()

                # split the teams
                team_list = teams.split("v.")
                team_A = " ".join(team_list[0].split()[1:])
                team_B = team_list[1].lstrip()

                # get the number of points for each team from the series result
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

                # make dictionary and convert to dataframe
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

    # save the dataframe as csv
    df.to_csv(proc_path + "series_data.csv")

    return


def init_ratings_data(proc_path):
    """
    Compute the number of ratings points at the last known rankings data (03/2013).

    Parameters
    ----------
    proc_path : str
        the data path for processed data

    Returns
    -------
    df_main : pandas dataframe
        the dataframe containing the initial points, rating and rankings data

    Notes
    -----
    Ratings are equal to the total number of points divided by matches played.
    The counting period dates back to the May from four years previously, so for
    March 2013 all matches from May 2010 are counted to get the total.
    If a series has more than one match, an extra match is added to the total
    because an extra point is available to the series winner.
    """

    # read in the main data file
    rank_df = pd.read_csv(proc_path + "rankings_data.csv")
    # extract the information as of March 2013
    rankings_init = rank_df[-9:]

    date_end = "2013/02/28"
    N_team_matches = count_matches_from(date_end, proc_path)

    # create the dataframe with rating, ranking and total points data
    df_main = pd.DataFrame()
    for team in N_team_matches:

        rating = rankings_init.rating[rankings_init.team == team].values[0]
        ranking = rankings_init.ranking[rankings_init.team == team].values[0]

        data = {
            "date": date_end,
            "team": team,
            "ranking": ranking,
            "rating": rating,
            "matches": N_team_matches[team],
            "tot_pts": rating * N_team_matches[team],
        }

        # convert to df and concatenate
        df_tmp = pd.DataFrame(data, index=[0])
        df_main = pd.concat([df_main, df_tmp], ignore_index=True)

    return df_main


def count_matches_from(date, proc_path):

    r"""Count the number of matches contributing to rankings points at a given date."""

    # get the number of matches played between May 2010 and March 2013
    main_df = pd.read_csv(proc_path + "series_data.csv")
    main_df["datenew"] = pd.to_datetime(main_df.date, format="%d/%m/%Y").dt.date

    # convert date to a datetime object
    date_end = pd.to_datetime(date)

    # get a list of the test teams
    test_teams = list(set(main_df.home_team))

    # retrieve the starting date
    if date_end.month >= 5:
        date_mid_year = date_end.year - 1
    else:
        date_mid_year = date_end.year - 2

    date_start_year = date_mid_year - 2

    date_mid = datetime.date(date_mid_year, 5, 1)
    date_start = datetime.date(date_start_year, 5, 1)

    main_df = main_df[(main_df.datenew >= date_start) & (main_df.datenew <= date_end)]

    # initialize match count and ratings
    N_team_matches = {team: 0 for team in test_teams}

    for datenew in main_df.datenew:
        N_row = main_df.loc[main_df.datenew == datenew]
        home_team = N_row.home_team.values[0]
        away_team = N_row.away_team.values[0]
        num_games = N_row.num_matches.values[0]
        startdate = N_row.date.values[0]
        try:
            end_series_date = datetime.datetime.strptime(
                get_end_series_date(startdate, num_games, [home_team, away_team]),
                "%Y/%m/%d",
            )
            end_series_date = datetime.date(
                end_series_date.year, end_series_date.month, end_series_date.day
            )
        except TypeError:
            pass

        if end_series_date >= date_mid and end_series_date <= date_end:

            # assign an extra number to the total count for series > 1 game
            if num_games > 1:
                N_team_matches[home_team] += num_games + 1
                N_team_matches[away_team] += num_games + 1

        elif end_series_date >= date_start and end_series_date < date_mid:

            # assign an extra number to the total count for series > 1 game
            if num_games > 1:
                N_team_matches[home_team] += 0.5 * (num_games + 1)
                N_team_matches[away_team] += 0.5 * (num_games + 1)

    # remove teams who played no matches in that period
    N_team_matches = {k: v for k, v in N_team_matches.items() if v != 0}

    return N_team_matches


def get_end_series_date(start_date, num_matches, team_list):
    """
    Calculate the end date of a test series from the start date and match number.

    Parameters
    ----------
    start_date : str
        start date in format dd/mm/yyyy
    num_matches : int
        number of matches in the test series
    team_list : list
        the teams contesting the series

    Returns
    -------
    end_date : str
       end date in format yyyy/mm/dd
    """

    # reformat the date string
    day, month, year = start_date.split("/")
    start_date = "/".join([year, month, day])

    # get the names of all files with the given start date
    cwd = os.getcwd()
    os.chdir("/home/callow46/test_cricket_stats/data/raw/match_data/")
    os_cmd = "grep " + start_date + " *_info.csv"
    fname_tmp = os.popen(os_cmd).read().split("\n")

    if fname_tmp == [""]:
        return

    # if more than one file has the given start date:
    # loop over them all until the one with correct teams is found
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
    # usually the matches in a serious monototically increase by one in the filenames
    # if they don't, keep increasing until the true last file is found
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
    os.chdir(cwd)
    return end_date


def calc_points(num_matches, home_score, away_score, home_rating, away_rating):

    if num_matches == 1:
        return [0.0, 0.0]

    # add half a point for each drawn game
    num_draws = num_matches - (home_score + away_score)
    home_score += 0.5 * num_draws
    away_score += 0.5 * num_draws

    # add bonus points for series result
    if home_score > away_score:
        home_score += 1
    elif home_score == away_score:
        home_score += 0.5
        away_score += 0.5
    else:
        away_score += 1

    # if the home and away ratings are within 40 points
    if abs(home_rating - away_rating) < 40:
        home_points = home_score * (away_rating + 50) + away_score * (away_rating - 50)
        away_points = away_score * (home_rating + 50) + home_score * (home_rating - 50)

    # else they are more than 40 points different
    else:
        if home_rating > away_rating:
            home_points = home_score * (home_rating + 10) + away_score * (
                home_rating - 90
            )
            away_points = away_score * (away_rating + 90) + home_score * (
                away_rating - 10
            )
        else:
            home_points = home_score * (home_rating + 90) + away_score * (
                home_rating - 10
            )
            away_points = away_score * (away_rating + 10) + home_score * (
                away_rating - 90
            )

    points_won = [home_points, away_points]

    return points_won


def calc_points_per_series(date_start, date_end, proc_path):

    # loop through the series data
    series_df = pd.read_csv(proc_path + "series_data.csv")
    ratings_df = pd.read_csv(proc_path + "rankings_data.csv")

    # filter series df by date range
    date_i = pd.to_datetime(date_start, format="%d/%m/%Y")
    date_f = pd.to_datetime(date_end, format="%d/%m/%Y")

    series_df = series_df[
        (pd.to_datetime(series_df["date"], format="%d/%m/%Y") >= date_i)
        & (pd.to_datetime(series_df["date"], format="%d/%m/%Y") <= date_f)
    ]

    try:
        df = pd.read_csv(proc_path + "series_points_data.csv")
    except FileNotFoundError:
        df = pd.DataFrame()

    for index, row in series_df.iterrows():

        date_end = get_end_series_date(
            row.date, row.num_matches, [row.home_team, row.away_team]
        )

        try:
            date = datetime.datetime.strptime(date_end, "%Y/%m/%d")
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

        print(
            start_home_rating,
            start_away_rating,
            row.home_team,
            row.away_team,
            month_str,
            year,
        )

        [home_pts, away_pts] = calc_points(
            row.num_matches,
            row.home_team_pts,
            row.away_team_pts,
            start_home_rating,
            start_away_rating,
        )

        rolling_matches = count_matches_from(date_end, proc_path)
        try:
            rolling_home_matches = rolling_matches[row.home_team]
        except KeyError:
            rolling_home_matches = 1
        try:
            rolling_away_matches = rolling_matches[row.away_team]
        except KeyError:
            rolling_away_matches = 1

        data_dict = {
            "date": datetime.date(year, month_num, 1),
            "month": month_num,
            "year": year,
            "home_team": row.home_team,
            "away_team": row.away_team,
            "num_matches": row.num_matches,
            "home_score": row.home_team_pts,
            "away_score": row.away_team_pts,
            "home_tot_points": home_pts,
            "away_tot_points": away_pts,
            "rolling_home_matches": rolling_home_matches,
            "rolling_away_matches": rolling_away_matches,
        }

        df_tmp = pd.DataFrame(data=data_dict, index=[0])
        df = pd.concat([df, df_tmp], ignore_index=True)

    # sort df by date
    df.sort_values(by=["date"], inplace=True)
    df.to_csv(proc_path + "series_points_data.csv")

    return df


def propagate_rankings_data(start_year, start_month, end_year, end_month, proc_path):

    series_df = pd.read_csv(proc_path + "series_points_data.csv")

    rankings_df = pd.read_csv(proc_path + "rankings_data.csv")

    for year in range(start_year, end_year + 1):
        if year == start_year:
            month_i = start_month
        else:
            month_i = 1
        if year == end_year:
            month_f = end_month
        else:
            month_f = 12

        for month in range(month_i, month_f + 1):
            if month > 1:
                date = datetime.date(year, month - 1, 25)
            else:
                date = datetime.date(year - 1, 12, 25)

            sum_rating_pts(date, series_df)

    return


def sum_rating_pts(date_end, series_df):

    series_df["date"] = pd.to_datetime(series_df.date, format="%Y-%m-%d").dt.date

    # get a list of the test teams
    test_teams = list(set(series_df.home_team))

    # retrieve the starting date
    if date_end.month >= 5:
        date_mid_year = date_end.year - 1
    else:
        date_mid_year = date_end.year - 2

    date_start_year = date_mid_year - 2

    date_start = datetime.date(date_start_year, 4, 30)
    date_mid = datetime.date(date_mid_year, 4, 30)

    half_weighting = series_df[
        (series_df["date"] >= date_start) & (series_df["date"] < date_mid)
    ]

    # print(half_weighting)

    full_weighting = series_df[
        (series_df["date"] >= date_mid) & (series_df["date"] <= date_end)
    ]

    print(full_weighting)

    for team in test_teams:

        team_home_pts = (
            0.5
            * half_weighting.loc[
                half_weighting["home_team"] == team, "home_tot_points"
            ].sum()
            + full_weighting.loc[
                full_weighting["home_team"] == team, "home_tot_points"
            ].sum()
        )

        team_away_pts = (
            0.5
            * half_weighting.loc[
                half_weighting["away_team"] == team, "away_tot_points"
            ].sum()
            + full_weighting.loc[
                full_weighting["away_team"] == team, "away_tot_points"
            ].sum()
        )

        team_total_points = team_home_pts + team_away_pts

        print(team, team_total_points)

    return


def aggregate_rankings_data():
    """WIP: compute rankings data for missing years, using initial data
    and match data."""

    # get the initial data
    df = init_ratings_data("../../data/processed/")

    # loop through the series data
    series_df = pd.read_csv("../../data/interim/series_data.csv")
    ratings_df = pd.read_csv("../../data/processed/rankings_data.csv")

    for index, row in series_df.iterrows():

        date_end = get_end_series_date(
            row.date, row.num_matches, [row.home_team, row.away_team]
        )

        try:
            date = datetime.datetime.strptime(date_end, "%Y/%m/%d")
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

    # calc_points_per_series(
    #    "01/05/2009", "01/03/2013", "/home/callow46/test_cricket_stats/data/processed/"
    # )
    propagate_rankings_data(
        2009, 5, 2013, 3, "/home/callow46/test_cricket_stats/data/processed/"
    )
    print(init_ratings_data("/home/callow46/test_cricket_stats/data/processed/"))
    # print(calc_points(3, 2, 1, 120, 40))
