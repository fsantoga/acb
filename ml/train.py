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


def train_model(from_year,to_year,last_X_games,next_journey_matches_df):
    #DB connection
    db_connection = sql.connect(host='localhost', port=3306, database='acb', user='root', password='root')
    df_games = pd.read_sql('SELECT * FROM game where game.season >= {}'.format(from_year), con=db_connection)
    print(df_games.shape)
    print(df_games.columns)
    df_games.head()

    #correlation matrix
    corrmat = df_games.corr()
    f, ax = plt.subplots(figsize=(20,18))
    sns.heatmap(corrmat, square=True, cmap=sns.diverging_palette(240, 10, as_cmap=True))
    plt.show()

    # cols to keep
    cols_to_keep = ['team_home_id', 'team_away_id', 'season', 'journey', 'kickoff_time',
                    'score_home', 'score_away', 'referee_1']
    cols_to_del = [c for c in df_games.columns if c not in cols_to_keep]
    df_games.drop(cols_to_del, axis=1, inplace=True)

    # check if nulls
    print("Number of nulls in df:", df_games.isnull().sum().max())

    # checking amount of times a home team won
    win_home = df_games["score_away"] < df_games["score_home"]
    print("Home Team Win percentage: {0:.1f}%".format(100 * win_home.values.sum() / len(win_home)))

    # create score difference feature
    df_games["score_difference"] = df_games["score_home"] - df_games["score_away"]
    print("Mean of score difference:", df_games["score_difference"].mean())

    df_games=calculate_WR_SD_last_X(df_games,last_X_games)
    df_games.head()


    df_final = df_games.copy()
    #df_final.drop(["score_home", "score_away", "kickoff_time", "referee_1"], axis=1, inplace=True)
    df_final = df_final[['team_home_id', 'team_away_id', "win_rate_home", "score_diff_avg_home", "win_rate_away", "score_diff_avg_away", "season","score_difference"]]

    print("Number of nulls in df_final:", df_final.isnull().sum().max())

    # 2016-2017 for train // 2018 for test
    train = df_final[df_final["season"]<to_year]
    test = df_final[df_final["season"]>=to_year]

    X_train = train.drop(['score_difference'], axis=1)
    y_train = train['score_difference']
    X_test = test.drop(['score_difference'], axis=1)
    y_test = test['score_difference']

    #X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=123)

    """
    logreg=LogisticRegression()
    logreg.fit(X_train,y_train)

    score_train=logreg.score(X_train,y_train)
    score_test=logreg.score(X_test,y_test)

    print("Training set accuracy: ", "%.3f"%(score_train))
    print("Test set accuracy: ", "%.3f"%(score_test))
    """

    clf = RandomForestClassifier(n_estimators=1000,random_state = 0, max_depth=10)
    clf.fit(X_train, y_train)

    print(clf.feature_importances_)

    y_pred = clf.predict(X_test)

    d = {'Real': y_test, 'Pred': y_pred}
    df_res = pd.DataFrame(data=d)
    df_res["winner_correct?"] = np.sign(df_res["Real"]) == np.sign(df_res["Pred"])

    print("Mean absolute error: {} points".format(metrics.mean_absolute_error(y_test, y_pred)))
    print("Percentage of the times the winner was correct: {}%".format(float(df_res["winner_correct?"].sum())/len(df_res)))

    display(df_res)

    #######################################################################


    #DB connection
    db_connection = sql.connect(host='localhost', port=3306, database='acb', user='root', password='root')
    df_games_2 = pd.read_sql('SELECT * FROM game where game.season >= {}'.format(from_year), con=db_connection)
    print(df_games_2.shape)
    print(df_games_2.columns)
    df_games_2.head()

    # cols to keep
    cols_to_keep = ['team_home_id', 'team_away_id', 'season', 'journey', 'kickoff_time',
                    'score_home', 'score_away', 'referee_1']
    cols_to_del = [c for c in df_games_2.columns if c not in cols_to_keep]
    df_games_2.drop(cols_to_del, axis=1, inplace=True)

    predict_df=df_games_2.append(next_journey_matches_df,ignore_index=True,sort=False)
    print(predict_df.tail(9))
    predict_df=calculate_WR_SD_last_X(predict_df,last_X_games)
    predict_df=predict_df.tail(9)
    print(predict_df)
    print(predict_df.shape)

    predict_df = predict_df[['team_home_id', 'team_away_id', "win_rate_home", "score_diff_avg_home", "win_rate_away", "score_diff_avg_away", "season"]]
    pred = clf.predict(predict_df)

    return clf, df_final,pred

