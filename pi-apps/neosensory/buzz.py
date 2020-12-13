#!/home/pi/venvs/ss/bin/python3

import asyncio
import argparse
import sys
import pika
import numpy as np
import json
import logging
from bleak import BleakClient
from bleak import discover
from neosensory_python import NeoDevice
from yamnet import yamnet as yamnet_model
import threading

logger = logging.getLogger()

class_mapping = yamnet_model.class_names('/opt/soundscene/yamnet_class_map.csv')

parser = argparse.ArgumentParser(
    description='send notification for provided inference')

parser.add_argument('--connection-attempts', type=int, required=True)
parser.add_argument('--buzz-addr', type=str, default='DB:9F:31:D3:29:53', required=False)
parser.add_argument('--idx',nargs='+', type=str, required=True)


def notification_handler(sender, data):
    print("{0}: {1}".format(sender, data))


def _discover_neo(disc_time):
    logger.info('discovering buzz %s seconds',disc_time)
    devices = discover(disc_time)
    buzz_addr = None
    for d in devices:
        if str(d).find("Buzz") > 0:
            print("Found a Buzz! " + str(d) +
                  "\r\nAddress substring: " + str(d)[:17])
            # set the address to a found Buzz
            buzz_addr = str(d)[:17]
            break
    return buzz_addr

def buzz(connection_attempts,vibration_pattern,buzz_addr=None):
    async def run(loop,connection_attempts,vibration_pattern,buzz_addr=None):

        #TODO - discover neo
        buzz_addr=buzz_addr or _discover_neo(10)

        client = BleakClient(buzz_addr, loop=loop)

        my_buzz = NeoDevice(client)

        x = await client.is_connected()

        logger.info('connected:%s',x)

        while x == False and connection_attempts > 0:
            try:
                await client.connect()
                await asyncio.sleep(3)
                logger.info('attempts left %s',connection_attempts)
                x = await client.is_connected()
            except Exception:
                logger.exception('Connection failed')

        if connection_attempts <= 0:
            logger.wanring('giving up..')
            return

        logger.info("Connection State: {0}\r\n".format(x))

        await my_buzz.enable_notifications(notification_handler)

        await asyncio.sleep(1)

        await my_buzz.request_developer_authorization()

        await my_buzz.accept_developer_api_terms()

        await my_buzz.pause_device_algorithm()

        try:
            logger.info('sending pattern')
            await my_buzz.vibrate_motors(vibration_pattern)
        except:
            logger.error('Unable to vibrate motors')

    loop = asyncio.new_event_loop()
    loop.run_until_complete(run(loop,connection_attempts,vibration_pattern,buzz_addr))


def _get_vibration_pattern(inf_sliding_window_avg):
    return [200,200,2,2]

if __name__ == "__main__":

    args = parser.parse_args()

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    idxs = []

    buzz_thread = None

    for _i in args.idx:
        try:
            idxs.append(int(_i))
        except:
            idxs.append(np.where(class_mapping == _i)[0])

    def _callback(ch, method, properties, body):
        confidence = [None] * len(args.idx)
        global buzz_thread
        try:
            d = json.loads(body)
            for _i, _idx in enumerate(idxs):
                idx = np.argwhere(np.asarray(d['idxs']) == _idx)
                if idx.shape[0] >= 1:
                    confidence[_i] = d['inferences'][idx[0, 0]]

            if len(confidence) and confidence[0] > .05:
                print ('buzzing')
                if buzz_thread:
                    if buzz_thread.is_alive():
                        logger.warning('A buzz threads is already running!!')
                        return
                print ('starting buzz thread')
                buzz_thread = threading.Thread(target=buzz,args=(args.connection_attempts,
                                                                 _get_vibration_pattern(None),
                                                                 args.buzz_addr))
                buzz_thread.start()

        except Exception as e:
            print('exception ', e)
            raise e


    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print('Consuming!')
    channel.start_consuming()


