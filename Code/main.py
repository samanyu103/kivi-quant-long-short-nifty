from config import START_DATE, END_DATE, DATA_FILE, UPDATE_MINUTES, CANDLE_TIME_FRAME, BASE_LOG_PATH #"quantx/logs"

from Exchange.logger import get_current_log_path
from Exchange.executor import Exchange
from data_store.data_feed import DataStore
from strategy.DGLongShort import DGLongShort
from strategy.base_strategy import Strategy

import time
import os
import os.path
import pandas as pd
import sys
import datetime as dt




class Infinity:
    def __init__(self):
        """
          Driver class for Strategy and Exchange
          This class fetches data at go and keeps sending minutely candles to both exchange and strategy
        """
        self.start_date = START_DATE
        self.end_date = END_DATE
        self.update_minutes = UPDATE_MINUTES
        self.log_path = get_current_log_path(self.start_date, self.update_minutes)

        # start = time.time()
        self.data_obj = DataStore(
            start_date=self.start_date,
            end_date=self.end_date,
            data_path = DATA_FILE, 
        )
        # update the end date to be a valid trading day
        self.end_date = self.data_obj.mkt_data.iloc[-1]['date'].date().strftime('%Y%m%d')

        # end = time.time()
        # print(f"datastore: {end-start}")

        self.exchange = Exchange(fill_type = "ON_OPEN", log_path=self.log_path)
        params = {
            "max_qty": 100,
            "sl_perc": 0.05,
            "update_minutes": self.update_minutes,
            "candle_tf": CANDLE_TIME_FRAME,
            "lot_size": 1
        }
        # self.strategy = DGLongShortRev(self.exchange, "DGLongShortRev", self.start_date,self.end_date, self.log_path, data_obj=self.data_obj, params = params)
        self.strategy = DGLongShort(self.exchange, "DGLongShort", self.start_date,self.end_date, self.log_path, data_obj=self.data_obj, params = params)

        # so that upon order filling strategy is notified
        self.exchange.order_update_subscribers.append(self.strategy)


    def run(self):        
        cnt_packets = 0
        while  self.data_obj.counter < self.data_obj.max_length:
            packet = self.data_obj.next()
            # print(packet)
            cnt_packets+=1
            self.exchange.on_data(packet)
            self.strategy.on_data(packet)


def run_sim():
    runner_class = Infinity()
    runner_class.run()
    del runner_class


def delete_logs():
    current_log_path = f"{BASE_LOG_PATH}/{START_DATE}"
    dir = f"{current_log_path}/{UPDATE_MINUTES}"
    os.system(f"rm -rf {dir}")  # delete existing log
    os.makedirs(current_log_path, exist_ok=True)
    os.mkdir(dir)



if __name__ == "__main__":
        

        if len(sys.argv) > 2:
            START_DATE = sys.argv[1]
            END_DATE = sys.argv[2]
        
        elif len(sys.argv) > 1:
            UPDATE_MINUTES = int(sys.argv[1])

        start = time.time()
        delete_logs()
        run_sim()
        end = time.time()
        print(f"main: {end-start}")