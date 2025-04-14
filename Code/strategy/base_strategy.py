import datetime

from Exchange.logger import setup_logger
from Exchange.executor import Exchange, Order
import pdb
import numpy as np
import matplotlib.pyplot as plt

# for one instrument
class Position:
    def __init__(self):
        self.pnl = 0
        # (total buy orders - total sell orders) * lot size basically total open position
        self.quantity = 0
        self.lot = 1
        # number of buy and sell orders (divided by lot size)
        self.total_buy = 0
        self.total_sell = 0
        # total_buy + total_sell
        self.total_trades = 0
        # total buy + total_sell * lot size
        self.volume =  0

        # summation buy_price*qty*lotsize
        self.avg_buy = 0
        self.avg_sell = 0
        # total pnl = avg_sell-avg_buy
        # turnover is avg_buy + avg_sell
        self.turnover =0
        # list are divided by lot
        self.buy_list = []
        self.sell_list = []
        self.pnl_list = []
        # win_pnl = sum(pnl for pnl in pnl_list if pnl > 0)
        self.win_pnl = 0
        self.loss_pnl = 0
        # summation of self.pnl_list * lot size = pnl
        # self.winning_trades = 0
        # self.sharpe = 0
        # self.drawdown = 0
    def show(self):
        print("pnl", self.pnl)
        print("quantity", self.quantity)
        print("total buy", self.total_buy)
        print("total sell", self.total_sell)
        print("buy list", self.buy_list)
        print("sell list", self.sell_list)


class StrategyModes:
    INTRADAY = 1 # this mode will liquidate position at 15:15 IST
    INTERDAY = 2 # this mode will not liquidate position at all

