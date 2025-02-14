from lumibot.brokers import Alpaca 
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert_utils import estimate_sentiment
#from pandas import Timedelta


API_KEY = "PKEBSVCGNXA33P7LK5WT"
API_SECRET = "9gtUj0A8hGapYdN4Rb8ZlPgJkGjB85T4xKTJb04Q"
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
    "API_KEY":API_KEY,
    "API_SECRET": API_SECRET,
    "PAPER": True
}
# Alpaca is the broker, YahooDataBackTesting is the framework for backtesting, and Strategy is the actual trading bot

class MLTrader(Strategy):
    def initialize(self, symbol:str="SPY", cash_at_risk:float=.5):
        self.symbol = symbol
        self.sleeptime = "24H" #Dictates how frequently the bot will trade
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    #position sizing and limits
    def position_sizing(self):
        #amount of cash that is still left in the bank
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        #calculate position size (will be calculated based on a metric called "cash at risk")
        #basically how much of a cash balance the bot is willing to risk on every trade
        quantity = round(cash * self.cash_at_risk / last_price , 0) 
        return cash, last_price, quantity
    
    #Get dates for backtesting
    def get_dates(self):
        #current date based on backtest
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days = 3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')
    
    #Get news using alpaca api
    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, start= three_days_prior, end=today)
        #news processing
        news = [event.__dict__["_raw"]["headline"] for event in news]
        # Print each headline
        print(news)
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        if cash > last_price:
             #create a simple baseline trade
            if sentiment == "positive" and probability > .999:
                if self.last_trade == "sell":
                    self.sell_all()
                print(probability, sentiment)
                order = self.create_order(
                        self.symbol,
                        quantity, #how many of that symbol the bot will buy
                        "buy",
                        type="bracket",
                        take_profit_price = last_price*1.2, #Take profit limit, when threshold hits, it automatically sells
                        stop_loss_price = last_price*.95    #stop loss limit, when this threshold hits, it automatically sells (will change depending on short or long order)
                )
                self.submit_order(order)
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > .999:
                if self.last_trade == "buy":
                    self.sell_all()
                print(probability, sentiment)
                order = self.create_order(
                        self.symbol,
                        quantity, #how many of that symbol the bot will buy
                        "sell",
                        type="bracket",
                        take_profit_price = last_price*.8, #Take profit limit, when threshold hits, it automatically sells
                        stop_loss_price = last_price*1.05    #stop loss limit, when this threshold hits, it automatically sells (will change depending on short or long order)
                )
                
                self.submit_order(order)
                self.last_trade = "sell"


start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 7, 4)
#initial ID is called the "life cycle method" 
#When the bot is started, the initalized method is gonna run once and the on trading iteration
#is going to run everytime tehre is a tick (everytime theres a new data from the data source, 
#a trade could be executed)
broker = Alpaca(ALPACA_CREDS)
#create instance of strategy
strategy = MLTrader(name='mlstrat', broker=broker, parameters={"symbol":"SPY", "cash_at_risk":.5})
#evaluate how well the bot would run
strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol":"SPY",  "cash_at_risk":.5}
)