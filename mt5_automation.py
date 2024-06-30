import numpy as np
import pandas as pd
import time
from datetime import datetime, timedelta
import requests
import MetaTrader5 as mt5
from MetaTrader5 import *
from sklearn.preprocessing import MinMaxScaler
from keras import models
import threading

# Creating a dictionary for storing all the credentials for MT5
credentials = {
    "login": "ACCOUNT_ID",
    "password": "PASSWORD",
    "server": "ICMarketsSC-Demo",
    "path": "C:/Program Files/MetaTrader 5/terminal64.exe",
    "timeout": 60000,
    "portable": False 
}

# Connecting to MT5 using the credentials above
if mt5.initialize(path=credentials['path'],
                  login=credentials['login'],
                  password=credentials['password'],
                  server=credentials['server'],
                  timeout=credentials['timeout'],
                  portable=credentials['portable']):
    print("Platform MT5 launched correctly")
else:
    print(f"There has been a problem with initialization: {mt5.last_error()}")

def get_latest_data():
    symbol = "BTCUSD"
    timeframe = mt5.TIMEFRAME_M15
    num_candles = 120

    # Getting the last completed candle
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 1, num_candles)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df[['close']].values


def execute_trade(symbol, predicted_price, lot_size=0.1):
    # This function opens up a trade
    if not mt5.initialize():
        print("Initialize() failed, error code =", mt5.last_error())
        return None
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Failed to get symbol info for {symbol}")
        return None

    if not symbol_info.visible:
        print(f"{symbol} is not visible, trying to switch on")
        if not mt5.symbol_select(symbol, True):
            print(f"symbol_select({symbol}) failed, exit")
            return None

    price = mt5.symbol_info_tick(symbol).ask

    # Determining order type
    if predicted_price > price:
        order_type = mt5.ORDER_TYPE_BUY
    else:
        order_type = mt5.ORDER_TYPE_SELL

    deviation = 20
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": 0.0,  # We're not setting a stop loss
        "tp": 0.0,  # We'll set the TP in manage_trade_closure function
        "deviation": deviation,
        "magic": 234000,
        "comment": "python script open",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    result = mt5.order_send(request)
    if result is None:
        print(f"order_send() failed, error code: {mt5.last_error()}")
        return None
    
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print("Order successfully placed!")
        return result
    else:
        print(f"Order failed, retcode: {result.retcode}")
        print(f"Description: {result.comment}")
        
        # Printing detailed error information
        result_dict = result._asdict()
        for field in result_dict.keys():
            print(f"{field}={result_dict[field]}")
            if field == "request":
                traderequest_dict = result_dict[field]._asdict()
                for tradereq_field in traderequest_dict:
                    print(f"traderequest: {tradereq_field}={traderequest_dict[tradereq_field]}")
    
    return None


def reverse_type(type):
    # This function reverses the type of the order
    if type == mt5.ORDER_TYPE_BUY:
        return mt5.ORDER_TYPE_SELL
    elif type == mt5.ORDER_TYPE_SELL:
        return mt5.ORDER_TYPE_BUY
    
def get_close_price(symbol, type):
    # This function gets the close price for ask and bid
    if type == mt5.ORDER_TYPE_BUY:
        return mt5.symbol_info(symbol).bid
    elif type == mt5.ORDER_TYPE_SELL:
        return mt5.symbol_info(symbol).ask

