import mysql.connector as sql
import numpy as np
from ml.preprocessing import *

from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import  train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn import metrics
from matplotlib.lines import Line2D

import seaborn as sns
import matplotlib.pyplot as plt
from IPython.display import display, HTML
from tqdm import tqdm
import pickle


ML_MODELS_PATH="./ml/models/"
validate_dir(ML_MODELS_PATH)

def train_model(from_year, to_year, streak_days_long, streak_days_short):

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

    # check if nulls
    #print("Number of nulls in df:", df_games.isnull().sum().max())

    # checking amount of times a home team won
    #win_home = df_games["score_away"] < df_games["score_home"]
    #print("Home Team Win percentage: {0:.1f}%".format(100 * win_home.values.sum() / len(win_home)))

    # create score difference feature
    df_games["score_difference"] = df_games["score_home"] - df_games["score_away"]
    #print("Mean of score difference:", df_games["score_difference"].mean())

    df_games=calculate_variables_last_X_train(df_games, streak_days_long)
    df_games=calculate_variables_last_X_train(df_games, streak_days_short)
    df_games.head()


    df_final = df_games.copy()
    df_final.drop(["score_home", "score_away", "journey", "kickoff_time", "referee_1"], axis=1, inplace=True)
    #df_final = df_final[["win_rate_home", "score_diff_avg_home", "win_rate_away", "score_diff_avg_away", "season", "score_difference"]]

    #print("Number of nulls in df_final:", df_final.isnull().sum().max())

    # Years for train // Years for test (generally 2016-2017 and 2018)
    train = df_final[df_final["season"]<to_year]
    test = df_final[df_final["season"]>=to_year]

    X_train = train.drop(['score_difference', "season"], axis=1)
    y_train = train['score_difference']
    X_test = test.drop(['score_difference', "season"], axis=1)
    y_test = test['score_difference']
    #X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=123)

    print(X_train.columns)
    clf = RandomForestRegressor(n_estimators=1000,random_state = 0, max_depth=20)
    clf.fit(X_train, y_train)

    #print(clf.feature_importances_)

    # Estimating an interval
    preds_estimators = {}
    for i in range(len(clf.estimators_)):
        e = clf.estimators_[i]
        preds_estimators["Est" + str(i).zfill(2)] = e.predict(X_test)
    df_preds_estimators = pd.DataFrame(data=preds_estimators)
    axes = df_preds_estimators.transpose().plot.box(figsize=(20, 20), showfliers=True,
                                                    flierprops=dict(marker='+', color='lightblue'),
                                                    color={'whiskers': 'lightblue', 'caps': 'lightblue',
                                                           'medians': 'lightblue', 'boxes': 'lightblue'})
    axes.plot(y_test, color='red', marker='o', linestyle=' ')
    axes.set_title("Predictions of the score difference for each game and real result")
    axes.set_xlabel("Game")
    axes.set_ylabel("Score difference")
    axes.legend([Line2D([0], [0], color='lightblue', marker='o', linestyle=' '),
                 Line2D([0], [0], color='red', marker='o', linestyle=' ')], ['Preds', 'Real'])
    plt.show()

    df_preds_estimators["Upper"] = df_preds_estimators.apply(
        lambda x: np.percentile(x, 75) + 1.5 * (np.percentile(x, 75) - np.percentile(x, 25)), axis=1)
    df_preds_estimators["Lower"] = df_preds_estimators.apply(
        lambda x: np.percentile(x, 25) - 1.5 * (np.percentile(x, 75) - np.percentile(x, 25)), axis=1)
    df_preds_estimators["Real"] = y_test

    mean_aux = df_preds_estimators.apply(lambda x: 1 if x.mean() >= 0 else 0, axis=1)
    print("Percentage of the times the mean was positive:", mean_aux.mean())
    median_aux=df_preds_estimators.apply(lambda x: 1 if np.percentile(x, 50)>=0 else 0, axis=1)
    print("Percentage of the times the median was positive:", median_aux.mean())

    df_preds_estimators["score_in_range?"] = (df_preds_estimators["Real"] >= df_preds_estimators["Lower"]) \
                                             & (df_preds_estimators["Real"] <= df_preds_estimators["Upper"])
    print("Percentage of the times the score was in the given interval: {}%".format(
        100 * float(df_preds_estimators["score_in_range?"].sum()) / len(df_preds_estimators)))


    # predicting score directly
    y_pred = clf.predict(X_test)

    d = {'Real': y_test, 'Pred': y_pred}
    df_res = pd.DataFrame(data=d)
    df_res["winner_correct?"] = np.sign(df_res["Real"]) == np.sign(df_res["Pred"])

    print("Mean absolute error: {} points".format(metrics.mean_absolute_error(y_test, y_pred)))
    print("Percentage of the times the winner was correct: {}%".format(
        float(df_res["winner_correct?"].sum()) / len(df_res)))

    # display(df_res)

    # save the model to disk
    filename = os.path.join(os.getcwd(), "ml", "models", "model_{}.sav".format(datetime.datetime.today().strftime("%Y%m%d%H%M%S")))
    pickle.dump(clf, open(filename, 'wb'))