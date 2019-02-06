
import mysql.connector as sql
from ml.preprocessing import *
import sqlalchemy
from datetime import datetime


def predict_next_journey(model,next_journey_matches_df,from_year,last_X_games,latest_file):

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

    df_predict = df_predict[["win_rate_home", "score_diff_avg_home", "win_rate_away", "score_diff_avg_away"]]
    pred_final = model.predict(df_predict)

    df_final=next_journey_matches_df[["team_home","team_home_id","team_away","team_away_id","kickoff_time","season","journey"]]
    x = df_final.copy()

    x['prediction']=pred_final
    x['prediction_date']=datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    model_path = os.path.basename(latest_file)
    model_file = os.path.splitext(model_path)[0]

    x['model']=model_file


    engine = sqlalchemy.create_engine('mysql+pymysql://root:root@localhost/acb')
    with engine.connect() as conn, conn.begin():
        x.to_sql('predictions', conn, if_exists='append',index=False,chunksize=1)

    return x