# BTCUSD Stock Prediction

## Overview

This repository contains the code and documentation for developing, integrating, and deploying an LSTM model to predict the closing price of BTC/USD. The goal is to achieve a predicted closing price as close to the actual closing price as possible, with real-time prediction, automated trading via MetaTrader 5 (MT5), and updates sent to a Telegram channel.

## Objectives

1. **Predict Closing Prices**:
   - **Timeframes**:
     - 15-minute intervals: Make predictions every 15 minutes within the hour (4 times per hour). E.g., 6:00PM, 6:15PM, 6:30PM...
   - **Prediction Timing**: Predictions must happen within the first 15 seconds of the specified interval.

2. **Automate Trading in MT5**:
   - **Integration with MT5**: Using the MetaTrader 5 (MT5) platform for executing trades based on the model's predictions.
   - **Take Profit (TP)**: Set the take profit (TP) to the predicted closing price.
   - **Enable Automated Algo Trading**: Click on Tools -> Options -> Expert Advisors and tick on Allow algorithmic trading and Allow DLL imports.

3. **Real-Time Notifications Using Telegram Bot**:
   - **Open Telegram and Search for BotFather**: Open Telegram and search for "BotFather" in the search bar. And start a chat with BotFather.
   - **Create a New Bot**: 
        - Use the /newbot command to create a new bot.
        - Follow BotFather's instructions to assign a name and username to your bot.
        - Once completed, BotFather will provide you with a token. This token is required for authenticating your bot.
   - **Telegram Channel**: Create a Telegram group channel and the bot as a member giving it admin access.
   - **Get Chat ID**:
        - Open a browser and search for URl: https://api.telegram.org/bot"Your_Bot_Token"/getUpdates
        - On the group channel you have created, type /my_id @Your_Bot_name and then refresh the Browser having the same url and you will get the chat id here: "chat":{"id":-111111111111}

## Tools and Platforms

- **Programming Language**: Python
- **Libraries**:
  - Data Manipulation: Pandas, NumPy
  - Model Development: TensorFlow (Keras)
  - Trading Integration: MetaTrader5 (MT5) API
  - Notifications: python-telegram-bot

## Getting Started

### Prerequisites

- Python 3.x
- MetaTrader 5 installed and configured
- Telegram account and bot token

### Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/Nehlr1/BTCUSD-Stock-Prediction.git
   cd BTCUSD-Stock-Prediction
   ```
2. Install the required Python Libraries:
    ```sh
   pip install -r requirements.txt
   ```

### Usage
1. Data Collection and Model Training:
    - Run the script "mt5_ltsm_train.ipynb" to collect historical BTC/USD price data from MT5 and train the LSTM model using the collected data.

2. Real-Time Prediction and telegram notification:
    - Use the trained model to make real-time predictions, execute trades on MT5 and send notifications to Telegram using the script "mt5_automation.py".

   ```sh
   python mt5_automation.py
   ```

