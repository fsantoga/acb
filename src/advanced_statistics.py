
import pymysql
from collections import defaultdict
import pandas as pd
import sqlalchemy
import math


def calculate_possessions():
    # Database connection
    conn = pymysql.connect(user='root', password='root', database='acb', host='localhost')

    # Load the data into a Pandas DataFrame
    query = "select * from event"
    df = pd.read_sql(query, conn)
    frames = []
    team_possession_list = []
    # GameDF dictionary
    dict_of_games = {k: v for k, v in df.groupby('game_acbid')}
    for game in dict_of_games.values():
        # For each team, we store a list with the possession events associated to that team. Besides, we only store the tuple (eventid, legend) associated to each event.
        # print("Game number: " + str(game.iloc[0]['game_acbid']))
        game_id = game.iloc[0]['game_acbid']
        cursor = conn.cursor()
        sql = "SELECT id FROM game WHERE game_acbid ='%s'"
        cursor.execute(sql % game_id)
        game_id_bueno = cursor.fetchone()[0]
        game['eventid'] = list(range(1, game.shape[0] + 1))
        possessions = defaultdict(list)
        # made2, made3 and turnover. These three categories are straightforward and we just insert them into each team:
        straightforward_elements = ["made2", "made3", "turnover"]
        straightforward_events = game[game["legend"].isin(straightforward_elements)]
        for _, event in straightforward_events.iterrows():
            possessions[event['team_id']].append((event['eventid'], event['legend']))

        # made1. We only include events of type made1 if they are the last free shot. That is, if extra_info is 1/1, 2/2 or 3/3:
        last_free_shot_elements = ["1/1", "2/2", "3/3"]
        last_free_shot_events = game[(game["legend"] == "made1") & (game["extra_info"].isin(last_free_shot_elements))]
        for _, event in last_free_shot_events.iterrows():
            possessions[event['team_id']].append((event['eventid'], event['legend']))

        # reb_def. Given a defensive rebound, the possession for the opponent team ends. Therefore, given a defensive rebound associated to team $i$, we insert such event to team $j$, where $i \not = j$.
        teams = list(possessions.keys())
        defensive_rebound_events = game[game["legend"] == "reb_def"]

        for _, event in defensive_rebound_events.iterrows():
            team = event['team_id']
            opponent_team = teams[(teams.index(team) + 1) % 2]
            possessions[opponent_team].append((event['eventid'], event['legend']))

        # technical fouls
        and_one_events = game[game["extra_info"] == "1/1"]

        for _, event in and_one_events.iterrows():
            if event['legend'] == 'made1':  # 1
                possessions[event['team_id']].remove((event['eventid'], event['legend']))
            else:  # The shot was missed... What do I find first? Technical foul or made2/made3?
                for i in reversed(range(event['eventid'])):
                    if game[game.eventid == i].extra_info.item() == 'technical':  # 2
                        break
                    elif (i, 'made2') in possessions[event['team_id']]:  # 3
                        possessions[event['team_id']].remove((i, 'made2'))
                        break
                    elif (i, 'made3') in possessions[event['team_id']]:  # 3
                        possessions[event['team_id']].remove((i, 'made3'))
                        break

                        # flagrant fouls
                        #    flagrant_elements = ["flagrant", "disqualifying"]
                        #    flagrant_events = game[game["extra_info"].isin(flagrant_elements)]
                        #
                        #    for _, foul in flagrant_events.iterrows():
                        #        events = game[game["eventid"] > foul["eventid"]]
                        #        for _, event in events.iterrows():
                        #            if event["extra_info"] == "2/2" and event["legend"] == "miss1":
                        #                break
                        #            elif event["extra_info"] == "2/2" and event["legend"] == "made1":
                        #                print(possessions[event['team_code']])
                        #                possessions[event['team_code']].remove((event['eventid'], 'made1'))
                        #                break
                        #
        for i, j in possessions.items():
            sql = "UPDATE participant SET possessions = %s WHERE participant.display_name ='Equipo' AND participant.game_id = %s AND participant.team_id = %s "
            val = (len(j),game_id_bueno,i)
            cursor.execute(sql,val)
            # print(i, len(j))

        def count_within_intervals(possessions, intervals):
            cont = 0
            idx_inter = 0
            idx_pos = 0
            left, right = intervals[idx_inter]

            while idx_pos < len(possessions):
                pos, _ = possessions[idx_pos]
                if pos < left:  # smaller than the current interval, next pos...
                    idx_pos += 1
                elif pos < right:  # between current interval, ok!
                    cont += 1
                    idx_pos += 1
                else:  # greater than current interval, new interval...
                    idx_inter += 1
                    if idx_inter == len(intervals):  # no more intervals
                        break
                    left, right = intervals[idx_inter]
            return cont

        substitution_elements = ['sub_in', 'sub_out']
        substitutions_events = game[game['legend'].isin(substitution_elements)]

        individual_possessions = {}
        subs = substitutions_events.groupby("actor_id")
        for name, groups in subs:

            team = groups.iloc[0]['team_id']
            substitutions = list(groups['eventid'])
            if len(substitutions) % 2 == 1:  # sometimes the last sub_out when the game ends is not registered...
                substitutions.append(game.eventid.max() + 1)
            playing = list(zip(substitutions[::2], substitutions[1::2]))  # intervals per player!
            individual_possessions[name] = count_within_intervals(possessions[team], playing)
            # print(name)
            # print(individual_possessions[name])
            sql = "UPDATE participant SET possessions = %s WHERE participant.actor_id = %s AND participant.game_id = %s "
            #print(individual_possessions[name], int(name), game_id_bueno)
            val = (individual_possessions[name], int(name), game_id_bueno)
            cursor.execute(sql,val)


    conn.commit()
    cursor.close()
    conn.close()

            #     s = pd.DataFrame(list(individual_possessions.items()), columns=['actor_id', 'possessions'])
            #     s['game_acbid'] = game_id
            #     s['actor_id'] = s['actor_id'].astype(int)
            #     frames.append(s)

