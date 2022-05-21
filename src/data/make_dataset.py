"""The main file to convert raw into processed data."""

# # -*- coding: utf-8 -*-
from pathlib import Path

import requests
import sys
from bs4 import BeautifulSoup
import pandas as pd
import glob
from datetime import datetime
from datetime import date as dtdate


class RawData:
    """Class to handle downloading of raw data from source.

    Parameters
    ----------
    datapath : str
        the raw data path
    year_start : int
        the starting year of the download
    end_year : int
        the ending year of the download
    """

    def __init__(self, datapath, year_start, year_end):

        self._datapath = datapath
        self._year_start = year_start
        self._year_end = year_end

    def download_rankings_data(self):
        """Download the rankings data from html source."""

        # main url for rankings data
        baseurl = (
            "https://web.archive.org/web/20130320093711/"
            + "http://www.icc-cricket.com/match_zone/test_ranking.php?year="
        )

        # loop over the years in the range
        for year in range(self._year_start, self._year_end + 1):
            print("downloading rankings data for year ", year)
            url = baseurl + str(year)
            data_page = requests.get(url)  # fetch the data
            # use beautiful soup to parse the data
            soup = BeautifulSoup(data_page.content, "html.parser")
            soup.prettify()
            # write the prettified html to file
            fname = "".join([self.outdir, "rankings_data_", str(year), ".html"])
            with open(fname, "w") as f:
                f.write(str(soup))

        return


