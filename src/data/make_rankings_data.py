"""
WIP: This file is intended to compute the rankings data for the missing
years (2013 - present), based on initial data about rankings and total
number of matches played.
"""

import os
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import calendar
import sys


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
        fname = "".join([raw_path, "series_data/series_data_", yrange, ".html"])
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
                date_fmt = pd.to_datetime(date_text, format="%d/%m/%Y")

                # match number from text
                N_matches = date.find_next("td")
                N_matches_text = int(N_matches.text.strip())

                # match result from text
                result = N_matches.find_next("td").text.strip()

                # split the teams
                team_list = teams.split("v.")
                team_A = " ".join(team_list[0].split()[1:])
                team_B = team_list[1].lstrip()

                # get the actual end date
                # date_end_fmt = get_end_series_date(
                #     date_fmt, N_matches_text, [team_A, team_B]
                # )

                len_series = N_matches_text * 9 - 4
                date_end_fmt = date_fmt + datetime.timedelta(days=len_series)

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
                    "date": date_fmt,
                    "date_end": date_end_fmt,
                    "home_team": team_A,
                    "away_team": team_B,
                    "num_matches": N_matches_text,
                    "home_team_pts": team_A_pts,
                    "away_team_pts": team_B_pts,
                }

                df_tmp = pd.DataFrame(data=output_dict)
                df = pd.concat([df, df_tmp], ignore_index=True)

    # save the dataframe as csv
    df.to_csv(proc_path + "series_data.csv")

    return


def count_matches_from(date_end, proc_path):

    r"""Count the number of matches contributing to rankings points at a given date."""

    # get the number of matches played between May 2010 and March 2013
    main_df = pd.read_csv(proc_path + "series_data.csv")
    main_df.date_end = pd.to_datetime(main_df.date_end)

    # get a list of the test teams
    test_teams = list(set(main_df.home_team))

    # retrieve the starting date
    if date_end.month >= 5:
        date_mid_year = date_end.year - 1
    else:
        date_mid_year = date_end.year - 2

    date_start_year = date_mid_year - 2

    date_mid = pd.to_datetime(datetime.date(date_mid_year, 5, 1))
    date_start = pd.to_datetime(datetime.date(date_start_year, 5, 1))

    # print(date_mid, date_start)

    main_df = main_df[(main_df.date_end >= date_start) & (main_df.date_end <= date_end)]
    # print(main_df)

    # initialize match count and ratings
    N_team_matches = {team: 0 for team in test_teams}

    for index, row in main_df.iterrows():
        home_team = row.home_team
        away_team = row.away_team
        num_games = row.num_matches

        end_series_date = row.date_end

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
    start_date = datetime.datetime.strftime(start_date, "%Y/%m/%d")

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

    end_date = pd.to_datetime(end_date)
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


