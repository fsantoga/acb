
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


def predict_next_journey(train_model,next_journey_matches_df,df_final):
   print(train_model)
   print(next_journey_matches_df)
   print(df_final)