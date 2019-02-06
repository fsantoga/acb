
import mysql.connector as sql
from ml.preprocessing import *
import sqlalchemy
from datetime import datetime


def predict_next_journey(model, next_journey_matches_df, from_year, streak_days_long, streak_days_short, latest_file):

    #DB connection
    db_connection = sql.connect(host='localhost', port=3306, database='acb', user='root', password='root')
    df_games = pd.read_sql('SELECT * FROM game where game.season >= {}'.format(from_year), con=db_connection)

    # cols to keep for df_games
    cols_to_keep = ['team_home_id', 'team_away_id', 'season', 'journey', 'kickoff_time',
                    'score_home', 'score_away', 'referee_1']
    cols_to_del = [c for c in df_games.columns if c not in cols_to_keep]
    df_games.drop(cols_to_del, axis=1, inplace=True)

    # generate the variables from historical games
    df_predict = calculate_variables_last_X_predict(next_journey_matches_df, df_games, streak_days_long)
    df_predict = calculate_variables_last_X_predict(df_predict, df_games, streak_days_short)

    # select the columns and predict
    cols_to_use = [c for c in df_predict.columns if c.startswith("win_rate_") or c.startswith("score_diff") or (c.startswith("team_") and c.endswith("_id"))]
    print(cols_to_use)
    preds = model.predict(df_predict[cols_to_use])

    # store predictions into table
    df_results = next_journey_matches_df[["team_home", "team_home_id", "team_away", "team_away_id", "kickoff_time", "season", "journey"]].copy()
    df_results['prediction_date'] = datetime.now()#.strftime("%Y%m%d%H%M%S")
    model_path = os.path.basename(latest_file)
    model_file = os.path.splitext(model_path)[0]
    df_results['model'] = model_file
    df_results['prediction'] = preds
    print(df_results)

    engine = sqlalchemy.create_engine('mysql+pymysql://root:root@localhost/acb')
    with engine.connect() as conn, conn.begin():
        df_results.to_sql('predictions', conn, if_exists='append', index=False, chunksize=1)

    return df_results