def calc_points_per_series(
    date_start, date_end, proc_path, series_df_csv="series_points_data.csv"
):

    try:
        date_start = pd.to_datetime(date_start, format="%d/%m/%Y")
        date_end = pd.to_datetime(date_end, format="%d/%m/%Y")
    except ValueError:
        pass

    # loop through the series data
    series_df = pd.read_csv(proc_path + "series_data.csv")
    series_df.date = pd.to_datetime(series_df.date)
    series_df.date_end = pd.to_datetime(series_df.date_end)
    ratings_df = pd.read_csv(proc_path + "rankings_data.csv", index_col=0)

    series_df = series_df[
        (series_df["date_end"] >= date_start) & (series_df["date_end"] < date_end)
    ]

    try:
        df = pd.read_csv(proc_path + series_df_csv)
        # df.date = pd.to_datetime(df.date)
        os.remove(proc_path + series_df_csv)
        df = pd.DataFrame()
    except FileNotFoundError:
        df = pd.DataFrame()

    for index, row in series_df.iterrows():

        # date_end = get_end_series_date(
        #     row.date, row.num_matches, [row.home_team, row.away_team]
        # )
        date_end = row.date_end
        month_num_init = date_end.month

        month_year_str = (
            ratings_df.iloc[-1]["month"]
            + " "
            + str(ratings_df.iloc[-1]["year"])
            + " 01"
        )
        lastdate_ratings = pd.to_datetime(month_year_str, format="%B %Y %d")

        if lastdate_ratings.year < date_end.year or (
            lastdate_ratings.year == date_end.year
            and lastdate_ratings.month < date_end.month
        ):
            ratings_df = bump_rankings_data(
                df, ratings_df, date_end.month, date_end.year
            )

        month_str = calendar.month_name[month_num_init].upper()
        year = date_end.year
        rolling_matches = count_matches_from(date_end, proc_path)

        ratings = [0.0, 0.0]
        for i, team in enumerate([row.home_team, row.away_team]):
            month_num = month_num_init
            while month_num > 0:
                month_str = date_end.strftime("%B").upper()
                try:
                    ratings[i] = float(
                        ratings_df[
                            (ratings_df["year"] == year)
                            & (ratings_df["month"] == month_str)
                            & (ratings_df["team"] == team)
                        ].rating
                    )
                except TypeError:
                    print(month_str, year, team)
                    month_num -= 1
                    try:
                        date_end = date_end.replace(month=month_num)
                    except ValueError:
                        ratings[i] = 0.0
                    continue
                break

        [home_pts, away_pts] = calc_points(
            row.num_matches,
            row.home_team_pts,
            row.away_team_pts,
            ratings[0],
            ratings[1],
        )

        try:
            rolling_home_matches = rolling_matches[row.home_team]
        except KeyError:
            rolling_home_matches = 1
        try:
            rolling_away_matches = rolling_matches[row.away_team]
        except KeyError:
            rolling_away_matches = 1

        try:
            rolling_points = sum_rating_pts(date_end, df)
        except AttributeError:
            rolling_points = {row.home_team: 0.0, row.away_team: 0.0}
            pass

        try:
            rolling_home_points = rolling_points[row.home_team] + home_pts
            rolling_away_points = rolling_points[row.away_team] + away_pts
        except KeyError:
            rolling_home_points = 0.0
            rolling_away_points = 0.0

        home_rating = round(rolling_home_points / rolling_home_matches, 1)
        away_rating = round(rolling_away_points / rolling_away_matches, 1)

        data_dict = {
            "date": pd.to_datetime(datetime.date(year, month_num_init, 1)),
            "month": month_num_init,
            "year": year,
            "home_team": row.home_team,
            "away_team": row.away_team,
            "num_matches": row.num_matches,
            "home_score": row.home_team_pts,
            "away_score": row.away_team_pts,
            "home_tot_points": round(home_pts, 1),
            "away_tot_points": round(away_pts, 1),
            "rolling_home_matches": rolling_home_matches,
            "rolling_away_matches": rolling_away_matches,
            "rolling_home_points": round(rolling_home_points, 1),
            "rolling_away_points": round(rolling_away_points, 1),
            "home_rating": home_rating,
            "away_rating": away_rating,
        }

        # update the ratings df
        # ratings_new = update_ratings_df(
        #     ratings_df,
        #     month_str,
        #     row.home_team,
        #     row.away_team,
        #     home_rating,
        #     away_rating,
        # )

        # ratings_df = pd.concat([ratings_df, ratings_new], ignore_index=True)

        df_tmp = pd.DataFrame(data=data_dict, index=[0])
        df = pd.concat([df, df_tmp], ignore_index=True)

    # sort df by date
    df.sort_values(by=["date"], inplace=True)
    df.to_csv(proc_path + series_df_csv, index=False)
    # ratings_df.to_csv(proc_path + "rankings_data.csv")

    return df


def bump_rankings_data(sp_df, ratings_df, month, year):

    # old_month, old_year = (
    #     sp_df.iloc[-1].month,
    #     sp_df.iloc[-1].year,
    # )

    rt_df = ratings_df.iloc[-9:]

    rt_df["month"] = month_to_str(month)
    rt_df["year"] = year

    # Handling home teams
    sp_df_home = sp_df[["home_team", "home_rating", "date"]].copy()
    sp_df_home.columns = ["team", "rating", "date"]

    # Handling away teams
    sp_df_away = sp_df[["away_team", "away_rating", "date"]].copy()
    sp_df_away.columns = ["team", "rating", "date"]

    # Concatenate home and away results
    sp_df_processed = pd.concat([sp_df_home, sp_df_away])

    # Get the most recent rating for each team
    sp_df_processed = (
        sp_df_processed.sort_values("date").groupby("team").last().reset_index()
    )

    # Merge rt_df with sp_df_processed
    rt_df = rt_df.merge(
        sp_df_processed,
        how="left",
        left_on="team",
        right_on="team",
        suffixes=("_rt_df", "_sp_df"),
    )

    # Replace rating in rt_df with the rating from df1 if it exists, else keep the original rating
    rt_df["rating"] = rt_df["rating_sp_df"].where(
        rt_df["rating_sp_df"].notna(), rt_df["rating_rt_df"]
    )

    # Drop unnecessary columns
    rt_df = rt_df.drop(["rating_sp_df", "rating_rt_df", "date"], axis=1)

    # update the rankings
    rt_df.ranking = rt_df["rating"].rank(method="dense", ascending=False).astype(int)
    rt_df = rt_df.sort_values(by=["ranking"])

    print(rt_df)

    ratings_df = pd.concat([ratings_df, rt_df], ignore_index=True)

    return ratings_df


