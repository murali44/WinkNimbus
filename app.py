#!/usr/bin/env python

import sys, traceback
sys.path.append("./py-wink")

import wink

import ConfigParser
import time
import json
import datetime
import mintapi
from googlefinance import getQuotes
from yahoo_finance import Share

def scale_value(x, in_min, in_max, out_min, out_max):
    try:
        return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min
    except ZeroDivisionError:
        return 0

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
            current_time = datetime.datetime.now().time()
            print "percent = %d%%, label = %s" % (percent, label)

            # assert manual control (chan. 10) with new config, value, & label:
            dial.update(dict(
                channel_configuration=dict(channel_id="10"),
                dial_configuration=dial_config,
                label=label,
                value=percent,
            ))


def main():
    app_cfg = ConfigParser.RawConfigParser()
    app_cfg.read("./cfg/app.cfg")
    update_period_sec = int(app_cfg.get('global', 'update_period_sec'))

    my_nimbus = Nimbus("./cfg/wink.cfg")

    mint_cfg = ConfigParser.RawConfigParser()
    mint_cfg.read("./cfg/mint.cfg")
    mint_email = mint_cfg.get('auth', 'email')
    mint_password = mint_cfg.get('auth', 'password')
    monthly_budget = mint_cfg.get('auth', 'monthly_budget')

    while 1:
        # stocks
        oas = Share('OAS')
        oas_open_price = float(oas.get_open())
        oas_json = json.dumps(getQuotes('OAS'), indent = 2)
        oas_data = json.loads(oas_json)[0]
        oas_price = float(oas_data['LastTradePrice'])
        percent = percentage(oas_price, oas_open_price)
        my_nimbus.set_dial_value(0, percent,
                                 "OAS:%.2f" % oas_price)

        ugaz = Share('UGAZ')
        ugaz_open_price = float(ugaz.get_open())
        ugaz_json = json.dumps(getQuotes('UGAZ'), indent = 2)
        ugaz_data = json.loads(ugaz_json)[0]
        ugaz_price = float(ugaz_data['LastTradePrice'])
        percent = percentage(ugaz_price, ugaz_open_price)
        my_nimbus.set_dial_value(1, percent,
                                 "UGAZ:%.2f" % ugaz_price)

        # monthly budget from mint
        mint = mintapi.Mint(mint_email, mint_password)
        budgets = json.loads(json.dumps(mint.get_budgets(), indent = 2))
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