# general logger is written to at init of startegy and build_eod_report quantx/logs/20250205/stdout.log
# self.logger quantx/logs/20250205/20250205_lakshya.csv
class Strategy:

    def __init__(self, exchange: Exchange, name, start_date:str,end_date:str, log_path):

        self.log_path = log_path
        self.general_logger = setup_logger(f"{log_path}/stdout.log")     # quantx/logs/20250205/stdout.log
        self.logger  = setup_logger(f"{log_path}/order_details")

        self.name = name
        self.counter = 0
        self.start_date = start_date#datetime.datetime.strptime(start_date, "%Y%m%d").date()
        self.end_date = end_date#datetime.datetime.strptime(end_date, "%Y%m%d").date()
        self.exchange = exchange
        # log_file: quantx/logs/20250205/20250205_lakshya.csv
        self.last_pnl_update_time = None
        self.start_time = datetime.time(9, 15)
        self.liquidation_time = datetime.time(15, 15)  # time to start liquidating intraday strats, default
        self.report_building_time = datetime.time(15, 26)
        self.prev_date = None
        self.mode = StrategyModes.INTRADAY
        self.report_build = False
        self.eostrategy_report_build = False
        self.position=Position()


    def plot_equity_curve_and_drawdowns(self, equity_curve, drawdowns):
        # Plot PnL
        plt.subplot(3, 1, 1)
        plt.plot(self.pnl, label='PnL per Trade', color='blue')
        plt.title('PnL per Trade')
        plt.ylabel('PnL')
        plt.grid(True)
        plt.legend()

        # Plot Equity Curve
        plt.subplot(3, 1, 2)
        plt.plot(equity_curve, label='Equity Curve', color='green')
        plt.title('Equity Curve')
        plt.ylabel('Equity')
        plt.grid(True)
        plt.legend()

        # Plot Drawdowns
        plt.subplot(3, 1, 3)
        plt.plot(drawdowns, label='Drawdown', color='red')
        plt.title('Drawdown')
        plt.ylabel('Drawdown')
        plt.xlabel('Trade Index')
        plt.grid(True)
        plt.legend()

        plt.tight_layout()
        plt.show()


    def update_position(self):
        pos = self.position
        pos.total_trades = (pos.total_buy + pos.total_sell)
        pos.volume = pos.total_trades *pos.lot
        # if (len(pos.sell_list)!=len(pos.buy_list)):
        #     print("buy, sell unequal")
        #     print("sell_list", len(pos.sell_list))
        #     print("buy_list", len(pos.buy_list))
        for i in range(min(len(pos.sell_list), len(pos.buy_list))):
            pos.pnl_list.append(pos.sell_list[i] - pos.buy_list[i])
        # pos.pnl_list = np.array(pos.sell_list) - np.array(pos.buy_list)
        pos.win_pnl = sum(pnl for pnl in pos.pnl_list if pnl > 0)*pos.lot
        pos.loss_pnl = sum(-pnl for pnl in pos.pnl_list if pnl < 0)*pos.lot
        pos.turnover = pos.avg_buy + pos.avg_sell
        pos.pnl = pos.avg_sell - pos.avg_buy
        pnl2 = sum(pos.pnl_list)*pos.lot
        pnl_close = abs(pos.pnl-pnl2)<=1e-2
        # if (not pnl_close):
        #     print(f"pos.pnl {pos.pnl}, pnl2 {pnl2}") 
        pos.pnl = pnl2

        # assert pnl_close
        # assert(pos.total_buy == len(pos.buy_list))
        # assert(pos.total_sell == len(pos.sell_list))
        # assert(pos.total_buy == pos.total_sell)
        # assert(pos.volume == pos.total_trades*pos.lot)


    def build_eostrategy_report(self):
        if self.eostrategy_report_build == True:
            return
        self.general_logger.write(f"########################## End of startegy report for NIFTY 50 #####################################\n")
        self.update_position()
        pos = self.position
        total_pnl = pos.pnl
        total_volume = pos.volume
        total_trades = pos.total_trades
        total_pnl_list = pos.pnl_list
        win_pnl = pos.win_pnl
        loss_pnl = pos.loss_pnl
        total_turnover = pos.turnover

        winning_trades = sum(1 for pnl in total_pnl_list if pnl > 0)
        import math
        win_ratio = winning_trades / (total_trades - winning_trades) if (total_trades - winning_trades) != 0 else math.inf
        win_loss_points = win_pnl/loss_pnl if loss_pnl != 0 else math.inf
        pnl_turnover_ratio = (total_pnl / total_turnover) * 10_000 if total_turnover != 0 else 0


        if len(total_pnl_list) == 0 or np.std(total_pnl_list) == 0:
            sharpe = np.nan  # or set to 0, depending on your preference
        else:
            sharpe = np.mean(total_pnl_list) / np.std(total_pnl_list)
        sharpe_annualized = sharpe * np.sqrt(252)

        equity_curve = np.cumsum(total_pnl_list)
        running_max = np.maximum.accumulate(equity_curve)
        drawdowns = np.divide(
            equity_curve - running_max,
            running_max,
            out=np.zeros_like(equity_curve),
            where=running_max != 0
        )   
        if len(drawdowns) == 0:
            max_drawdown = np.nan  # or set to 0, depending on your use case
        else:
            max_drawdown = np.min(drawdowns)
        
                # Equity Curve Plot
        # self.plot_equity_curve_and_drawdowns(equity_curve, drawdowns)


        # write to general logger logs/{date}/stdout.csv
        self.general_logger.write(f"Total PNL:{total_pnl}, START_DATE : {self.start_date}, END_DATE:{self.end_date}\n")
        self.general_logger.write(f"Total Orders:{len(self.exchange.completed_order)}\n")
        # self.general_logger.write(f"Total Trades: total quanity buys + sells:{total_trades}\n")
        self.general_logger.write(f"Total volume traded:  {total_volume}\n")
        self.general_logger.write(f"Winning Trades:{winning_trades}\n")
        # self.general_logger.write(f"Win Ratio :{win_ratio}\n")
        # self.general_logger.write(f"Win loss points:{win_loss_points}\n")
        self.general_logger.write(f"PNL turover ratio in bps:{pnl_turnover_ratio}\n")
        self.general_logger.write(f"Sharpe Annually: {sharpe_annualized}\n")
        self.general_logger.write(f"Drawdown: {max_drawdown}\n")
        self.general_logger.write("###############################################################################\n")
 
            #     'PNL',
            #     'Total orders',
            #     'Total trades',
            #     'Volume traded',
            #     'Winning trades',
            #     'Win Loss Ratio',
            #     'Win loss points',
            #     'PNl turover ratio in bps',
            #     'Annualised Sharpe ratio',
            #     'Drawdown'

        # write to log/{date}/stats.csv
        row = [total_pnl,len(self.exchange.completed_order), total_volume,winning_trades, pnl_turnover_ratio, sharpe_annualized, max_drawdown]
        import csv, os

        csv_file = f"{self.log_path}/stats.csv"
        if not os.path.exists(csv_file):
            with open(csv_file, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'PNL',
                    'Total orders',
                    'Volume traded',
                    'Winning trades',
                    'PNl turover ratio in bps',
                    'Annualised Sharpe ratio',
                    'Drawdown'
                ])
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(row)


        # write to a file in reports
        
        self.eostrategy_report_build = True





    def on_order_update(self, order: Order):
        pos = self.position
        pos.lot = order.lot
        num_orders = int(order.quantity/order.lot)

        if order.side == Order.BUY and order.status == Order.FILLED:
            for _ in range(num_orders):
                pos.buy_list.append(float(order.fill_price))
                pos.total_buy+=1
            pos.quantity += order.quantity 
            pos.avg_buy += order.quantity * float(order.fill_price)
        elif order.side == Order.SELL and order.status == Order.FILLED:
            for _ in range(num_orders):
                pos.sell_list.append(float(order.fill_price))
                pos.total_sell+=1
            pos.quantity -= order.quantity
            pos.avg_sell += abs(order.quantity) * float(order.fill_price)
        # self.position.show()

