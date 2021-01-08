#!/home/pi/venvs/ss/bin/python3

import asyncio
import argparse
import sys
import pika
import json
import signal
import logging
from bleak import BleakClient
from bleak import discover
from neosensory_python import NeoDevice
import threading
import multiprocessing

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


frm_rcv, frm_snd = multiprocessing.Pipe(False)

parser = argparse.ArgumentParser(
    description='Handle communication with the buzz')

parser.add_argument('--connection-attempts', type=int, default=2,required=False)
parser.add_argument('--buzz-addr', type=str, default='DB:9F:31:D3:29:53', required=False)

def notification_handler(sender, data):
    logger.info("{0}: {1}".format(sender, data))

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

def buzz_along(connection_attempts,frm_rcv,buzz_addr=None):
    async def run(loop,connection_attempts,frm_rcv,buzz_addr=None):
        logger.info('staring buzz run loop')

        #TODO - discover neo
        buzz_addr=buzz_addr or _discover_neo(10)

        client = BleakClient(buzz_addr, loop=loop)

        my_buzz = NeoDevice(client)

        connectionResult = await client.is_connected()

        logger.info('connected:%s',connectionResult)

        while connectionResult == False and connection_attempts > 0:
            try:
                await client.connect()
                await asyncio.sleep(1)
                logger.info('attempts left %s',connection_attempts)
                x = await client.is_connected()
                connection_attempts-=1
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


        logger.info('starting recv loop')
        num_motors=4
        running_default = False
        #drain
        while frm_rcv.poll():
            _ = frm_rcv.recv()
        while True:
            try:
                hz, frames_per_send,frames = frm_rcv.recv()
            except Exception as e:
                logger.exception('Unable to drain pipe')
                break
            if None in frames:
                if not running_default:
                    logger.info('Starting default algo')
                    await my_buzz.resume_device_algorithm()
                    running_default = True
                continue
            else:
                if running_default:
                    logger.info('Pausing default algo')
                    await my_buzz.pause_device_algorithm()
                    running_default = False
            try:
                hz_sleep_time=1.0/hz
                step_size = num_motors * frames_per_send
                for _i in range(0,len(frames),step_size):
                    frames_to_send=frames[_i:_i+step_size]
                    logger.info('sending:%s',frames_to_send)
                    await my_buzz.vibrate_motors(frames_to_send)
                    await asyncio.sleep(hz_sleep_time-.1) #- for transmission time

            except:
                logger.exception('Unable to vibrate motors')
                break
        await my_buzz.vibrate_motors([0,0,0,0])
        logger.info('disconnect')

        #Resume algo
        logger.info('resuming algo')
        await my_buzz.resume_device_algorithm()
        logger.info('disconnecting')
        await client.disconnect()
        logger.info('disconnect')

    loop = asyncio.new_event_loop()
    loop.run_until_complete(run(loop,connection_attempts,frm_rcv,buzz_addr))



if __name__ == "__main__":

    args = parser.parse_args()

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='buzz',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='buzz')

    buzz_thread = threading.Thread(target=buzz_along,args=(args.connection_attempts,
                                                           frm_rcv,
                                                           args.buzz_addr))
    buzz_thread.setDaemon(True)
    buzz_thread.start()

    running_avg = 0.

    def _handle_kill(_signo,_stackframe):
        global buzz_thread
        frm_snd.send(None)
        buzz_thread.join()
        logger.info('killed buzz thread')
        channel.stop_consuming()

    signal.signal(signal.SIGTERM, _handle_kill)

    def _callback(ch, method, properties, body):
        global buzz_thread
        try:

            if buzz_thread.is_alive() == False:
                logger.warning('Buzz thread died...restarting')
                buzz_thread = threading.Thread(target=buzz_along, args=(args.connection_attempts,
                                                                        frm_rcv,
                                                                        args.buzz_addr))
                buzz_thread.start()

            d = json.loads(body)
            desired_hz = d['hz']
            frames_per_send = d['fps']
            pattern = d['pattern']

            logger.info('Sending new pattern @ \n  hz: %s\n  fps: %d\n  %s',desired_hz,frames_per_send,pattern)

            frm_snd.send([
                desired_hz,
                frames_per_send,
                pattern])

        except Exception as e:
            logger.exception('doh')
            raise e


    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    logger.info('Consuming!')
    channel.start_consuming()


