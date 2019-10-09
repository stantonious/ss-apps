#!/usr/bin/python
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

api_key = os.environ.get('SS_API_KEY')


class NotificationActs(base.InferenceActs):

    def __init__(self, tracked_inference, led_device):
        super().__init__(tracked_inference)
        self.dev = led_device

    @actions.rule_action(params={'idx': fields.FIELD_NUMERIC,
                                 'color': fields.FIELD_TEXT})
    def paint_strip(self,
                    c1,
                    c2,
                    c3):
        from colour import Color
        c1 = Color(c1) or None
        c2 = Color(c2) or None
        c3 = Color(c3) or None

        if c1:
            self.dev.set_pixel(1,
                               int(c1.red * 255),
                               int(c1.green * 255),
                               int(c1.blue * 255))
        else:
            self.dev.set_pixel(idx,
                               int(0),
                               int(0),
                               int(0))
        if c2:
            self.dev.set_pixel(2,
                               int(c2.red * 255),
                               int(c2.green * 255),
                               int(c2.blue * 255))
        else:
            self.dev.set_pixel(idx,
                               int(0),
                               int(0),
                               int(0))
        if c3:
            self.dev.set_pixel(3,
                               int(c3.red * 255),
                               int(c3.green * 255),
                               int(c3.blue * 255))
        else:
            self.dev.set_pixel(idx,
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

    paint_strip = dict(name='paint_strip',
                       params=dict(c1=arg.led_color1,
                                   c2=arg.led_color2,
                                   c3=arg.led_color3))

    off_led = dict(name='change_led_color',
                   params=dict(idx=int(args.led_id),
                               color=None))

    rules = [
        {'conditions': {
            'any': [inf1_thresh, inf2_thresh, inf3_thresh, not_inf1_thresh, not_inf2_thresh, not_inf3_thresh]
        },
            'actions':[paint_strip]
        }
    ]

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    inf = base.Inference(idx=args.index)

    led_device = apa102.APA102(num_led=3)

    def _callback(ch, method, properties, body):
        try:
            d = json.loads(body)
            idx1 = np.argwhere(np.asarray(d['idxs']) == args.index)
            if idx1.shape[0] > 1:
                inf.last_conf1 = d['inferences'][idx1[0, 0]]
            idx2 = np.argwhere(np.asarray(d['idxs']) == args.index)
            if idx2.shape[0] > 1:
                inf.last_conf2 = d['inferences'][idx2[0, 0]]
            idx3 = np.argwhere(np.asarray(d['idxs']) == args.index)
            if idx3.shape[0] > 1:
                inf.last_conf3 = d['inferences'][idx3[0, 0]]
            inf.time = d['time']

            run_all(rule_list=rules,
                    defined_variables=base.InferenceVars(inf),
                    defined_actions=NotificationActs(
                        inf, led_device=led_device),
                    stop_on_first_trigger=False)

        except Exception as e:
            print ('exception ', e)

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()