# report
            


#  log_file = f"quantx/reports/{self.start_date}_stats"
#         import os
#         os.makedirs(os.path.dirname(log_file), exist_ok=True)


#         from config import UPDATE_MINUTES,CANDLE_TIME_FRAME
#         with open(log_file, "w") as f:  
#             f.write(f"Total PNL = {total_pnl}\n")
#             f.write(f"Total Orders = {len(self.exchange.completed_order)}\n")  
#             f.write(f"Total Trades (buys + sells) = {total_trades}\n")  
#             f.write(f"Total Volume Traded = {total_volume}\n")  
#             f.write(f"Winning Trades = {winning_trades}\n")  
#             f.write(f"Win Ratio = {win_ratio}\n")  
#             f.write(f"Win Loss Points = {win_loss_points}\n")  
#             f.write(f"PNL Turnover Ratio (bps) = {pnl_turnover_ratio}\n")  
#             f.write(f"Sharpe Annually = {sharpe_annualized}\n")  
#             f.write(f"Drawdown = {max_drawdown}\n") 

#             f.write("Config:\n")
#             f.write(f"START_DATE = {self.start_date}\n")
#             f.write(f"END_DATE = {self.end_date}\n")
#             f.write(f"UPDATE_MINUTES = {UPDATE_MINUTES}\n")
#             f.write(f"CANDLE_TIME_FRAME = {CANDLE_TIME_FRAME}\n") 
#             f.write("#" * 79 + "\n")  # Separator line  

#         # write to a csv in reports
#         import csv
#         report_dir = f"quantx/reports"
#         os.makedirs(report_dir, exist_ok=True) 
#         csv_file_path = os.path.join(report_dir, f"{self.start_date}_stats.csv")

#         headers = [
#             "PNL",
#             "Total orders",
#             "Total trades",
#             "Volume traded",
#             "Winning trades",
#             "Win Loss Ratio",
#             "Win loss points",
#             "PNL turnover ratio in bps",
#             "Annualized Sharpe ratio",
#             "Drawdown"
#         ]

#         # Prepare the data row
#         row = [
#             total_pnl,
#             len(self.exchange.completed_order),
#             total_trades,
#             total_volume,
#             winning_trades,
#             win_ratio,
#             win_loss_points,
#             pnl_turnover_ratio,
#             sharpe_annualized,
#             max_drawdown
#         ]

#         # Write the data to CSV
#         with open(csv_file_path, "w", newline="") as f:
#             writer = csv.writer(f)
#             writer.writerow(headers)
#             writer.writerow(row)

#         print(f"Stats written to {csv_file_path}")