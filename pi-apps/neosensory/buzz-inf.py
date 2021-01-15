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
parser.add_argument('--buzz-max-intensity', type=int, default=155)


def _get_motor_pattern(confs,
                       buzz_max_intensity):
    return (np.asarray(confs) * buzz_max_intensity).astype(np.int).tolist()

if __name__ == "__main__":

    args = parser.parse_args()

    buzz_connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    buzz_channel = buzz_connection.channel()
    buzz_channel.exchange_declare(exchange='buzz',
                                  exchange_type='fanout'
                                  )
    
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    logger.info('args:%s',args)
    logger.info('args idxs:%s',args.idxs)

    def _callback(ch, method, properties, body):
        global buzz_connection
        global buzz_channel
        try:
            d = json.loads(body)
            confs=[]
            for _i, _idx in enumerate(args.idxs):
                idx = np.argwhere(np.asarray(d['idxs']) == _idx)
                confs.append( d['inferences'][idx[0, 0]])

            
            pattern = _get_motor_pattern(confs, buzz_max_intensity=args.buzz_max_intensity)

            print ('sending',pattern,flush=True)
            #logger.info('sending 7hz frame:%s',motor_amp_frames.shape)
            buzz_channel.basic_publish(exchange='buzz',
                                       routing_key='',
                                       body=json.dumps(dict(time=time.time(),
                                                            hz=1,
                                                            fps=1,
                                                            pattern=pattern,)))

        except pika.exceptions.AMQPError as sle:
            logger.exception('Reconnecting')
            buzz_connection = pika.BlockingConnection(
                pika.ConnectionParameters('localhost'))
            buzz_channel = buzz_connection.channel()
            buzz_channel.exchange_declare(exchange='buzz',
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


