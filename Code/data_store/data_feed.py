import datetime
import os.path
import pandas as pd

import pdb

class DataStore:

    def __init__(self, start_date:str, end_date:str, data_path:str):
        self.start_date = datetime.datetime.strptime(start_date, "%Y%m%d")
        self.end_date = datetime.datetime.strptime(end_date, "%Y%m%d")
        self.data_path = data_path
        self.counter = 0
        self.mkt_data = None
        self.max_length = 0
        self.reader()

    def generate_all_dates_between(self):
        dates = []
        while self.start_date <= self.end_date:
            dates.append(self.start_date.strftime("%Y%m%d"))
            self.start_date += datetime.timedelta(days=1)
        return dates

    def reader(self):
        if os.path.isfile(self.data_path):
            data = pd.read_csv(self.data_path)
        else:
            print("data file not found")
            return
        data['date'] = pd.to_datetime(data['date'])
        data = data.drop(columns=['volume'])
        # start date time 0:0 to end date+1 days to include the entire end date.
        data = data[(data['date'] >= self.start_date) & (data['date'] < self.end_date+datetime.timedelta(days=1))]
        data = data.reset_index(drop=True)
        # pdb.set_trace()
        self.mkt_data = data
        self.max_length = self.mkt_data.shape[0]

    def next(self):
        current_packet = self.mkt_data.iloc[self.counter]
        self.counter += 1
        return current_packet
    

    def fetch_candle(self, from_dt, to_dt, tf):

        df = self.mkt_data

        # Filter between from_dt and to_dt
        mask = (df['date'] >= from_dt) & (df['date'] < to_dt)
        df_filtered = df.loc[mask]
        df_filtered = df_filtered.set_index('date')
        df_filtered.index.name = 'date'


        if df_filtered.empty:
            return pd.DataFrame()

        # Resample to candles
        resampled = df_filtered.resample(tf).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last'
        }).dropna()

        resampled.reset_index(inplace=True)

        return resampled