def next_month(month: str, year: int) -> tuple:
    months_dict = {
        "JANUARY": 1,
        "FEBRUARY": 2,
        "MARCH": 3,
        "APRIL": 4,
        "MAY": 5,
        "JUNE": 6,
        "JULY": 7,
        "AUGUST": 8,
        "SEPTEMBER": 9,
        "OCTOBER": 10,
        "NOVEMBER": 11,
        "DECEMBER": 12,
    }
    month_num = months_dict[month.upper()]
    if month_num == 12:
        return ("JANUARY", year + 1)
    else:
        return (list(months_dict.keys())[month_num], year)


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
                date = pd.to_datetime(datetime.date(year, month - 1, 25))
            else:
                date = pd.to_datetime(datetime.date(year - 1, 12, 25))

            N_team_matches = count_matches_from(date, proc_path)
            # print(N_team_matches)
            sum_rating_pts(date, series_df)

    return


def sum_rating_pts(date_end, series_df):

    # get a list of the test teams
    test_teams = list(set(series_df.home_team))

    series_df["date"] = pd.to_datetime(series_df["date"])

    # retrieve the starting date
    if date_end.month >= 5:
        date_mid_year = date_end.year - 1
    else:
        date_mid_year = date_end.year - 2

    date_start_year = date_mid_year - 2

    date_start = pd.to_datetime(datetime.date(date_start_year, 5, 1))
    date_mid = pd.to_datetime(datetime.date(date_mid_year, 5, 1))

    half_weighting = series_df[
        (series_df["date"] >= date_start) & (series_df["date"] < date_mid)
    ]

    full_weighting = series_df[
        (series_df["date"] >= date_mid) & (series_df["date"] <= date_end)
    ]

    team_pts_dict = {}

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

        team_pts_dict[team] = team_total_points

    return team_pts_dict


def make_new_rankings_data(start_year, start_month, end_year, end_month, proc_path):

    series_df = pd.read_csv(proc_path + "series_data.csv", index_col=0)
    series_points_df = pd.read_csv(proc_path + "series_points_data.csv")
    rankings_df = pd.read_csv(proc_path + "rankings_data.csv", index_col=0)

    # get a month and year column for series df
    series_df["month"] = pd.to_datetime(series_df.date_end).dt.month
    series_df["year"] = pd.to_datetime(series_df.date_end).dt.year

    for year in range(start_year, end_year + 1):
        if year == start_year:
            month_i = start_month
        else:
            month_i = 1
        if year == end_year:
            month_f = end_month + 1
        else:
            month_f = 12

        for month in range(month_i, month_f):

            # update the rankings df
            # need to change the rankings df function

            date_rnk_str = "-".join([str(year), str(month), "01"])
            date_rnk = (
                pd.to_datetime(date_rnk_str, format="%Y-%m-%d") - pd.offsets.MonthEnd()
            )

            # compute the match and points total up to the final day of the previous month
            N_matches = count_matches_from(date_rnk, proc_path)
            tot_points = sum_rating_pts(date_rnk, series_points_df)

            # update the rankings df if it has fallen behind
            rankings_df = bump_rankings_data_new(
                rankings_df, tot_points, N_matches, month, year
            )

            series_df_tmp = series_df[
                (series_df.month == month) & (series_df.year == year)
            ]

            print(rankings_df.tail(9))

            if not series_df_tmp.empty:
                # print(series_df_tmp)
                # update the series points df now
                series_points_df = update_series_pts_df(
                    series_points_df, series_df_tmp, rankings_df, proc_path
                )
                continue

    print(series_points_df.tail(10))

    return


