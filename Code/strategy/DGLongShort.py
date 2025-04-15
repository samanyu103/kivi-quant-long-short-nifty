import pandas as pd
import datetime as dt
from copy import copy

import streaming_indicators as si
from collections import deque

from collections import OrderedDict
from Exchange.executor import Exchange, Order
from .base_strategy import Strategy, StrategyModes
import pdb


class DGLongShort(Strategy):
    __version__ = '1.0.0'
    STATE_INITIAL = 'INITIAL'
    STATE_SQUAREDOFF = 'SQUAREDOFF'

    def __init__(self, *args, data_obj, params):
        super().__init__(*args)
        self.params = params
        self.data_obj = data_obj
        self.start_time = dt.time(9,15)
        self.setup_time = dt.time(9,40)
        # self.max_qty = params['max_qty']
        self.lot=params['lot_size']
        self.sl_perc = params['sl_perc']
        self.bool_setup = False
        self.packet_cnt = 0
        self.last_update_dt = None
        self.upd = False
        self.state = self.STATE_INITIAL
        self.update_minutes = dt.timedelta(minutes=params['update_minutes'])
        self.tf = dt.timedelta(minutes=params['candle_tf'])
        self.date = None






    def setup(self, t):
        # indicators

        self.RSI = si.RSI(14)
        self.prev_RSI = deque(maxlen=3)
        self.PLUS_DI = si.PLUS_DI(14)
        self.prev_PLUS_DI = deque(maxlen=3)
        self.MINUS_DI = si.PLUS_DI(14)
        self.prev_MINUS_DI = deque(maxlen=3)
        self.BBANDS = si.BBands(14, 2)
        self.SMA = si.SMA(7)
        self.update_indicators(t)

        self.position_count = 0
        self.open_positions=[]

        return True

    def update_indicators(self, t):
        # function to fetch candles and update indicators
        if(self.last_update_dt is None):
            # 25 is 9:40 - 9:15 minutes
            candles = self.data_obj.fetch_candle(t-dt.timedelta(minutes=25), t, self.tf)
            # print(candles)
            # return
            if(candles is None):
                self.logger.write("No historical datan\n")
                return False
        else:#if(self.last_update_dt < t):
            candles = self.data_obj.fetch_candle(self.last_update_dt, t, self.tf)
            # print(candles)
            if(candles is None):
                self.logger.write(f"Live candle not received\n")
                # raise Exception("NoLiveData")
                return False
        if(not isinstance(candles, pd.DataFrame)): candles = pd.DataFrame([candles])
        if(len(candles) == 0):
            self.logger.write(f"No candles received\n")
            return False
        for _, candle in candles.iterrows():
            rsi = self.RSI.update(candle['close'])
            # print("prev RSI", self.prev_RSI)
            self.prev_RSI.append(rsi)
            plus_di = self.PLUS_DI.update(candle)
            self.prev_PLUS_DI.append(plus_di)
            minus_di = self.MINUS_DI.update(candle)
            self.prev_MINUS_DI.append(minus_di)
            self.BBANDS.update(candle['close'])
            self.SMA.update(candle['close'])
            self.last_update_dt = candle['date'] + self.tf
        if (
            len(self.prev_RSI) >= 3 and 
            self.prev_PLUS_DI[-3] not in [None, 0] and
            self.prev_MINUS_DI[-3] not in [None, 0] and
            self.prev_RSI[-3] not in [None, 0]
        ):
            self.rsi_rc = (self.prev_RSI[-1] - self.prev_RSI[-3]) / self.prev_RSI[-3] * 100
            self.plus_di_rc  = (self.prev_PLUS_DI[-1]  - self.prev_PLUS_DI[-3]) / self.prev_PLUS_DI[-3] * 100
            self.minus_di_rc = (self.prev_MINUS_DI[-1] - self.prev_MINUS_DI[-3]) / self.prev_MINUS_DI[-3] * 100
            self.band_diff = (self.BBANDS.upperband - self.BBANDS.lowerband) / candle['close'] * 100
        else:
            self.logger.write("Not enough data to compute rate of change safely\n")
            return False

        # self.rsi_rc = (self.prev_RSI[-1] - self.prev_RSI[-3]) / self.prev_RSI[-3] * 100
        # self.plus_di_rc  = (self.prev_PLUS_DI[-1]  - self.prev_PLUS_DI[-3] ) / self.prev_PLUS_DI[-3]  * 100
        # self.minus_di_rc = (self.prev_MINUS_DI[-1] - self.prev_MINUS_DI[-3]) / self.prev_MINUS_DI[-3] * 100
        # self.band_diff = (self.BBANDS.upperband - self.BBANDS.lowerband) / candle['close'] * 100
        self.candle = candle
        return True

    def update(self, t):
        updated = self.update_indicators(t)
        if(not updated): return False
        if(self._long_condition()):
            self.logger.write(f"Long condition met at {t}\n")
            entry_price = self.candle['close']
            order_id = self.exchange.place_order(entry_price, Order.BUY, 1*self.lot, self.lot)
            self.position_count += 1
            sl_price = round(entry_price - self.sl_perc * entry_price, 2)
            sl_order_id = self.exchange.place_order(sl_price,Order.SELL ,1*self.lot, self.lot, Order.SL_LIMIT, trigger_price=sl_price)
            sl_points = entry_price - sl_price
            tgt_price = round(entry_price + sl_points, 2)
            tgt_order_id = self.exchange.place_order(tgt_price, Order.SELL, 1*self.lot, self.lot,order_type=Order.LIMIT)
            self.open_positions.append({'order_id': order_id, 'sl_order_id':sl_order_id, 'tgt_order_id':tgt_order_id })
            self.logger.write(f"Entered Long, at {entry_price} SL: {sl_price} Target: {tgt_price}\n")

               
        elif(self._short_condition()):
            self.logger.write(f"Short condition met at {t}\n")
            entry_price = self.candle['close']
            order_id = self.exchange.place_order(entry_price, Order.SELL, 1*self.lot, self.lot)
            self.position_count -= 1
            sl_price = round(entry_price + self.sl_perc * entry_price, 2)
            sl_order_id = self.exchange.place_order(sl_price,Order.BUY ,1*self.lot, self.lot, Order.SL_LIMIT, trigger_price=sl_price)
            sl_points = sl_price - entry_price
            tgt_price = round(entry_price - sl_points, 2)
            tgt_order_id = self.exchange.place_order(tgt_price, Order.BUY, 1*self.lot, self.lot,order_type=Order.LIMIT)
            self.open_positions.append({'order_id': order_id, 'sl_order_id':sl_order_id, 'tgt_order_id':tgt_order_id })
            self.logger.write(f"Entered Short, at {entry_price} SL: {sl_price} Target: {tgt_price}\n")

        return True

    # def _long_condition(self):
    def _short_condition(self):
        return (
            (self.candle['high'] > self.BBANDS.upperband) &
            (self.rsi_rc > 5) &
            (self.plus_di_rc > 5) &
            (self.band_diff > 0.4)
        )

    # def _short_condition(self):
    def _long_condition(self):
        return (
            (self.candle['low'] < self.BBANDS.lowerband) &
            (self.rsi_rc <= -5) &
            (self.minus_di_rc < -5) &
            (self.band_diff > 0.4)
        )

    # def place_order(self, side, qty=1):
    #     order_id = self.exchange.place_order(self.candle['close'], side, qty*self.lot, self.lot)
    #     self.logger.write(f"Placed order {side} at {self.candle['close']} qty: {qty}\n")
    #     if(order_id is None):
    #         self.logger.write(f"Error in placing order in {side}\n")
    #         raise Exception("OrderPlacementException")
    #     return self.candle['close'], order_id
        


    def on_order_update(self, order):
        super().on_order_update(order)
        if(order.status == Order.FILLED):
            # reference self.open_positions updated when pos changed
            # stop loss or target has not been hit
            for pos in self.open_positions:
                if(order.id == pos['sl_order_id']):
                    if (order.side == "SELL"):
                        self.position_count-=1
                    else:
                        self.position_count+=1
                    self.logger.write(f"SL hit in Order {pos['order_id']} at {order.fill_price}\n")
                    pos['sl_order_id'] = None
                    self.exchange.cancel_order(pos['tgt_order_id'])
                    pos['tgt_order_id'] = None
                    return True
                elif(order.id == pos['tgt_order_id']):
                    if (order.side == "SELL"):
                        self.position_count-=1
                    else:
                        self.position_count+=1
                    self.logger.write(f"Target hit in Order {pos['order_id']} at {order.fill_price}\n")
                    pos['tgt_order_id'] = None
                    self.exchange.cancel_order(pos['sl_order_id'])
                    pos['sl_order_id'] = None
                    return True


    # doing self.position_count = 0
    def squareoff(self, t):
        # self.logger.write(f"squaring off...at {t}\n")
        if(self.position_count > 0):
            # type = aggressive so will automatically be filled and packet.open irrespective of self.candle['close']
            self.exchange.place_order(self.candle['close'], Order.SELL, self.position_count*self.lot, self.lot)
            self.logger.write(f"squaring off .. at {t}, placing {self.position_count} SELL orders\n")
            # self.place_order(Order.SELL, self.position_count)
        elif(self.position_count < 0):
            self.exchange.place_order(self.candle['close'], Order.BUY, -self.position_count*self.lot, self.lot)
            self.logger.write(f"sqauring off at {t}, placing {-self.position_count} BUY orders\n")
            # self.place_order(Order.BUY, -self.position_count)
        self.position_count=0
        self.state = self.STATE_SQUAREDOFF
        return True
    
    def setup_for_next_4_day(self):
        # self.eostrategy_report_build = False
        self.bool_setup = False
        self.last_update_dt = None
        self.state = self.STATE_INITIAL


    def on_data(self, packet):
        self.packet_cnt += 1
        t = packet.date
        time = t.time()  
        date = t.date()

        if (self.date == None):
            self.date = date
        if date - self.date >= dt.timedelta(days=4):
            self.date= date
            self.setup_for_next_4_day()
        
        if (not self.bool_setup and time >= self.setup_time ):
            # print("setting up once", t)
            self.setup(t)
            self.bool_setup = True
            # print("self.last_updated_time", self.last_update_dt)
        elif self.bool_setup and self.last_update_dt is not None and (t - self.last_update_dt) >= self.update_minutes and time<self.liquidation_time:
            # print("updating once")
            self.upd = True
            self.update(t)
            # print("self.last_updated_time", self.last_update_dt)
        elif self.state != self.STATE_SQUAREDOFF and time>=self.liquidation_time and date - self.date >= dt.timedelta(days=3):
            self.squareoff(t)
        elif time>= self.report_building_time and not self.eostrategy_report_build:
            if (date == (dt.datetime.strptime(self.end_date, "%Y%m%d")).date()):
                # print("building eo strategy report")
                self.build_eostrategy_report()