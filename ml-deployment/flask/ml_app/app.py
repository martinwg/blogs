import pandas as pd
import os
from flask import Flask, jsonify, request, make_response

import generate_features
from auth import requires_auth

app = Flask(__name__)

@app.route('/')
@requires_auth
def home_get():
    return("API status 200")

@app.route('/forecast', methods=["POST"])
@requires_auth
def forecast_post():
    """
    Args:
        request.data: json pandas dataframe, example: {"columns":["date","open","high","low","close","volume"],"index":[8158,8159,8160,8161,8162],"data":[[1532390400000,108.57,108.82,107.260002,107.660004,26316600],[1532476800000,107.959999,111.150002,107.599998,110.830002,30702100],[1532563200000,110.739998,111.0,109.5,109.620003,31372100],[1532649600000,110.18,110.18,106.139999,107.68,37005300],[1532908800000,107.190002,107.529999,104.760002,105.370003,34602700]]}
    """
    if request.data:
        df = pd.read_json(request.data, orient='split')
        preprocess(df)
        df_json = df.to_json(orient='split')
        resp = make_response(jsonify({"data": df_json}), 200)
        return resp
    else:
        return make_response(jsonify({"message": "no data"}), 400)

def preprocess(df):
    """
    Args:
        df: pd.DataFrame(columns=["date","open","high","low","close","volume"])
    Returns:
        df: pd.DataFrame
    """
    forecast_len = len(df)
    df = combine_with_old_prices(df)
    df = generate_features.return_features(df)
    df = generate_features.target_value(df)
    df = generate_features.trend_features(df)
    df = generate_features.momentum_features(df)
    df = generate_features.volatility_features(df)
    df = generate_features.volume_features(df)
    X, y = remove_unused_features(df)
    X_forecast = X[len(X)-forecast_len:]
    y_forecast = y[len(y)-forecast_len:]
    X_forecast = X_forecast.values # convert to np.ndarray for sklearn
    y_forecast = y_forecast.values # convert to np.ndarray for sklearn

def yahoo_finance_source_to_df(filename):
    """
    Lead Yahoo Finance csv and format to DataFrame
    Args:
        filename: string
    Returns:
        pandas.DataFrame
    """
    df = pd.read_csv(filename, header=0)
    df.drop(labels="Close", axis=1, inplace=True)
    df.columns = ["date", "open", "high", "low", "close", "volume"]
    df["date"] = pd.to_datetime(df["date"])
    return df

def combine_with_old_prices(df_new):
    """
    Combines old prices with new forecast values, leaving out duplicates
    Args:
        df: pd.DataFrame(columns=["date","open","high","low","close","volume"])
    Returns:
        df: pd.DataFrame(columns=["date","open","high","low","close","volume"])
    """
    df = yahoo_finance_source_to_df("MSFT.csv")
    exists_idx = df_new["date"].isin(df["date"]) == False
    for i, row in df_new.loc[exists_idx].iterrows():
        df.loc[len(df)] = row
    return df

def remove_unused_features(df):
    """
    - skip rows with nan values due to feature extraction
    - extract only useful columns for learning
    Args:
        df: pandas.DataFrame
    Returns:
        pandas.DataFrame
    """
    X = df.loc[200:len(df)-1, ["return", "close_to_open", "close_to_high", "close_to_low",
        "macd_diff", "ma_50_200", "sar", "stochastic_oscillator",
        "cci", "rsi", "5d_volatility", "21d_volatility", "60d_volatility",
        "bollinger", "atr", "on_balance_volume", "chaikin_oscillator"]]
    y = df.loc[200:len(df)-1, ["y"]]
    return X, y

    