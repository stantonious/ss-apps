#!/usr/bin/python
""" Inference backoff app """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import argparse
import time
import json
import sys
import pika
import numpy as np
from app_utils import base
from business_rules import variables, actions, run_all, fields

parser = argparse.ArgumentParser(
    description='stop embedding processing for provided inference')

parser.add_argument('-n', '--notification-window', type=int, required=True)
parser.add_argument('-e', '--event-window', type=int, required=True)
parser.add_argument('-t', '--event-num-threshold', type=int, required=True)
parser.add_argument('-c', '--confidence-threshold', type=float, required=True)
parser.add_argument('-p', '--pause-duration', type=int, required=True)


class BackoffActs(base.InferenceActs):

    def __init__(self, tracked_inference):
        super().__init__(tracked_inference)

    @actions.rule_action(params={"seconds": fields.FIELD_NUMERIC})
    def pause_audio(self, seconds):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_bind(queue='audio_control', exchange='soundscene')

        print ('pausing audio')
        d = dict(command='resume_at',
                 value=time.time() + seconds)  # 100 secs
        channel.basic_publish(exchange='soundscene',
                              routing_key='audio_control',
                              body=json.dumps(d))


if __name__ == '__main__':
    args = parser.parse_args()

    silence_idx = dict(name='idx',
                       operator='equal_to',
                       value=500)
    cnt_exceeded = dict(name='cnt',
                        operator='greater_than',
                        value=args.event_num_threshold)
    inf_thresh = dict(name='last_conf',
                      operator='greater_than',
                      value=args.confidence_threshold)
    pause_audio = dict(name='pause_audio',
                       params=dict(seconds=args.pause_duration))
    reset_act_win = dict(name='reset_act_window',
                         params=dict(duration=args.notification_window))
    reset_win = dict(name='reset_window',
                     params=dict(duration=args.event_window))
    rules = [
        {'conditions': {
            'all': [inf_thresh]
        },
            'actions':[base.inc_cnt]
        },
        {'conditions': {
            'all': [silence_idx, cnt_exceeded, base.act_win]
        },
            'actions':[pause_audio, reset_act_win, base.reset_cnt]
        },
        {'conditions': {
            'all': [base.window_elapsed]
        },
            'actions':[reset_win, base.reset_cnt]
        }
    ]

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    inf = base.Inference(idx=500)

    def _callback(ch, method, properties, body):
        try:
            d = json.loads(body)
            idx = np.argwhere(np.asarray(d['idxs']) == 500)
            if idx.shape[0] < 1:
                print ('no receiving inference for class idx', 500)
                sys.exit()

            conf = d['inferences'][idx[0, 0]]

            inf.last_conf = conf

            run_all(rule_list=rules,
                    defined_variables=base.InferenceVars(inf),
                    defined_actions=BackoffActs(inf),
                    stop_on_first_trigger=False)

        except Exception as e:
            print ('exception ', e)

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()
