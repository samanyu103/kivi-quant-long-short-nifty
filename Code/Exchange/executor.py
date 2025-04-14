from .logger import setup_logger
import datetime
from config import FILL_TYPE
import pandas as pd



class Order:
    BUY = "BUY"
    SELL = "SELL"
    AGGRESSIVE = "AGGRESSIVE"
    LIQUIDATE = "LIQUIDATE"
    LIMIT = "LIMIT"
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    SL_LIMIT = "SL_LIMIT"

    def __init__(self, id, price, side, quantity, lot, logger="order", order_type="AGGRESSIVE", trigger_price=None):
        self.id = id
        self.price = price
        self.side = side  # "BUY", "SELL"
        self.status = "INITIATED"
        self.quantity = quantity
        self.fill_price = 0
        self.order_type = order_type  # AGGRESSIVE, LIMIT, SL_LIMIT
        self.order_time = None
        self.fill_time = None
        self.trigger_price = trigger_price
        self.lot =lot

# exchange has logger: pending placed orderd and fill_logger: filled orders
class Exchange:
    """
    Every packet is first received by the exchange and then the strategy
    orders: inst wise open orders
    fill_type: can be filled on OPEN_OPEN, ON_CLOSE, ON_HIGH, ON_LOW
    completed_order: maintain a list of all orders completed so far
    order_update_subscribers : this can be any type of object to receive order updates -  in our case it is a strategy
    """

    # log_name=self.start_date
    def __init__(self,fill_type, log_path):
        self.orders = []
        self.completed_order = []
        self.counter = 0
        self.fill_type = fill_type 
        self.logger = setup_logger(f"{log_path}/orders.csv")
        self.fill_logger = setup_logger(f"{log_path}/fill_orders.csv")
        log_headers = "id, order_time, fill_time, price, side, status, quantity/lot, fill_price, order_type\n"
        self.logger.write(log_headers)
        self.fill_logger.write(log_headers)
        self.current_time = None
        self.order_update_subscribers = list()


#  if order pending the log it in self.logger else log it in self.fill_logger
    def log_order(self, order):
        log_line = (f"{order.id}, {order.order_time}, {order.fill_time}, {order.price}, {order.side}, {order.status}, {int(order.quantity/order.lot)},{order.fill_price}, {order.order_type}")
        if order.status == "PENDING":
            # print(log_line)
            self.logger.write(log_line + '\n')
            # self.logger.flush()
        elif order.status == "FILLED":
            # print(log_line)
            self.fill_logger.write(log_line + '\n')
            # self.fill_logger.flush()


    def place_order(self, price, side, quantity, lot, order_type=Order.AGGRESSIVE, trigger_price=None):
        # print("placing order at price", price, self.counter)
        order = Order(self.counter, price, side, quantity, lot, trigger_price=trigger_price)
        order.status = Order.PENDING
        order.order_time = self.current_time
        order.order_type = order_type
        # order pending logged to self.logger 
        self.log_order(order)
        self.orders.append(order)
        self.counter +=1
        return self.counter-1

    def cancel_order(self, order_id):
        self.orders = [order for order in self.orders if order.id != order_id]

    def raise_order_update(self, order):
        for strategy in self.order_update_subscribers:
            strategy.on_order_update(order)

    def post_filled_order_checks(self, order, packet):
        order.fill_time = self.current_time
        order.status = Order.FILLED
        self.raise_order_update(order)
        self.completed_order.append(order)
        # print(len(self.completed))
        # fill logger
        self.log_order(order)
        self.orders.remove(order)

    def on_data(self, packet): 
        self.current_time = packet.date   
        orders_to_fill = self.orders
        # get orders for current packet instrument  
        if orders_to_fill:
            for order in orders_to_fill:
                if order.price == 0:  # market order for liquidation
                    order.price = float(packet.open)
                if order.side == Order.BUY:
                    # SL order for buy will be a sell order with low sl price
                    # SL order for sell will be a buy order with high price
                    if order.order_type == Order.SL_LIMIT:
                        if (packet.open > order.trigger_price):
                            order.fill_price = order.trigger_price
                            self.post_filled_order_checks(order, packet)
                    if order.order_type in {Order.AGGRESSIVE, Order.LIQUIDATE}:
                        if (FILL_TYPE == "ON_OPEN"):
                            order.fill_price = packet.open  # filling at open
                        elif (FILL_TYPE == "ON_CLOSE"):
                            order.fill_price = packet.open 
                        elif (FILL_TYPE == "ON_HIGH"):
                            order.fill_price = packet.high
                        elif (FILL_TYPE == "ON_LOW"):
                            order.fill_price = packet.low
                        # print("filling order", order.price, "at price", packet.open)
                        self.post_filled_order_checks(order, packet)
                    elif order.order_type == Order.LIMIT:
                        #  buy side order if low < price then price must be reached during the candle hence execute order.
                        if packet.low <= order.price:
                            order.fill_price = order.price
                            self.post_filled_order_checks(order, packet)
                elif order.side == Order.SELL:
                    # SL order for buy will be a sell order with low sl price
                    # SL order for sell will be a buy order with high price
                    if order.order_type == Order.SL_LIMIT:
                        if (packet.open < order.trigger_price):
                            order.fill_price = order.trigger_price
                            self.post_filled_order_checks(order, packet)
                        
                    if order.order_type in {Order.AGGRESSIVE, Order.LIQUIDATE}:
                        # if packet.open >= order.price:
                        if (FILL_TYPE == "ON_OPEN"):
                            order.fill_price = packet.open  # filling at open
                        elif (FILL_TYPE == "ON_CLOSE"):
                            order.fill_price = packet.open 
                        elif (FILL_TYPE == "ON_HIGH"):
                            order.fill_price = packet.high
                        elif (FILL_TYPE == "ON_LOW"):
                            order.fill_price = packet.low
                        self.post_filled_order_checks(order, packet)
                    elif order.order_type == Order.LIMIT:
                        # sell side high > price then price must be reached during the candle thus order would get executed.
                        if packet.high >= order.price:
                            order.fill_price = order.price
                            self.post_filled_order_checks(order, packet)