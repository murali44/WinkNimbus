#!/usr/bin/env python
import ConfigParser
import datetime
import itertools
import pytz
import simplejson
import sys
import time
import traceback
import urllib
import json

from googlefinance import getQuotes
import mintapi
from nimbus import Nimbus
import pandas as pd
from rescuetime.api.service import Service
from rescuetime.api.access import AnalyticApiKey
from yahoo_finance import Share


# Globals
NIMBUS = Nimbus("./cfg/wink.cfg")
cfg = ConfigParser.RawConfigParser()
cfg.read("./cfg/app.cfg")
update_period_sec = int(cfg.get('global', 'update_period_sec'))
mint_email = cfg.get('mint', 'email')
mint_password = cfg.get('mint', 'password')
monthly_budget = float(cfg.get('mint', 'monthly_budget'))
MINT_DISPLAY = itertools.cycle(["spent", "can_spend"])
rescuetime_apikey = cfg.get('rescuetime', 'apikey')
google_apikey = cfg.get('traffic', 'google_apikey')
origin_cord = cfg.get('traffic', 'origin_cord')
dest_cord = cfg.get('traffic', 'destination_cord')

def trading_hours():
    start = datetime.time(8, 30, 0)
    end = datetime.time(15, 0, 0)
    eastern = pytz.timezone('US/Eastern')
    return start <= datetime.datetime.now(eastern).time() <= end


def percentage(part, whole):
    change = 0
    if part < whole:
        return 0
    elif part > whole:
        change = part - whole
    percent = 100 * float(change)/float(whole)
    return percent


def update_stock(dial, stock):
    stk = Share(stock)
    prev_close_price = float(stk.get_prev_close())
    stk_data = json.loads(json.dumps(getQuotes(stock), indent=2))[0]
    stk_price = float(stk_data['LastTradePrice'])
    NIMBUS.set_dial_value(dial, percentage(stk_price, prev_close_price),
                          "%s:%.2f" % (stock, stk_price))


def update_mint(dial, total_spent, can_spend, spent_percent):
    if MINT_DISPLAY.next() == 'spent':
        NIMBUS.set_dial_value(dial, spent_percent, "Budg:%d" % total_spent)
    else:
        NIMBUS.set_dial_value(dial, spent_percent, "Left:%d" % can_spend)


def get_mint_data():
    mint = mintapi.Mint(mint_email, mint_password)
    budgets = json.loads(json.dumps(mint.get_budgets(), indent=2))
    total_spent = 0
    can_spend = 0
    for budget in budgets['spend']:
        item = json.loads(json.dumps(budget))
        total_spent = total_spent + item['amt']
        can_spend = can_spend + item['rbal']
    spent_percent = 100 * float(total_spent)/float(monthly_budget)
    return total_spent, can_spend, spent_percent


def update_rescuetime_efficiency(dial):
    try:
        today_date = datetime.date.today().strftime("%Y-%m-%d")
        s = Service.Service()
        k = AnalyticApiKey.AnalyticApiKey(rescuetime_apikey, s)
        p = {'restrict_begin': today_date,
             'restrict_end': today_date,
             'restrict_kind': 'efficiency',
             'perspective': 'interval',
             'resolution_time': 'day'}
        d = s.fetch_data(k, p)

        df = pd.DataFrame(d['rows'], columns=d['row_headers'])
        efficiency = df["Efficiency (percent)"]
        dates = df["Date"]
        eff = int(efficiency.tail(1))
        NIMBUS.set_dial_value(dial, eff, "Prod:%d" % eff)
    except:
        print "rescuetime Failed"


def update_traffic_info(dial):
    utc_now = int(time.time())
    url = "https://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&mode=driving&language=en-EN&sensor=false&departure_time={2}&key={3}".format(str(origin_cord),str(dest_cord), str(utc_now), str(google_apikey))
    result= simplejson.load(urllib.urlopen(url))
    driving_time = result['rows'][0]['elements'][0]['duration_in_traffic']['value']
    d_time = int(driving_time)/60
    NIMBUS.set_dial_value(3, 0, "Traf:%d" % d_time)


def main():
    stock_list = cfg.get('stocks', 'stocks')
    stocks = itertools.cycle(stock_list.replace(" ", "").split(","))

    total_spent, can_spend, spent_percent = get_mint_data()
    update_mint(1, total_spent, can_spend, spent_percent)

    while 1:
        # stocks
        if trading_hours():
            update_stock(0, stocks.next())

        # mint
        # check mint only once an hour
        if datetime.datetime.now().minute == 0:
            total_spent, can_spend, spent_percent = get_mint_data()
        update_mint(1, total_spent, can_spend, spent_percent)

        # rescuetime daily efficiency
        if datetime.datetime.now().minute in [0, 15, 30, 45]:
            print "rescuetime update"
            update_rescuetime_efficiency(2)

	# traffic info
	if datetime.datetime.now().minute in [0, 15, 30, 45]:
	    update_traffic_info(3)

        # sleep
        time.sleep(update_period_sec)

    # normally, we should never return...
    return -1


if __name__ == "__main__":
    # do forever, unless we receive SIGINT:
    while 1:
        try:
            ret = main()
        except KeyboardInterrupt:
            ret = 0
            break
        except:
            traceback.print_exc(file=sys.stdout)
            continue

    sys.exit(ret)
