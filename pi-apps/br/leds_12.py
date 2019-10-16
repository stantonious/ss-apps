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
from gpiozero import LED

parser = argparse.ArgumentParser(
    description='send notification for provided inference')

num_leds=12
parser.add_argument('--conf',nargs='+', type=float, required=True)
parser.add_argument('--idx',nargs='+', type=int, required=True)
parser.add_argument('--color',nargs='+', type=str, required=True)

led_power=LED(5)
led_power.on()

class LedInference(object):
    confs=[0.0] * num_leds
    thresh=[0.0] * num_leds

    def _init_(self):
        pass


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

    def __init__(self,
                 tracked_inference, 
                 colors, 
                 led_device):
        super().__init__(tracked_inference)
        self.colors = [None] * num_leds
        
        for _i,_c in enumerate(colors):
            self.colors[_i] = colour.Color(_c) if _c is not None else None
        self.dev = led_device
        
        self.paint_strip(led_states)
    def paint_strip(self):
        
        for _i,_s in self.tracked_inference.confs:
            _c = self.colors[_i]
            _t = self.tracked_inference.thresh[_i]
            if _s and _c is not None and _t is not None and _s > _t:
                self.dev.set_pixel(_i,
                                   int(_c.red * 255),
                                   int(_c.green * 255),
                                   int(_c.blue * 255))
            else:
                self.dev.set_pixel(_i,
                                   int(0),
                                   int(0),
                                   int(0))
        self.dev.show()


if __name__ == '__main__':
    args = parser.parse_args()

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    inf = LedInference()

    led_device = apa102.APA102(num_led=num_leds)
    colors = [None] * num_leds
    thresholds = [None] * num_leds
    
    for _i,_c in enumerate(args.colors):
        colors[_i] = _c
    for _i,_c in enumerate(args.conf):
        thresholds[_i] = _c
        

    def _callback(ch, method, properties, body):
        confidence = [None] * num_leds
        try:
            d = json.loads(body)
            for _i,_idx in enumerate(args.idx):
                idx = np.argwhere(np.asarray(d['idxs']) == _idx)
                if idx.shape[0] >= 1:
                    confidence[_i] = d['inferences'][idx[0, 0]]
            
            inf.time = d['time']
            inf.confs = confidence
            inf.thresh = thresholds

            run_all(rule_list=rules,
                    defined_variables=LedVars(
                        inf),
                    defined_actions=NotificationActs(
                        inf,
                        colors=colors,
                        led_device=led_device),
                    stop_on_first_trigger=False)

        except Exception as e:
            print ('exception ', e)
            raise e

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()
