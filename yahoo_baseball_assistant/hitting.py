#!/bin/python

from baseball_scraper import batting_stats_range
from baseball_id import Lookup
import pandas as pd


class Builder:
    """Class that constructs datasets for hitters.

    The datasets it generates are used with the machine learning models; both
    for modeling and prediction.

    :param date_range: List of date ranges to use for the dataset.
    :type date_range: List of date ranges
    """
    def __init__(self, date_ranges):
        self.date_ranges = date_ranges
        self.min_PA = None
        self.stats_source = batting_stats_range
        self.id_lookup = Lookup

    def set_min_PA(self, v):
        """Limits the dataset to hitters that reach the minimum PA in each of
        the date ranges we generate data for.

        :param v: Minimum plate appearance value.  All hitters that have less
        plate appearances will be filtered out of the dataset.
        :type v: int
        """
        self.min_PA = v

    def set_date_ranges(self, date_ranges):
        """Use new date ranges for the object

        :param date_range: List of date ranges to use for the dataset.
        :type date_range: List of date ranges
        """
        self.date_ranges = date_ranges

    def set_stats_source(self, source):
        self.stats_source = source

    def set_id_lookup(self, lk):
        self.id_lookup = lk

    def model_dataset(self, predict_category):
        '''Build the dataset used for building hitting models

        :param predict_category: The hitting category that we will predict.
            The category name must be one of the columns returned by the
            batting_stats_range() API.
        :type predict_category: str
        :return: The dataset of k columns.  The first k-1 columns will be
            the input values and the kth column is the predicted value.
        :rtype: DataFrame

        >>> df = hitting.build_model_dataset([['2016-01-01', '2016-12-31'],
                                              ['2017-01-01', '2017-12-31']],
                                             'HR')
        '''
        if len(self.date_ranges) <= 1:
            raise RuntimeError("Must have at least 2 date ranges")
        input_ranges = self.date_ranges[:-1]
        predict_range = self.date_ranges[-1]
        input_data = self._build_input(input_ranges)
        predict_full_data = self._transform(
            self.stats_source(predict_range[0], predict_range[1]))
        predict_data = pd.DataFrame()
        predict_data['Name'] = predict_full_data['Name']
        predict_data[predict_category] = predict_full_data[predict_category]
        return pd.merge(input_data, predict_data, on='Name')

    def predict_dataset(self):
        '''Build the dataset used with a hitting model to predict values.

        :return: The dataset of hitting stats to base prediction on.
        :rtype: DataFrame
        '''
        if len(self.date_ranges) != 1:
            raise RuntimeError("Must have at exactly 1 date ranges")
        if len(self.date_ranges[0]) != 2:
            raise RuntimeError("Date range must have start and end date: " +
                               str(self.date_ranges[0]))
        return self._build_input(self.date_ranges)

    def dataset_for_roster(self, roster):
        """
        Build a dataset to use with a prediction model for a particular team.

        The resulting dataset will have one entry for each player on the team.

        :param roster: Team to generate the dataset for
        :type team: yahoo_fantasy_api.Team
        """
        yahoo_ids = [x['player_id'] for x in roster if
                     x['position_type'] == 'B']
        lk = self.id_lookup.from_yahoo_ids(yahoo_ids)
        full_df = self.predict_dataset()
        df = pd.merge(full_df, lk, left_on='mlb_ID_P0', right_on='mlb_id')
        # Remove the columns that were added from lk.
        df = df.drop(labels=lk.columns.to_list(), axis=1)
        return df

    def _build_input(self, input_ranges):
        """Build a data set across multiple date ranges.

        :param input_ranges: Set of 1 or more date ranges.  Each range we will
            generate stats for and join them into a master data set.
        :type input_ranges: List of date pairs
        """
        input_data = None
        for i, dr in zip(range(len(input_ranges)), input_ranges):
            data = self._transform(self.stats_source(dr[0], dr[1]))
            # We're going to join each of the input sets together, so we need
            # to change the column name to avoid collision.
            data.rename(lambda x: "{}_P{}".format(x, i) if x != "Name" else x,
                        axis=1, inplace=True)
            if input_data is None:
                input_data = data
            else:
                input_data = pd.merge(input_data, data, on='Name')
        return input_data

    def _transform(self, df):
        '''Transform column values in a hitting dataset

        :param df: Hitting DataFrame to transform
        :ptype df: DataFrame
        :return:The transformed DataFrame
        :rtype: DataFrame
        '''
        # Convert a bunch of counting stats to be ratio's of plate appearances
        counting_stats = ['R', 'H', '2B', '3B', 'HR', 'RBI', 'BB', 'IBB',
                          'SO', 'HBP', 'SH', 'SF', 'GDP', 'SB', 'CS']
        for counting_stat in counting_stats:
            df[counting_stat] = df[counting_stat] / df['PA']
        if self.min_PA is not None:
            df = df[df.PA >= self.min_PA]
        # Drop any columns with null's and a few non-numeric columns
        return df.dropna().drop(columns=['#days', 'Lev', 'Tm', 'PA', 'G',
                                         'AB'])
