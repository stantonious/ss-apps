#!/usr/bin/python
'''
Created on Aug 28, 2019

@author: bstaley
'''
import argparse
import time
import json
import sys
import os
import pika
from app_utils import base
import numpy as np
from business_rules import variables, actions, run_all, fields

parser = argparse.ArgumentParser(
    description='send notification for provided inference')

parser.add_argument('-s', '--sleep-action-duration', type=int, required=True)
parser.add_argument('-e', '--event-window', type=int, required=True)
parser.add_argument('-t', '--event-num-threshold', type=int, required=True)
parser.add_argument('-c', '--confidence-threshold', type=float, required=True)
parser.add_argument('-i', '--index', type=int, required=True)

api_key = os.environ.get('SS_API_KEY')


class NotificationActs(base.InferenceActs):

    def __init__(self, tracked_inference):
        super().__init__(tracked_inference)

    @actions.rule_action(params={'size': fields.FIELD_NUMERIC})
    def record_audio(self, size):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_bind(queue='dump_commands', exchange='soundscene')

        d = dict(command='client',
                 size=size)
        channel.basic_publish(exchange='soundscene',
                              routing_key='dump_commands',
                              body=json.dumps(d))

    @actions.rule_action(params={'api_key': fields.FIELD_TEXT,
                                 'class_idx': fields.FIELD_NUMERIC})
    def ss_notify(self,
                  api_key,
                  class_idx):
        import requests

        url = 'http://trainer.soundscene.org:8081/soundscene/v.1.0/notification/sms'
        params = dict(api_key=api_key,
                      classification_id=class_idx)
        print ('sending sms')

        r = requests.get(url=url,
                         params=params)

        print ('ss response', r.json())


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

    record_audio = dict(name='record_audio',
                        params=dict(size=20))

    notify = dict(name='ss_notify',
                  params=dict(api_key=api_key,
                              class_idx=args.index))
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
            'actions':[record_audio, notify, reset_act_win, base.reset_cnt]
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

    inf = base.Inference(idx=args.index)

    def _callback(ch, method, properties, body):
        try:
            d = json.loads(body)
            idx = np.argwhere(np.asarray(d['idxs']) == args.index)
            if idx.shape[0] < 1:
                print ('no receiving inference for class idx', args.index)
                sys.exit()

            conf = d['inferences'][idx[0, 0]]

            inf.last_conf = conf

            run_all(rule_list=rules,
                    defined_variables=base.InferenceVars(inf),
                    defined_actions=NotificationActs(inf),
                    stop_on_first_trigger=False)

        except Exception as e:
            print ('exception ', e)

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()
