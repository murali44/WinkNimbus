import sys
sys.path.append("./py-wink")
import wink


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
