#!/bin/python

import copy
import logging
import numpy as np
import pandas as pd
import math
import random
import sys
from yahoo_fantasy_bot import roster


def optimize_single_player_at_a_time(cfg, score_comparer, roster_bldr,
                                     avail_plyrs, lineup):
    """
    Optimize by swapping in a single player to a constructed lineup

    :param cfg: Loaded config object
    :type cfg: configparser.ConfigParser
    :param score_comparer: Object that is used to compare two lineups to
    determine the better one
    :type score_comparer: bot.ScoreComparer
    :param roster_bldr: Object that is used to construct a roster given the
    constraints of the league
    :type roster_bldr: roster.Builder
    :param avail_plyrs: Pool of available players that can be included in
    a lineup
    :type avail_plyrs: DataFrame
    :param lineup: The currently constructed lineup
    :type lineup: list
    :return: If a better lineup was found, this will return it.  If no better
    lineup was found this returns None
    :rtype: list or None
    """
    selector = roster.PlayerSelector(avail_plyrs)
    categories = cfg['LineupOptimizer']['categories'].split(",")
    try:
        selector.rank(categories)
    except KeyError:
        raise KeyError("Categories are not valid: {}".format(categories))

    found_better = False
    score_comparer.update_score(lineup)
    for i, plyr in enumerate(selector.select()):
        if i+1 > int(cfg['LineupOptimizer']['iterations']):
            break

        print("Player: {} Positions: {}".
              format(plyr['name'], plyr['eligible_positions']))

        plyr['selected_position'] = np.nan
        best_lineup = copy.deepcopy(lineup)
        for potential_lineup in roster_bldr.enumerate_fit(best_lineup, plyr):
            if score_comparer.compare_lineup(potential_lineup):
                print("  *** Found better lineup when including {}"
                      .format(plyr['name']))
                lineup = copy.deepcopy(potential_lineup)
                score_comparer.update_score(lineup)
                found_better = True
    return lineup if found_better else None


def optimize_with_genetic_algorithm(cfg, score_comparer, roster_bldr,
                                    avail_plyrs, lineup):
    """
    Loader for the GeneticAlgorithm class

    See GeneticAlgorithm.__init__ for parameter type descriptions.
    """
    # SPILLY - are the players in lineup included in avail_plyrs?  if not, we
    # need to include it
    algo = GeneticAlgorithm(cfg, score_comparer, roster_bldr, avail_plyrs,
                            lineup)
    generations = int(cfg['LineupOptimizer']['generations']) \
        if 'generations' in cfg['LineupOptimizer'] else 100
    return algo.run(generations)


