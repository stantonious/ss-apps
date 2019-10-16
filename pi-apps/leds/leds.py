#!/home/pi/venvs/ss/bin/python3
""" Seeed mic LED app """
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
from gpiozero import LED

parser = argparse.ArgumentParser(
    description='send notification for provided inference')

parser.add_argument('--num-leds', type=int, required=True)
parser.add_argument('--conf',nargs='+', type=float, required=True)
parser.add_argument('--idx',nargs='+', type=int, required=True)
parser.add_argument('--color',nargs='+', type=str, required=True)

led_power=LED(5)
led_power.on()

class LedInference(object):
    

    def _init_(self,num_leds):
        self.confs=[0.0] * num_leds
        self.thresh=[0.0] * num_leds


class LedControl():

    def __init__(self,
                 colors, 
                 led_device,
                 num_leds):
        super().__init__(tracked_inference)
        self.colors = [None] * num_leds
        
        for _i,_c in enumerate(colors):
            self.colors[_i] = colour.Color(_c) if _c is not None else None
        self.dev = led_device
        
        
    def paint_strip(self,
                    confidences,
                    thresholds):
        
        for _i,_s in enumerate(confidences):
            _c = self.colors[_i]
            _t = thresholds[_i]
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

    inf = LedInference(args.num_leds)

    led_device = apa102.APA102(num_led=args.num_leds)
    colors = [None] * args.num_leds
    thresholds = [None] * args.num_leds
    
    for _i,_c in enumerate(args.color):
        colors[_i] = _c
    for _i,_c in enumerate(args.conf):
        thresholds[_i] = _c
        

    led_control = LedControl(colors=colors,
                             led_device=led_device,
                             num_leds=args.num_leds)
    
    def _callback(ch, method, properties, body):
        confidence = [None] * args.num_leds
        try:
            d = json.loads(body)
            for _i,_idx in enumerate(args.idx):
                idx = np.argwhere(np.asarray(d['idxs']) == _idx)
                if idx.shape[0] >= 1:
                    confidence[_i] = d['inferences'][idx[0, 0]]
                    
            led_control.paint_strip(confidences=confidence, 
                                    thresholds=thresholds)
            

        except Exception as e:
            print ('exception ', e)
            raise e

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()
