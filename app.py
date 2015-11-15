#!/usr/bin/env python
import ConfigParser
import datetime
import itertools
import sys
import time
import traceback
import json

from googlefinance import getQuotes
import mintapi
from yahoo_finance import Share

sys.path.append("./py-wink")
import wink


def percentage(part, whole):
    if part < 1:
        return 0
    elif part > whole:
        return 99

    percent = 100 * float(part)/float(whole)
    if percent > 99:
        return 99
    return percent


class Nimbus(object):
    def __init__(self, secret_file_name):
        w = wink.init(secret_file_name)

        if "cloud_clock" not in w.device_types():
            raise RuntimeError(
                "you do not have a cloud_clock associated with your account!"
            )

        # Wrap cloud_clock with Nimbus object
        c = w.cloud_clock()
        self.__class__ = type(c.__class__.__name__,
                              (self.__class__, c.__class__),
                              {})
        self.__dict__ = c.__dict__

    def set_dial_value(self, dial_num, percent, label):
        dial = self.dials()[dial_num]
        # the dial servo will always display a percentage [0..100],
        # we'll set up the dial minimum and maximum to reflect that:
        dial_config = {
            "scale_type": "linear",
            "rotation": "cw",
            "min_value": 0,
            "max_value": 100,
            "min_position": 0,
            "max_position": 360,
            "num_ticks": 12
        }

        # log statement:
        print "percent = %d%%, label = %s" % (percent, label)

        # assert manual control (chan. 10) with new config, value, & label:
        dial.update(dict(
            channel_configuration=dict(channel_id="10"),
            dial_configuration=dial_config,
            label=label,
            value=percent,
        ))


def main():
    cfg = ConfigParser.RawConfigParser()
    cfg.read("./cfg/app.cfg")
    update_period_sec = int(cfg.get('global', 'update_period_sec'))

    mint_email = cfg.get('mint', 'email')
    mint_password = cfg.get('mint', 'password')
    monthly_budget = cfg.get('mint', 'monthly_budget')

    stock_list = cfg.get('stocks', 'stocks')
    stocks = itertools.cycle(stock_list.replace(" ", "").split(","))

    my_nimbus = Nimbus("./cfg/wink.cfg")

    while 1:
        # stocks
        stock = stocks.next()
        stk = Share(stock)
        open_price = float(stk.get_open())
        stk_json = json.dumps(getQuotes(stock), indent=2)
        stk_data = json.loads(stk_json)[0]
        stk_price = float(stk_data['LastTradePrice'])
        percent = percentage(stk_price, open_price)
        my_nimbus.set_dial_value(0, percent, "%s:%.2f" % (stock, stk_price))

        # monthly budget from mint
        # check mint only once an hour at the top of the hour
        if datetime.datetime.now().minute == 0:
            mint = mintapi.Mint(mint_email, mint_password)
            budgets = json.loads(json.dumps(mint.get_budgets(), indent=2))
            total_spent = 0
            can_spend = 0
            for budget in budgets['spend']:
                item = json.loads(json.dumps(budget))
                total_spent = total_spent + item['amt']
                can_spend = can_spend + item['rbal']
            percent = percentage(total_spent, monthly_budget)
            my_nimbus.set_dial_value(2, percent, "%d" % total_spent)
            my_nimbus.set_dial_value(3, 0, "Left:%d" % can_spend)

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
            print "Exception:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60
            continue

    sys.exit(ret)
