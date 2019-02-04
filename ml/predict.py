
import mysql.connector as sql
import pandas as pd
import numpy as np
from datetime import date, timedelta
from ml.preprocessing import *

from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import  train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics

import seaborn as sns
import matplotlib.pyplot as plt
from IPython.display import display, HTML
from tqdm import tqdm


def predict_next_journey(model,next_journey_matches_df,from_year,last_X_games):

    #DB connection
    db_connection = sql.connect(host='localhost', port=3306, database='acb', user='root', password='root')
    df_games = pd.read_sql('SELECT * FROM game where game.season >= {}'.format(from_year), con=db_connection)
    #print(df_games.shape)
    #print(df_games.columns)
    #df_games.head()

    #correlation matrix
    #corrmat = df_games.corr()
    #f, ax = plt.subplots(figsize=(20,18))
    #sns.heatmap(corrmat, square=True, cmap=sns.diverging_palette(240, 10, as_cmap=True))
    #plt.show()

    # cols to keep
    cols_to_keep = ['team_home_id', 'team_away_id', 'season', 'journey', 'kickoff_time',
                    'score_home', 'score_away', 'referee_1']
    cols_to_del = [c for c in df_games.columns if c not in cols_to_keep]
    df_games.drop(cols_to_del, axis=1, inplace=True)

    df_games, df_predict=calculate_WR_SD_last_X_predict(next_journey_matches_df,df_games,last_X_games)

    df_predict = df_predict[['team_home_id', 'team_away_id', "win_rate_home", "score_diff_avg_home", "win_rate_away", "score_diff_avg_away", "season"]]
    pred_final = model.predict(df_predict)

    df_final=next_journey_matches_df[["team_home","team_home_id","team_away","team_away_id","kickoff_time","season","journey"]]
    x = df_final.copy()

    x['prediction']=pred_final

    return x