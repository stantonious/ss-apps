#!/home/pi/venvs/ss/bin/python3
""" Seeed 2hat mic LED app """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import argparse
import time
import json
import sys
import os
import pika
from app_utils import base, apa102
import numpy as np
import colour
from business_rules import variables, actions, run_all, fields

parser = argparse.ArgumentParser(
    description='send notification for provided inference')

parser.add_argument('--conf1', type=float, required=True)
parser.add_argument('--conf2', type=float, required=True)
parser.add_argument('--conf3', type=float, required=True)
parser.add_argument('--idx1', type=int, required=True)
parser.add_argument('--idx2', type=int, default=-1)
parser.add_argument('--idx3', type=int, default=-1)
parser.add_argument('--led-color1', type=str, required=True)
parser.add_argument('--led-color2', type=str, required=True)
parser.add_argument('--led-color3', type=str, required=True)


class LedInference(object):
    last_conf1 = 0.0
    last_conf2 = 0.0
    last_conf3 = 0.0

    def _init_(self):
        self.last_conf1 = 0.0
        self.last_conf2 = 0.0
        self.last_conf3 = 0.0


class LedVars(variables.BaseVariables):
    def __init__(self, inf):
        self.tracked_inference = inf

    @variables.numeric_rule_variable(label='current confidence')
    def last_conf1(self):
        return self.tracked_inference.last_conf1

    @variables.numeric_rule_variable(label='current confidence1')
    def last_conf2(self):
        return self.tracked_inference.last_conf2

    @variables.numeric_rule_variable(label='current confidence2')
    def last_conf3(self):
        return self.tracked_inference.last_conf3


class NotificationActs(base.InferenceActs):

    def __init__(self, tracked_inference, c1, c2, c3, led_device):
        super().__init__(tracked_inference)
        self.c1 = colour.Color(c1) if c1 else None
        self.c2 = colour.Color(c2) if c2 else None
        self.c3 = colour.Color(c3) if c3 else None
        self.dev = led_device

    @actions.rule_action(params={'led_states': fields.FIELD_NUMERIC})
    def paint_strip(self,
                    led_states):
        c1 = self.c1 if led_states & 0x0001 else None
        c2 = self.c2 if led_states & 0x0002 else None
        c3 = self.c3 if led_states & 0x0004 else None
        print ('painting strip', led_states, c1, c2, c3)

        if c1:
            self.dev.set_pixel(0,
                               int(c1.red * 255),
                               int(c1.green * 255),
                               int(c1.blue * 255))
        else:
            self.dev.set_pixel(0,
                               int(0),
                               int(0),
                               int(0))
        if c2:
            self.dev.set_pixel(1,
                               int(c2.red * 255),
                               int(c2.green * 255),
                               int(c2.blue * 255))
        else:
            self.dev.set_pixel(1,
                               int(0),
                               int(0),
                               int(0))
        if c3:
            self.dev.set_pixel(2,
                               int(c3.red * 255),
                               int(c3.green * 255),
                               int(c3.blue * 255))
        else:
            self.dev.set_pixel(2,
                               int(0),
                               int(0),
                               int(0))
        self.dev.show()


if __name__ == '__main__':
    args = parser.parse_args()

    inf1_thresh = dict(name='last_conf1',
                       operator='greater_than',
                       value=args.conf1)
    inf2_thresh = dict(name='last_conf2',
                       operator='greater_than',
                       value=args.conf2)
    inf3_thresh = dict(name='last_conf3',
                       operator='greater_than',
                       value=args.conf3)

    not_inf1_thresh = dict(name='last_conf1',
                           operator='less_than',
                           value=args.conf1)
    not_inf2_thresh = dict(name='last_conf2',
                           operator='less_than',
                           value=args.conf2)
    not_inf3_thresh = dict(name='last_conf3',
                           operator='less_than',
                           value=args.conf3)

    paint_strip_0000 = dict(name='paint_strip',
                            params=dict(led_states=0))
    paint_strip_0001 = dict(name='paint_strip',
                            params=dict(led_states=1))
    paint_strip_0010 = dict(name='paint_strip',
                            params=dict(led_states=2))
    paint_strip_0011 = dict(name='paint_strip',
                            params=dict(led_states=3))
    paint_strip_0100 = dict(name='paint_strip',
                            params=dict(led_states=4))
    paint_strip_0101 = dict(name='paint_strip',
                            params=dict(led_states=5))
    paint_strip_0110 = dict(name='paint_strip',
                            params=dict(led_states=6))
    paint_strip_0111 = dict(name='paint_strip',
                            params=dict(led_states=7))

    rules = [
        {'conditions': {
            'all': [not_inf3_thresh, not_inf2_thresh, not_inf1_thresh]
        },
            'actions':[paint_strip_0000]
        },
        {'conditions': {
            'all': [not_inf3_thresh, not_inf2_thresh, inf1_thresh]
        },
            'actions':[paint_strip_0001]
        },
        {'conditions': {
            'all': [not_inf3_thresh, inf2_thresh, not_inf1_thresh]
        },
            'actions':[paint_strip_0010]
        },
        {'conditions': {
            'all': [not_inf3_thresh, inf2_thresh, inf1_thresh]
        },
            'actions':[paint_strip_0011]
        },
        {'conditions': {
            'all': [inf3_thresh, not_inf2_thresh, not_inf1_thresh]
        },
            'actions':[paint_strip_0100]
        },
        {'conditions': {
            'all': [inf3_thresh, not_inf2_thresh, inf1_thresh]
        },
            'actions':[paint_strip_0101]
        },
        {'conditions': {
            'all': [inf3_thresh, inf2_thresh, not_inf1_thresh]
        },
            'actions':[paint_strip_0110]
        },
        {'conditions': {
            'all': [inf3_thresh, inf2_thresh, inf1_thresh]
        },
            'actions':[paint_strip_0111]
        },
    ]

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    inf = LedInference()

    led_device = apa102.APA102(num_led=3)

    def _callback(ch, method, properties, body):
        try:
            d = json.loads(body)
            idx1 = np.argwhere(np.asarray(d['idxs']) == args.idx1)
            if idx1.shape[0] >= 1:
                inf.last_conf1 = d['inferences'][idx1[0, 0]]
            idx2 = np.argwhere(np.asarray(d['idxs']) == args.idx2)
            if idx2.shape[0] >= 1:
                inf.last_conf2 = d['inferences'][idx2[0, 0]]
            idx3 = np.argwhere(np.asarray(d['idxs']) == args.idx3)
            if idx3.shape[0] >= 1:
                inf.last_conf3 = d['inferences'][idx3[0, 0]]
            inf.time = d['time']

            run_all(rule_list=rules,
                    defined_variables=LedVars(
                        inf),
                    defined_actions=NotificationActs(
                        inf,
                        led_device=led_device,
                        c1=args.led_color1,
                        c2=args.led_color2,
                        c3=args.led_color3),
                    stop_on_first_trigger=False)

        except Exception as e:
            print ('exception ', e)
            raise e

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()