class GeneticAlgorithm:
    """
    Optimize the lineup using a genetic algorithm

    The traits of the algorithm and how it relates to lineup building is
    as follows:
    - chromosomes: lineups
    - genes: players in the lineup
    - population (group): random set of lineups that use all available players
    - fitness function: evaluation a lineup against the base line with the
    score_comparer

    When apply generations to the chromosomes, the following applies:
    - selection: Lineups that have the best score are more likely to be
    selected.
    - crossover: Involves merging of two lineups.
    - mutate: Randomly swapping out a player with someone else

    :param cfg: Loaded config object
    :type cfg: configparser.ConfigParser
    :param score_comparer: Object that is used to compare two lineups to
    determine the better one
    :type score_comparer: bot.ScoreComparer
    :param roster_bldr: Object that is used to construct a roster given the
    constraints of the league
    :type roster_bldr: roster.Builder
    :param avail_plyrs: Pool of available players that can be included in
    a lineup
    :type avail_plyrs: DataFrame
    :param lineup: The currently constructed lineup
    :type lineup: list
    :return: If a better lineup was found, this will return it.  If no better
    lineup was found this returns None
    :rtype: list or None
    """
    def __init__(self, cfg, score_comparer, roster_bldr, avail_plyrs, lineup):
        self.cfg = cfg
        self.score_comparer = score_comparer
        self.roster_bldr = roster_bldr
        self.ppool = avail_plyrs
        self.population = []
        self.logger = logging.getLogger()
        self.best_lineup = lineup

    def run(self, generations):
        """
        Optimize a lineup by running the genetic algorithm

        :param generations: The number of generations to run the algorithm for
        :type generations: int
        :return: The best lineup we generated.  Or None if no lineup was
        generated
        :rtype: list or None
        """
        self._init_population()
        for generation in range(generations):
            sys.stdout.write(".")
            sys.stdout.flush()
            self._mate()
            self._mutate()
        self._compute_best_lineup()
        self._log_lineup("Best lineup", self.best_lineup)
        return self.best_lineup

    def _log_lineup(self, descr, lineup):
        self.logger.info("Lineup " + str(descr))
        for plyr in lineup:
            self.logger.info(
                "{} - {} ({}%)".format(plyr['selected_position'],
                                       plyr['name'],
                                       plyr['percent_owned']))

    def _log_population(self):
        for i, lineup in enumerate(self.population):
            self._log_lineup("Initial Population " + str(i), lineup)

    def _init_population(self):
        """
        Setup the initial population of random lineups

        On exit self.population will be setup.
        """
        selector = roster.PlayerSelector(self.ppool)
        selector.set_descending_categories([])
        selector.rank(['percent_owned'])
        lineups = []
        lineups.append([])
        for plyr in selector.select():
            fit = False
            for lineup in lineups:
                if len(lineup) == self.roster_bldr.max_players():
                    continue
                try:
                    if plyr['status'] != '':
                        continue
                    plyr['selected_position'] = np.nan
                    lineup = self.roster_bldr.fit_if_space(lineup, plyr)
                    fit = True

                    # If lineup is no complete add it to the population
                    if len(lineup) == self.roster_bldr.max_players():
                        self.population.append(lineup)

                    break   # Stop trying to find a lineup for plyr
                except LookupError:
                    pass   # Try fitting in the next lineup

            if not fit:
                lineup = self.roster_bldr.fit_if_space([], plyr)
                lineups.append(lineup)
        self._log_population()

    def _compute_best_lineup(self):
        """
        Goes through all of the possible lineups and figures out the best

        The best lineup will be set in self.best_lineup
        """
        assert(self.best_lineup)
        self.score_comparer.update_score(self.best_lineup)
        for lineup in self.population:
            if self.score_comparer.compare_lineup(lineup):
                self.best_lineup = lineup
                self.score_compare.update_score(lineup)
                self._log_lineup("Best", lineup)

    def _mate(self):
        """
        Merge two lineups to produce children that character genes from both

        The selection process regarding who to mate is determined using the
        selectionStyle config parameter.
        """
        mates = self._pick_lineups()
        offspring = self._produce_offspring(mates)
        for i, lineup in enumerate(offspring):
            self._log_lineup("Offspring " + str(i), lineup)
        self.population = self.population + offspring

    def _pick_lineups(self):
        """
        Pick two lineups at random

        This uses the tournament selection process where random set of lineups
        are selected, then go through a tournament to pick the top number.

        :return: List of lineups
        """
        k = int(self.cfg['LineupOptimizer']['tournamentParticipants'])
        if k > len(self.population):
            pw = math.floor(math.log(len(self.population), 2))
            k = 2**pw
        assert(math.log(k, 2).is_integer()), "Must be a power of 2"
        participants = random.choices(self.population, k=k)
        rounds = math.log(k, 2) - 1
        for _ in range(int(rounds)):
            next_participants = []
            for opp_1, opp_2 in zip(participants[0::2], participants[1::2]):
                self.score_comparer.update_score(opp_1)
                if self.score_comparer.compare_lineup(opp_2):
                    next_participants.append(opp_2)
                else:
                    next_participants.append(opp_1)
            participants = next_participants
        assert(len(participants) == 2)
        return participants

    def _produce_offspring(self, mates):
        """
        Merge two lineups together to produce a set of children.

        :param mates: Two parent lineups that we use to produce offspring
        :return: List of lineups
        """
        assert(len(mates) == 2)
        ppool = self._create_player_pool(mates)
        offspring = []
        for _ in range(int(self.cfg['LineupOptimizer']['numOffspring'])):
            offspring.append(self._complete_lineup([], ppool))
        return offspring

    def _create_player_pool(self, lineups):
        """
        Produces a player pool from a set of lineups

        The player pool is suitable for use with the PlayerSelector

        :param lineups: Set of lineups to create a pool out of
        :return: DataFrame of all of the unique players in the lineups
        """
        df = pd.DataFrame()
        player_ids = []
        for lineup in lineups:
            for i, plyr in enumerate(lineup):
                # Avoid adding duplicate players to the pool
                if plyr['player_id'] not in player_ids:
                    df = df.append(plyr, ignore_index=True)
                    player_ids.append(plyr['player_id'])
        return df

    def _complete_lineup(self, lineup, ppool):
        """
        Complete a lineup so that it has the max number of players

        The players are selected at random.

        :param lineup: Lineup to fill.  Can be [].
        :param ppool: Player pool to pull from
        :return: List that contains the players in the lineup
        """
        ids = [e['player_id'] for e in lineup]
        selector = roster.PlayerSelector(ppool)
        selector.shuffle()
        for plyr in selector.select():
            # Do not add the player if it is already in the lineup
            if plyr['player_id'] in ids:
                continue
            try:
                plyr['selected_position'] = np.nan
                lineup = self.roster_bldr.fit_if_space(lineup, plyr)
            except LookupError:
                pass
            if len(lineup) == self.roster_bldr.max_players():
                return lineup
        raise RuntimeError(
            "Walked all of the players but couldn't create a lineup.  Have "
            "{} players".format(len(lineup)))

    def _mutate(self):
        """
        Go through all of the players and mutate a certain percent.

        Mutation simply means swapping out the player with a random player.
        """
        mutate_pct = int(self.cfg['LineupOptimizer']['mutationPct'])
        for lineup in self.population:
            mutates = []
            for i, plyr in enumerate(lineup):
                if random.randint(0, 100) <= mutate_pct:
                    self.logger.info("Mutating player {}".format(plyr['name']))
                    mutates.append(i)
            mutates.reverse()   # Delete at the end of lineup first
            for i in mutates:
                del(lineup[i])
            if len(lineup) < self.roster_bldr.max_players():
                self._complete_lineup(lineup, self.ppool)
                self._log_lineup("Mutated lineup", lineup)
                assert(len(lineup) == self.roster_bldr.max_players())
