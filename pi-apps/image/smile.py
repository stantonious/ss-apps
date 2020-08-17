#!/home/pi/venvs/ss/bin/python3
""" Seeed mic LED app """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 202"
__credits__ = []
__license__ = "GPL"

import argparse
import time
import picamera
import multiprocessing
from threading import Thread
import json
import sys
import os
import pika
import numpy as np
from yamnet import yamnet as yamnet_model

class_mapping = yamnet_model.class_names('/opt/soundscene/yamnet_class_map.csv')

parser = argparse.ArgumentParser(
    description='snap pic')

img_rcv, img_snd = multiprocessing.Pipe(False)

parser.add_argument('--conf', type=float, required=True)
parser.add_argument('--idx', type=str, required=True)
parser.add_argument('--dump-dir', type=str, required=True)
parser.add_argument('--xres', type=int, default=128, )
parser.add_argument('--yres', type=int, default=128, )


def snap_pics(img_rcv,
              dump_dir,
              for_idx,
              xres=128,
              yres=128,
              warmup_time=2,
              keep_warm=10):
    camera = None
    on_since = 0

    running = True

    while running:
        if img_rcv.poll(2):
            if not camera:
                camera = picamera.PiCamera()
                camera.resolution = (xres, yres)
                camera.start_preview()
                time.sleep(warmup_time)
                on_since = time.time()

            when = img_rcv.recv()
            camera.capture(f'{dump_dir}/{for_idx}-{when}.jpg')

        else:
            if camera and time.time() > on_since + keep_warm:
                camera = None


if __name__ == '__main__':
    args = parser.parse_args()

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    img_thread = Thread(target=snap_pics, args=(img_rcv,
                                                args.dump_dir,
                                                args.xres,
                                                args.yres,))

    img_thread.start()

    idxs = []

    for _i in args.idx:
        try:
            idxs.append(int(_i))
        except:
            idxs.append(np.where(class_mapping == _i)[0])


    def _callback(ch, method, properties, body):
        try:
            d = json.loads(body)
            for _i, _idx in enumerate(idxs):
                idx = np.argwhere(np.asarray(d['idxs']) == _idx)
                if idx.shape[0] >= 1:
                    if d['inferences'][idx[0, 0]] >= args.conf:
                        img_snd.send(time.time())


        except Exception as e:
            print('exception ', e)
            raise e


    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print('Consuming!')
    channel.start_consuming()