def bump_rankings_data_new(rankings_df, tot_points, N_matches, month, year):

    rt_df = rankings_df.iloc[-9:]

    date_last = pd.to_datetime(
        f"{rankings_df.iloc[-1].month}-{rankings_df.iloc[-1].year}", format="%B-%Y"
    )

    # only update if required
    if date_last >= pd.to_datetime(
        "-".join([str(year), str(month), "01"]), format="%Y-%m-%d"
    ):
        return rankings_df

    rt_df["month"] = month_to_str(month)
    rt_df["year"] = year

    rt_df["rating"] = rt_df["team"].map(tot_points) / rt_df["team"].map(N_matches)

    rt_df.ranking = rt_df["rating"].rank(method="dense", ascending=False).astype(int)
    rt_df = rt_df.sort_values(by=["ranking"])

    rankings_df = pd.concat([rankings_df, rt_df], ignore_index=True)

    return rankings_df


def update_series_pts_df(series_points_df, series_df_tmp, ratings_df, proc_path):

    lastdate_1 = pd.to_datetime(series_points_df.iloc[-1].date)
    lastdate_2 = pd.to_datetime(
        series_df_tmp.date_end.iloc[-1]
    ) - pd.offsets.MonthBegin(n=0)

    if lastdate_1 >= lastdate_2:
        return series_points_df

    for index, row in series_df_tmp.iterrows():

        date_end = pd.to_datetime(row.date_end)
        month_num_init = date_end.month

        month_str = calendar.month_name[month_num_init].upper()
        year = date_end.year
        rolling_matches = count_matches_from(date_end, proc_path)

        ratings = [0.0, 0.0]
        for i, team in enumerate([row.home_team, row.away_team]):
            month_num = month_num_init
            while month_num > 0:
                month_str = date_end.strftime("%B").upper()
                try:
                    ratings[i] = float(
                        ratings_df[
                            (ratings_df["year"] == year)
                            & (ratings_df["month"] == month_str)
                            & (ratings_df["team"] == team)
                        ].rating
                    )
                except TypeError:
                    print(month_str, year, team)
                    month_num -= 1
                    try:
                        date_end = date_end.replace(month=month_num)
                    except ValueError:
                        ratings[i] = 0.0
                    continue
                break

        [home_pts, away_pts] = calc_points(
            row.num_matches,
            row.home_team_pts,
            row.away_team_pts,
            ratings[0],
            ratings[1],
        )

        try:
            rolling_home_matches = rolling_matches[row.home_team]
        except KeyError:
            rolling_home_matches = 1
        try:
            rolling_away_matches = rolling_matches[row.away_team]
        except KeyError:
            rolling_away_matches = 1

        try:
            rolling_points = sum_rating_pts(date_end, series_points_df)
        except AttributeError:
            rolling_points = {row.home_team: 0.0, row.away_team: 0.0}
            pass

        try:
            rolling_home_points = rolling_points[row.home_team] + home_pts
            rolling_away_points = rolling_points[row.away_team] + away_pts
        except KeyError:
            rolling_home_points = 0.0
            rolling_away_points = 0.0

        home_rating = round(rolling_home_points / rolling_home_matches, 1)
        away_rating = round(rolling_away_points / rolling_away_matches, 1)

        data_dict = {
            "date": pd.to_datetime(datetime.date(year, month_num_init, 1)),
            "month": month_num_init,
            "year": year,
            "home_team": row.home_team,
            "away_team": row.away_team,
            "num_matches": row.num_matches,
            "home_score": row.home_team_pts,
            "away_score": row.away_team_pts,
            "home_tot_points": round(home_pts, 1),
            "away_tot_points": round(away_pts, 1),
            "rolling_home_matches": rolling_home_matches,
            "rolling_away_matches": rolling_away_matches,
            "rolling_home_points": round(rolling_home_points, 1),
            "rolling_away_points": round(rolling_away_points, 1),
            "home_rating": home_rating,
            "away_rating": away_rating,
        }

        df_tmp = pd.DataFrame(data=data_dict, index=[0])

        series_points_df = pd.concat([series_points_df, df_tmp], ignore_index=True)

    return series_points_df


