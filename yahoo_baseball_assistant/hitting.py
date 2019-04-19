#!/bin/python

from pybaseball import batting_stats_range
import pandas as pd


def build_model_dataset(date_ranges, predict_category, min_PA=None,
                        generator=batting_stats_range):
    '''Build the dataset used for building hitting models

    :param date_range: List of date ranges to use for the dataset.  There must
        be at least two ranges here.  One range that serve as the input data
        and the second that will serve the predicted value.  If more then two
        ranges are specified, the first n-1 will be used for the input data and
        the last one will be for the predicted values.
    :type date_range: List of date ranges
    :param predict_category: The hitting category that we will predict.
        The category name must be one of the columns returned by the
        batting_stats_range() API.
    :type predict_category: str
    :param min_PA: If set, we will filter out rows that doesn't exceed
        this minimum plate appearances
    :type min_PA: int
    :param generator: Data generation source.  Use the default, unless
        you are adding dependency injection for testing purposes
    :type generator: function
    :return: The dataset of k columns.  The first k-1 columns will be
        the input values and the kth column is the predicted value.
    :rtype: DataFrame

    >>> df = hitting.build_model_dataset([['2016-01-01', '2016-12-31'],
                                         ['2017-01-01', '2017-12-31']],
                                         'HR')
    '''
    if len(date_ranges) <= 1:
        raise RuntimeError("Must have at least 2 date ranges")
    input_ranges = date_ranges[:-1]
    predict_range = date_ranges[-1]
    input_data = _build_input(input_ranges, generator, min_PA=min_PA)
    predict_full_data = _transform(
        generator(predict_range[0], predict_range[1]), min_PA=min_PA)
    predict_data = pd.DataFrame()
    predict_data['Name'] = predict_full_data['Name']
    predict_data[predict_category] = predict_full_data[predict_category]
    return pd.merge(input_data, predict_data, on='Name')


def build_predict_dataset(date_range, generator=batting_stats_range):
    '''Build the dataset used with a hitting model to predict values.

    :param date_range: A single date range of the baseball data to use
    :type date_range: List of two dates
    '''
    if len(date_range) == 1:
        raise RuntimeError("Must have at exactly 1 date ranges")
    return _build_input(date_range, generator)


def _build_input(input_ranges, generator, min_PA=None):
    """Build a data set across multiple date ranges.

    :param input_ranges: Set of 1 or more date ranges.  Each range we will
       generate stats for and join them into a master data set.
    :type input_ranges: List of date pairs
    :param generator: Generator of the data.  Takes as input two date ranges.
    :type generator: function
    :param min_PA: If set, we will filter out rows that doesn't exceed
        this minimum plate appearances
    :type min_PA: int
    """
    input_data = None
    for i, dr in zip(range(len(input_ranges)), input_ranges):
        data = _transform(generator(dr[0], dr[1]), min_PA=min_PA)
        # We're going to join each of the input sets together, so we need
        # to change the column name to avoid collision.
        data.rename(lambda x: "{}_P{}".format(x, i) if x != "Name" else x,
                    axis=1, inplace=True)
        if input_data is None:
            input_data = data
        else:
            input_data = pd.merge(input_data, data, on='Name')
    return input_data


def _transform(df, min_PA=None):
    '''Transform column values in a hitting dataset

    Args:
      df (DataFrame) Hitting DataFrame to transform
      minPA (int)  Filter out rows that don't match this minimum plate
                   appearance

    Returns:
      DataFrame: The transformed DataFrame
    '''
    # Convert a bunch of counting stats to be ratio's of plate appearances
    counting_stats = ['R', 'H', '2B', '3B', 'HR', 'RBI', 'BB', 'IBB',
                      'SO', 'HBP', 'SH', 'SF', 'GDP', 'SB', 'CS']
    for counting_stat in counting_stats:
        df[counting_stat] = df[counting_stat] / df['PA']
    if min_PA is not None:
        df = df[df.PA >= min_PA]
    # Drop any columns with null's and a few non-numeric columns
    return df.dropna().drop(columns=['#days', 'Lev', 'Tm', 'PA', 'G', 'AB'])
