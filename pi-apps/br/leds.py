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

parser.add_argument('-s', '--sleep-action-duration', type=int, required=True)
parser.add_argument('-e', '--event-window', type=int, required=True)
parser.add_argument('-t', '--event-num-threshold', type=int, required=True)
parser.add_argument('-c', '--confidence-threshold', type=float, required=True)
parser.add_argument('-i', '--index', type=int, required=True)
parser.add_argument('-l', '--led-id', type=str, required=True)
parser.add_argument('-C', '--led-color', type=str, required=True)

api_key = os.environ.get('SS_API_KEY')


class NotificationActs(base.InferenceActs):

    def __init__(self, tracked_inference, led_device):
        super().__init__(tracked_inference)
        self.dev = led_device

    @actions.rule_action(params={'idx': fields.FIELD_NUMERIC,
                                 'color': fields.FIELD_TEXT})
    def change_led_color(self,
                         idx,
                         color):
        from colour import Color
        if color:
            c = Color(color)

            self.dev.set_pixel(idx,
                               int(c.red * 255),
                               int(c.green * 255),
                               int(c.blue * 255))
        else:
            self.dev.set_pixel(idx,
                               int(0),
                               int(0),
                               int(0))
        self.dev.show()


if __name__ == '__main__':
    args = parser.parse_args()

    tracked_idx = dict(name='idx',
                       operator='equal_to',
                       value=args.index)
    cnt_exceeded = dict(name='cnt',
                        operator='greater_than',
                        value=args.event_num_threshold)
    inf_thresh = dict(name='last_conf',
                      operator='greater_than',
                      value=args.confidence_threshold)

    change_led = dict(name='change_led_color',
                      params=dict(idx=int(args.led_id),
                                  color=args.led_color))

    off_led = dict(name='change_led_color',
                   params=dict(idx=int(args.led_id),
                               color=None))

    reset_act_win = dict(name='reset_act_window',
                         params=dict(duration=args.sleep_action_duration))
    reset_win = dict(name='reset_window',
                     params=dict(duration=args.event_window))

    rules = [
        {'conditions': {
            'all': [inf_thresh]
        },
            'actions':[base.inc_cnt]
        },
        {'conditions': {
            'all': [tracked_idx, cnt_exceeded, base.act_win]
        },
            'actions':[change_led, reset_act_win, base.reset_cnt]
        },
        {'conditions': {
            'all': [base.window_elapsed]
        },
            'actions':[reset_win, base.reset_cnt, off_led]
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
            idx = np.argwhere(np.asarray(d['idxs']) == args.index)
            if idx.shape[0] < 1:
                print ('no receiving inference for class idx', args.index)
                sys.exit()

            conf = d['inferences'][idx[0, 0]]

            inf.last_conf = conf
            inf.embeddings = np.asarray(d['embeddings'], dtype=np.uint8)
            inf.time = d['time']

            run_all(rule_list=rules,
                    defined_variables=base.InferenceVars(inf, 3),
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