def manage_trade_closure(symbol, trade_result, predicted_price, interval_end_time):
    trade_open_time = datetime.now()
    five_minute_mark = trade_open_time + timedelta(minutes=5)
    
    # Waiting until 5 minutes have passed
    while datetime.now() < five_minute_mark:
        time.sleep(1)  # Checking every second

    # Setting the TP at the 5-minute mark
    position = mt5.positions_get(ticket=trade_result.order)
    if not position:
        return

    position = position[0]

    point = mt5.symbol_info(symbol).point
    current_price = mt5.symbol_info_tick(symbol).ask if position.type == 0 else mt5.symbol_info_tick(symbol).bid

    # Calculating TP ensuring it's at least 10 points away from the current price
    min_distance = 10 * point
    if position.type == 0:  # Buying position
        tp = max(predicted_price, current_price + min_distance)
    else:  # Selling position
        tp = min(predicted_price, current_price - min_distance)

    tp_round = round(tp, mt5.symbol_info(symbol).digits)

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": position.ticket,
        "tp": tp_round + 100 * point,
    }

    max_attempts = 10
    for attempt in range(max_attempts):
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"TP set to {tp_round}")
            break
        else:
            print(f"Failed to set TP, attempt {attempt + 1}/{max_attempts}")
            if result:
                print(f"Retcode: {result.retcode}")
            time.sleep(1)  # Waiting before retrying
    else:
        print("Failed to set TP after maximum attempts")

    # Waiting until the end of the interval
    while datetime.now() < interval_end_time:
        time.sleep(1)  # Checking every second
        position = mt5.positions_get(ticket=trade_result.order)
        if not position:
            print("Trade closed before interval end (TP hit)")
            return

    # If we have reached this point, closing the trade at interval end
    position = mt5.positions_get(ticket=trade_result.order)
    position = position[0]
    if position:
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position.ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": reverse_type(position.type),
            "price": get_close_price(position.symbol, position.type),
            "deviation": 20,
            "magic": 234000,
            "comment": "python script close at interval end",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
      
        for attempt in range(max_attempts):
            result = mt5.order_send(close_request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                print("Trade closed at interval end")
                break
            else:
                print(f"Failed to close trade, attempt {attempt + 1}/{max_attempts}")
                if result:
                    print(f"Retcode: {result.retcode}")
                time.sleep(1)  # Waiting before retrying
        else:
            print("Failed to close trade after maximum attempts")
    else:
        print("Trade was already closed")

    # Calculating and returning the profit/loss
    trade_history = mt5.history_deals_get(ticket=trade_result.order)
    if trade_history:
        profit = sum(deal.profit for deal in trade_history)
        print(f"Profit/Loss: {profit}")
        return profit
    else:
        print("Could not retrieve trade history")
        return None


def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("Message sent successfully!")
        else:
            print(f"Failed to send message. Status code: {response.status_code}")
            print(f"Response: {response.text}")
    except requests.RequestException as e:
        print(f"An error occurred while sending the message: {e}")

def main():
    token = "BOT_TOKEN"
    chat_id = "CHAT_ID"
    scaler = MinMaxScaler(feature_range=(0, 1))
    
    try:
        model = models.load_model('./saved_model/model_v3.keras')
    except Exception as e:
        print(f"Failed to load the model: {e}")
        return

    while True:
        try:
            current_time = datetime.now()
            
            # Checking if it's the beginning of a 15-minute interval
            if current_time.minute % 15 == 0 and current_time.second < 15:
                # Getting the latest data
                latest_data = get_latest_data()
                if latest_data is None or len(latest_data) == 0:
                    print("Failed to get latest data. Skipping this iteration.")
                    continue
                
                # Preparing the data for prediction
                scaled_data = scaler.fit_transform(latest_data)
                x_pred = np.array([scaled_data[-60:]])
                x_pred = np.reshape(x_pred, (x_pred.shape[0], x_pred.shape[1], 1))
                
                # Making prediction
                prediction = model.predict(x_pred)
                predicted_price = scaler.inverse_transform(prediction)[0][0]

                # Getting actual price
                actual_price = mt5.symbol_info_tick("BTCUSD").ask

                print(f"Current price: {actual_price:.2f}, Predicted price: {predicted_price:.2f}")

                # Checking if the predicted price is within a reasonable range (e.g., ±10% of the actual price)
                if not (0.9 * actual_price <= predicted_price <= 1.1 * actual_price):
                    print(f"Predicted price ({predicted_price:.2f}) is outside the reasonable range. Skipping trade.")
                    continue

                # Executing trade
                trade_result = execute_trade("BTCUSD", predicted_price)
                if trade_result is None:
                    print("Failed to execute trade. Skipping this iteration.")
                    continue

                try:
                    # Calculating the end time of this 15-minute interval
                    interval_end_time = current_time.replace(second=0, microsecond=0)
                    minutes_to_add = 15 - (interval_end_time.minute % 15)
                    interval_end_time += timedelta(minutes=minutes_to_add)
                except ValueError as e:
                    print(f"Error calculating interval end time: {e}")
                    continue

                # Starting a new thread to manage the trade closure
                thread = threading.Thread(target=manage_trade_closure, args=("BTCUSD", trade_result, predicted_price, interval_end_time))
                thread.start()

                # Sending Telegram notification about trade opening
                open_message = f"Trade opened:\nCurrent price: {actual_price:.2f}\nPredicted price: {predicted_price:.2f}"
                send_telegram_message(token, chat_id, open_message)
                
                # Waiting for the thread to complete
                thread.join()
                
                # Waiting until the next 15-minute interval
                next_prediction_time = interval_end_time
                time_to_sleep = (next_prediction_time - datetime.now()).total_seconds()
                if time_to_sleep > 0:
                    time.sleep(time_to_sleep)
                else:
                    print("Negative sleep time calculated, skipping sleep")
            
            else:
                # Waiting for 1 second before checking again
                time.sleep(1)
        
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            time.sleep(60)  # Waiting for 1 minute before trying again

if __name__ == "__main__":
    main()