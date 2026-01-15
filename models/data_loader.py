"""
Data loading functions for DistroDashboard.
Functions moved here from core/data_loader.py.
"""

import os
import pandas as pd
import psycopg2

def get_data(folder_name , args_list , file_type):
    data = pd.DataFrame()
    for file in os.scandir(folder_name):
        if file.name.endswith(file_type) and all(x in file.name for x in args_list):
            if(file_type == ".parquet"):
                data = pd.read_parquet(file.path , engine = 'pyarrow')
            elif (file_type == ".csv"):
                data = pd.read_csv(file.path)
            break
    return data

def get_price_movt(start_timestamp , end_timestamp , x , y , folder):
    price_data = get_data(folder , [x,y] , ".parquet")
    price_data = price_data[(price_data['US/Eastern Timezone'] >= start_timestamp) &
                            (price_data['US/Eastern Timezone'] <= end_timestamp)]

    return [price_data['Open'].iloc[0] , price_data['High'].max() , price_data['Close'].iloc[-1] , price_data['Low'].min()]

DB_CONFIG = {
    "Host": "100.82.143.79",
    "Port": 5432,
    "Database": "postgres",
    "Username": "postgres",
    "Password": "postgres123",
    "Table":    "ohlcv_1m"
}
def get_data_db(table_name , args_list , query):

    conn = psycopg2.connect(**DB_CONFIG)
    data = pd.read_sql(query, conn)
    conn.close()
    return data



