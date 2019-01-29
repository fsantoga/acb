import mysql.connector as sql
import pandas as pd
from sklearn.model_selection import cross_val_score
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import  train_test_split
from sklearn.linear_model import LogisticRegression
import seaborn as sns
import matplotlib.pyplot as plt


#DB connection
db_connection = sql.connect(host='localhost', port=3306, database='acb', user='root', password='root')
df = pd.read_sql('SELECT * FROM game where game.season >= 1994', con=db_connection)

#correlation matrix
corrmat = df.corr()
f, ax = plt.subplots(figsize=(20,18))
sns.heatmap(corrmat, vmax=.8, square=True)
plt.show()

print(df.shape)

#drop unnecessary columns
to_drop=['id','kickoff_time','game_acbid','venue','attendance','referee_1','referee_2','referee_3','competition_phase','round_phase','db_flag','score_home_extra','score_away_extra']
df.drop(to_drop, inplace=True, axis=1)

#check if nulls
print(df.isnull().sum().max())


df["winning_team"] = df["score_away"] < df["score_home"]
print("Home Team Win percentage: {0:.1f}%".format(100 * df["winning_team"].sum() / df["winning_team"].count()))

df["score_difference"] = df["score_home"] - df["score_away"]

df["home_last_win"] = False
df["away_last_win"] = False

from collections import defaultdict
won_last = defaultdict(int)

for index, row in df.iterrows():
    home_team = row["team_home_id"]
    visitor_team = row["team_away_id"]
    row["home_last_win"] = won_last[home_team]
    row["away_last_win"] = won_last[visitor_team]
    df.ix[index] = row
    #We then set our dictionary with the each team's result (from this row) for the next
    #time we see these teams.
    #Set current Win
    won_last[home_team] = row["winning_team"]
    won_last[visitor_team] = not row["winning_team"]

"""
df.id=df.id.astype(int)
df.game_acbid=df.game_acbid.astype(int)
df.team_home_id=df.team_home_id.astype(int)
df.team_away_id=df.team_away_id.astype(int)
df.season=df.season.astype(int)
df.journey=df.journey.astype(int)
df.competition_phase=df.competition_phase.astype(str)
df.score_home=df.score_home.astype(int)
df.score_away=df.score_away.astype(int)
df.score_home_first=df.score_home_first.astype(int)
df.score_away_first=df.score_away_first.astype(int)
df.score_home_second=df.score_home_second.astype(int)
df.score_away_second=df.score_away_second.astype(int)
df.score_home_third=df.score_home_third.astype(int)
df.score_away_third=df.score_away_third.astype(int)
df.score_home_fourth=df.score_home_fourth.astype(int)
df.score_away_fourth=df.score_away_fourth.astype(int)
df.venue=df.venue.astype(str)
df.attendance=df.attendance.astype(int)
df.referee_1=df.referee_1.astype(str)
df.referee_2=df.referee_2.astype(str)
df.referee_3=df.referee_3.astype(str)
df.winning_team=df.winning_team.astype(int)
df.home_last_win=df.home_last_win.astype(bool)
df.away_last_win=df.away_last_win.astype(int)
df.score_difference=df.score_difference.astype(int)
"""

print(df.isnull().sum(axis = 0))
print(df.isnull().sum(axis = 1))

print(df.dtypes)
print(df.head())

final = df[['team_home_id', 'team_away_id',
        'score_home', 'score_away',
        'winning_team','score_difference']]

print(final.isnull().sum().max())

X = final.drop(['score_difference'], axis=1)
y = final['score_difference']
y = y.astype('int')

X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=0.25, random_state=123)

"""
logreg=LogisticRegression()
logreg.fit(X_train,y_train)

score_train=logreg.score(X_train,y_train)
score_test=logreg.score(X_test,y_test)

print("Training set accuracy: ", "%.3f"%(score_train))
print("Test set accuracy: ", "%.3f"%(score_test))
"""

from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics

clf = RandomForestClassifier(n_estimators=1000,random_state = 123)
clf.fit(X_train, y_train)

print(clf.feature_importances_)

pred = clf.predict(X_test)
print(pred)
print(clf.predict_proba(X_test))
print(metrics.accuracy_score(y_test, pred))

"""
from sklearn.ensemble import GradientBoostingClassifier
clfgtb = GradientBoostingClassifier(n_estimators=100, learning_rate=1.0, max_depth=1, random_state=0).fit(X_train, y_train)
print(clfgtb.score(X_test, y_test))
"""





