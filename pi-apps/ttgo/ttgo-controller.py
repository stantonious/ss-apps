#!/home/pi/venvs/ss/bin/python3

import asyncio
import argparse
import sys
import pika
import json
import signal
import logging
from bleak import BleakClient,discover
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
    description='Handle communication with the lilygo ttwatch')

parser.add_argument('--connection-attempts', type=int, default=2,required=False)
parser.add_argument('--ttgo-addr', type=str, default='3C:61:05:0D:7A:8E', required=False)
parser.add_argument('--tt_rx_uuid', type=str, default='6e400002-b5a3-f393-e0a9-e50e24dcca9e', required=False)

def notification_handler(sender, data):
    logger.info("{0}: {1}".format(sender, data))

def buzz_along(connection_attempts,frm_rcv,ttgo_addr,tt_rx_uuid):
    # 0x10 - Data start
    # GB - Part of gadgetbridge protocol
    # 0x20 - Space
    # 0x0a - Part of gadgetbridge protocol
    # 0x03 - Part of gadgetbridge protocol

    ttgo_buzz_msg = bytearray('GB {"vib":"on"}'.encode())
    ttgo_buzz_msg =bytearray([0x10]) + ttgo_buzz_msg + bytearray([0x20,0x0a,0x03])
    print (ttgo_buzz_msg)

    async def run(loop,connection_attempts,frm_rcv,ttgo_addr,tt_rx_uuid):
        logger.info('staring ttgo controller run loop')

        try:
            client = BleakClient(ttgo_addr, loop=loop)
    
            await asyncio.sleep(1)
    
            connectionResult = await client.is_connected()
    
            logger.info('connected:%s',connectionResult)
    
            while connectionResult == False and connection_attempts > 0:
                try:
                    await client.connect()
                    await asyncio.sleep(1)
                    logger.info('attempts left %s',connection_attempts)
                    connectionResult = await client.is_connected()
                    connection_attempts-=1
                except Exception:
                    logger.exception('Connection failed')
    
            if connection_attempts <= 0:
                logger.warning('giving up..')
                return
    
            logger.info("Connection State: {0}\r\n".format(connectionResult))
    
            logger.info('starting recv loop')

            #drain
            while frm_rcv.poll():
                _ = frm_rcv.recv()

            while True:
                hz, frames_per_send,frames = frm_rcv.recv()
                await client.write_gatt_char(tt_rx_uuid,ttgo_buzz_msg)


        except Exception as e:
            logger.exception('ttgo processing loop failed')

            # Attempt disconnect
            try:
                logger.info('disconnecting')
                await client.disconnect()
            except:
                pass
            return

    loop = asyncio.new_event_loop()
    loop.run_until_complete(run(loop,connection_attempts,frm_rcv,ttgo_addr,tt_rx_uuid))



if __name__ == "__main__":

    args = parser.parse_args()

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='ttgo',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='ttgo')

    ttgo_thread = threading.Thread(target=buzz_along,args=(args.connection_attempts,
                                                           frm_rcv,
                                                           args.ttgo_addr,
                                                           args.tt_rx_uuid))
    ttgo_thread.setDaemon(True)
    ttgo_thread.start()

    running_avg = 0.

    def _handle_kill(_signo,_stackframe):
        global ttgo_thread
        frm_snd.send(None)
        ttgo_thread.join()
        logger.info('killed ttgo thread')
        channel.stop_consuming()

    signal.signal(signal.SIGTERM, _handle_kill)

    def _callback(ch, method, properties, body):
        global ttgo_thread
        try:

            if ttgo_thread.is_alive() == False:
                logger.warning('TTGO thread died...restarting')
                ttgo_thread = threading.Thread(target=buzz_along, args=(args.connection_attempts,
                                                                        frm_rcv,
                                                                        args.ttgo_addr,
                                                                        args.tt_rx_uuid))
                ttgo_thread.start()

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


