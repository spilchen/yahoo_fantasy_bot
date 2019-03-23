#!/bin/python

from datetime import date, timedelta


def is_game_on(d):
    """Checks whether on the given baseball is played

    Returns:
        True if baseball is played
    """
    return d.month >= 4 and d.month <= 9


def prior_game_on(d, delta=1):
    """Find a date that is a number of "baseball" days prior to passed in date

    It will adjust the date if the date math langs in the baseball offseason

    Args:
        d - Starting date
        delta - Number of games to adjust

    Returns:
        New day
    """
    for _ in range(delta):
        d = d - timedelta(days=1)
        d = closest_game_on(d)
    return d


def closest_game_on(d):
    """Find the close date to 'd' where a game is played.

    Args:
        d - Starting date to check

    Returns:
        Returns 'd' if baseball is played on this game.  Otherwise, it will
        find the close date prior to it where baseball is played.
    """
    while is_game_on(d) is False:
        d = d - timedelta(days=1)
    return d


def to_s(d):
    """Return the date in string format.

    This picks the format that is expected in the pybaseball APIs

    Args:
        d - Date to print

    Returns:
        Date in string format
    """
    return d.strftime("%Y-%m-%d")


class Generator:
    """Generate a list of date pairs.

    This class generates a list of date pairs of a given interval length.
    Each pair is suitable for the pybaseball APIs.  Why the special APIs and
    not the python Date library?  To account for the off season.  If you want
    the last 5 months of baseball and you are in May, it should return May,
    April and 3 months from the prior season (Sep, Aug, July).
    """
    def __init__(self, num_pairs=6, range_day_len=30, end_date=date.today()):
        """Object initializer

        Args:
            num_pairs - Number of date pairs that produce() will generate
            range_day_len - The number of days each date pair should be
            end_date (optional) - The ending date to consider in the generator
        """
        self.range_day_len = range_day_len
        self.num_pairs = num_pairs
        self.end_date = closest_game_on(end_date)

    def produce(self):
        """Produce a list of date ranges based on the configured object

        Returns:
          A list of date range pairs.  Each pair will be self.range_day_len
          days long.
        """
        date_pairs = []
        cur_end_date = self.end_date
        for _ in range(self.num_pairs):
            start_date = prior_game_on(cur_end_date, delta=self.range_day_len)
            date_pairs.append([to_s(start_date), to_s(cur_end_date)])
            cur_end_date = prior_game_on(start_date)
        # Reverse the list so that the earliest date is first
        date_pairs.reverse()
        return date_pairs
