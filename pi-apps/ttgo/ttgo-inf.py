#!/home/pi/venvs/ss/bin/python3

import argparse
import sys
import pika
import numpy as np
import json
import logging
import time
from enum import Enum
from yamnet import yamnet as yamnet_model


logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class_mapping = yamnet_model.class_names('/opt/soundscene/yamnet_class_map.csv')

parser = argparse.ArgumentParser(
    description='send notification for provided inference')

parser.add_argument('--idxs',nargs='+', type=int, required=True)
parser.add_argument('--conf-threshold', type=float, default=.8, required=False)


if __name__ == "__main__":

    args = parser.parse_args()

    ttgo_connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    ttgo_channel = ttgo_connection.channel()
    ttgo_channel.exchange_declare(exchange='ttgo',
                                  exchange_type='fanout'
                                  )
    
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    idxs = []

    logger.info('args:%s',args)
    logger.info('args idxs:%s',args.idxs)

    for _i in args.idx:
        try:
            idxs.append(int(_i))
        except:
            idxs.append(np.where(class_mapping == _i)[0])

    running_avg = 0.

    def _callback(ch, method, properties, body):
        confidence = [None] * len(args.idx)
        global ttgo_connection
        global ttgo_channel
        global running_avg #poor man's convolution

        try:
            d = json.loads(body)
            for _i, _idx in enumerate(idxs):
                idx = np.argwhere(np.asarray(d['idxs']) == _idx)
                if idx.shape[0] >= 1:
                    confidence[_i] = d['inferences'][idx[0,0]]

            if confidence[0] > args.conf_threshold:
                logger.info('Idx:%s found with confidence: %s > %s...Buzzing!',_idx,confidence[0],args.conf_threshold)
                running_avg = 1.0
            else:
                running_avg -= .1

            
            mel = np.asarray(d['mel'])
            if running_avg >0:

                logger.info('sending buzz frame')
                ttgo_channel.basic_publish(exchange='ttgo',
                                           routing_key='',
                                           body=json.dumps(dict(time=time.time(),
                                                                hz=0,
                                                                fps=0,
                                                                pattern=[])))
        except pika.exceptions.AMQPError as sle:
            logger.exception('Reconnecting')
            ttgo_connection = pika.BlockingConnection(
                pika.ConnectionParameters('localhost'))
            ttgo_channel = ttgo_connection.channel()
            ttgo_channel.exchange_declare(exchange='ttgo',
                                          exchange_type='fanout'
                                          )
        except Exception as e:
            logger.exception('doh')
            raise e
    
    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    logger.info('Consuming!')
    channel.start_consuming()