def rankings_by_date(rankings_df, month, year):

    # convert the month to a string
    datetmp = datetime.date(year, month, 1)
    month_str = datetmp.strftime("%B").upper()

    # return the part of the rankings df with the correct month and year
    df_ym = rankings_df.loc[
        (rankings_df["month"] == month_str) & (rankings_df["year"] == year)
    ]

    return df_ym


def series_df_by_date(series_df, month, year):

    # get the start and end date from month and year
    start_date = datetime.datetime(year, month, 1)
    if month != 12:
        end_date = datetime.datetime(year, month + 1, 1)
    else:
        end_date = datetime.datetime(year + 1, 1, 1)

    df_ym = series_df.loc[
        (pd.to_datetime(series_df["date_end"]) >= start_date)
        & (pd.to_datetime(series_df["date_end"]) < end_date)
    ]

    return df_ym


def complete_update(
    date_start: str, date_end: str, rankings_csv: str, series_data_csv: str
):

    # get the starting month and year
    year_start, month_start = get_MY_from_str(date_start)
    year_end, month_end = get_MY_from_str(date_end)

    print(month_start, year_start, month_end, year_end)

    # open the csv files
    series_df = pd.read_csv(series_data_csv, index_col=0)
    rankings_df = pd.read_csv(rankings_csv, index_col=0)

    for year in range(year_start, year_end + 1):
        month_i = 1
        month_f = 13
        if year == year_start:
            month_i = month_start
        elif year == year_end:
            month_f = month_end + 1

        for month in range(month_i, month_f):

            # check to see if rankings data already exists
            last_date_rankings = get_rankings_last_month(rankings_df)
            date_string = pd.to_datetime(f"1 {month} {year}", format="%d %m %Y")
            if date_string <= last_date_rankings:
                continue

            num_matches_dict = count_matches_from(
                date_string, "/home/callow46/test_cricket_stats/data/processed/"
            )
            num_matches_df = pd.DataFrame(
                list(num_matches_dict.items()), columns=["team", "num_matches"]
            )

            rankings_partial = rankings_df.tail(9).reset_index(drop=True)

            rankings_partial["tot_points"] = (
                rankings_partial.rating * num_matches_df.num_matches
            )

            partial_df = get_partial_df(series_df, month, year)


def get_partial_df(df, month, year):
    date_end = pd.to_datetime(df["date_end"])
    mask = (date_end.dt.month == month) & (date_end.dt.year == year)
    return df[mask]


def get_rankings_last_month(df):
    last_row = df.iloc[-1]
    month = last_row["month"]
    year = last_row["year"]
    date_string = f"1 {month} {year}"
    return pd.to_datetime(date_string, format="%d %B %Y")


def get_MY_from_str(date_str):
    year, month, _ = date_str.split("/")
    return int(year), int(month)


def month_to_str(month: int) -> str:

    months_dict = {
        "1": "JANUARY",
        "2": "FEBRUARY",
        "3": "MARCH",
        "4": "APRIL",
        "5": "MAY",
        "6": "JUNE",
        "7": "JULY",
        "8": "AUGUST",
        "9": "SEPTEMBER",
        "10": "OCTOBER",
        "11": "NOVEMBER",
        "12": "DECEMBER",
    }

    return months_dict[str(month)]


if __name__ == "__main__":

    home_dir = "/home/callow46/test_cricket_stats/"
    data_dir = home_dir + "data/"
    proc_dir = data_dir + "processed/"

    # series_data_to_csv(
    #     data_dir + "raw/", data_dir + "interim/", data_dir + "processed/"
    # )

    calc_points_per_series(
        "01/05/2009", "01/03/2013", "/home/callow46/test_cricket_stats/data/processed/"
    )

    make_new_rankings_data(2013, 1, 2022, 1, proc_dir)

    # complete_update(
    #     "2012/01/01",
    #     "2016/03/01",
    #     proc_dir + "rankings_data.csv",
    #     proc_dir + "series_data.csv",
    # )

    # propagate_rankings_data(2009, 5, 2013, 3, data_dir + "processed/")
    # print(init_ratings_data(data_dir + "processed/"))

    # make_new_rankings_data(2013, 3, 2013, 4, data_dir + "processed/")

    # print(calc_points(3, 2, 1, 120, 40))