class ProcessData:
    """Class which holds the routines handling processing of raw data.

    Parameters
    ----------
    raw_datapath : str
        the raw data path
    processed_datapath : str
        the processed data path
    year_start : int
        the starting year of the data
    end_year : int
        the ending year of the data
    rankings_file : str
        the filename (and location) of the rankings csv file
    aggregate_file : str
        the filename (and location) of the aggregate csv file
    """

    def __init__(
        self,
        raw_datapath,
        processed_datapath,
        year_start,
        year_end,
        rankings_file,
        aggregate_file,
    ):

        self.raw_datapath_ = raw_datapath
        self.processed_datapath_ = processed_datapath
        self.year_start_ = year_start
        self.year_end_ = year_end
        self.rankings_file_ = rankings_file
        self.aggregate_file_ = aggregate_file

    def rankings_to_csv(self):
        r"""Make a csv file of the rankings / ratings data."""

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

        data_agg = pd.DataFrame()  # initialize dataframe

        # loop over months and years
        for year in range(self.year_start_, self.year_end_ + 1):
            for month in month_list:
                try:
                    YM_data = self.get_rankings_data(month, year)
                    data_agg = pd.concat([data_agg, YM_data], ignore_index=True)
                except AttributeError:
                    pass

        data_agg.to_csv(self.processed_datapath_ + self.rankings_file_)

        return

    def get_rankings_data(self, month, year):
        """Strip the rankings data from the html file for a given M/Y.

        Parameters
        ----------
        month : str
            the given month (all upper case chars)
        year : int
            the given year

        Returns
        -------
        rankings_df : pandas dataframe
            a dataframe of the rankings data (date, team, ranking and rating)
        """

        # load the html file for the given year
        fname = "".join(
            [self.raw_datapath_, "rankings_data/rankings_data_", str(year), ".html"]
        )

        # parse the html file and loop until the given month table is found
        with open(fname, "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        for x in soup.find_all("a"):
            if x.get("name") == month:
                break
        # extract the table content
        table_description = x.next_sibling
        table_content = table_description.next_sibling

        team_list = []
        rankings_list = []
        ratings_list = []
        # loop over each row in the table, where each row is a team with rank info
        for row in table_content.contents:
            rowtext = row.text
            # find the ranking and rating by their position in the text
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

        # convert month and year to list with same length as team count
        month_list = len(team_list) * [month]
        year_list = len(team_list) * [year]

        # create a dictionary of the data and then convert it to a pandas df
        output_dict = {
            "year": year_list,
            "month": month_list,
            "team": team_list,
            "ranking": rankings_list,
            "rating": ratings_list,
        }
        rankings_df = pd.DataFrame(data=output_dict)

        return rankings_df

    def get_match_data(self, filename):
        """
        Extract the desired data from a given venue_info file.

        Parameters
        ----------
        filename : str
            the csv to extract from

        Returns
        -------
        match_data : list
            the desired match data (date, teams, result, toss result)
        """

        # the file containing the venue - country info
        venue_file = self.raw_datapath_ + "venue_info.csv"
        # read the match data file
        with open(filename, "r") as f:
            lines = f.readlines()

        # dummy list of teams
        team_count = 0
        teams = ["a", "b"]
        # loop over all the lines to get the desired info
        for line in lines:

            if "info,team," in line:
                team = line.split(",")[2]
                teams[team_count] = team.strip()
                team_count += 1

            elif "info,date" in line:
                dateraw = line.split(",")[2].strip()

            elif "info,winner," in line:
                result = line.split(",")[2].strip()
            elif "info,outcome," in line:
                result = line.split(",")[2].strip()

            elif "info,toss_winner," in line:
                toss_winner = line.split(",")[2].strip()

            elif "info,venue," in line:
                venue = ",".join(line.split(",")[2:]).strip()
                # remove speech marks from the venue for comparison with venue file
                venue1 = venue.replace('"', "")
                df_venues = pd.read_csv(venue_file, header=0)
                # look for the venue in the venue file to get country
                home_team = (
                    df_venues.loc[df_venues["venue"] == venue1]
                    .country.to_string(index=False, header=False)
                    .strip()
                )

        # assign home and away teams
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

        match_data = [dateraw, home_team, away_team, result, toss_winner]

        return match_data

    def merge_match_ranking_data(
        self,
        filename,
        date_min,
        date_max,
    ):
        """
        Combine the match and rankings data for a given match.

        Parameters
        ----------
        filename : str
            the _info.csv file for the given match
        date_min : datetime object
            the earliest date for which to merge data
        date_max : datetime object
            the latest date for which to merge data

        Returns
        -------
        df_out : pd.DataFrame
            a dataframe of the merged data
            the df is empty if the match date isn't in the accepted range
        """

        # extract date and teams from the match data
        match_data = self.get_match_data(filename)
        dateraw = match_data[0]
        home_team = match_data[1]
        away_team = match_data[2]
        # convert date to datetime object
        date = datetime.strptime(dateraw, "%Y/%m/%d")

        # return empty df if date outside allowed range
        if date.date() < date_min or date.date() > date_max:
            return pd.DataFrame()

        month_num = date.month
        month_str = date.strftime("%B").upper()
        year = date.year

        # load the rankings data file
        df_rankings = pd.read_csv(self.processed_datapath_ + self.rankings_file_)

        # try to extract the data for the given month
        # if that month has no rankings data, loop backwards through the months
        # until a month with rankings data is found
        while month_num > 0:
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
                # go to the previous month
                month_num -= 1
                # in case the month num reaches 0 - return empty df
                try:
                    date = date.replace(month=month_num)
                except ValueError:
                    return pd.DataFrame()
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

    def agg_data_to_csv(self):
        """Dump all the processed data into a single csv file."""

        # define the min and max dates
        # TODO : these should be set in the class initialization
        date_min = dtdate(2004, 3, 1)
        date_max = dtdate(2013, 3, 31)
        data_agg = pd.DataFrame()

        # list of all info files
        info_files = glob.glob(self.raw_datapath_ + "match_data/*_info.csv")

        # loop through the info files and append everything into a single df
        for info_file in info_files:
            try:
                match_rank_data = self.merge_match_ranking_data(
                    info_file, date_min, date_max
                )
                data_agg = pd.concat([match_rank_data, data_agg], ignore_index=True)
            except ValueError:
                pass

        data_agg.to_csv(self.processed_datapath_ + self.aggregate_file_)

        return


def main(input_filepath, output_filepath):
    """Runs data processing scripts to turn raw data from (../raw) into
    cleaned data ready to be analyzed (saved in ../processed).
    """

    # create the processed data object
    processed_data = ProcessData(
        input_filepath,
        output_filepath,
        2003,
        2013,
        "rankings_data.csv",
        "aggregate_data.csv",
    )

    # transform html rankings data to csv file
    processed_data.rankings_to_csv()

    # aggregate match and rankings data
    processed_data.agg_data_to_csv()


if __name__ == "__main__":

    # not used in this stub but often useful for finding various files
    project_dir = Path(__file__).resolve().parents[2]

    main(sys.argv[1], sys.argv[2])
