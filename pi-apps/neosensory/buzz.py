#!/home/pi/venvs/ss/bin/python3

import argparse
import sys
import pika
import numpy as np
import json
import logging
import time
from yamnet import yamnet as yamnet_model

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


parser = argparse.ArgumentParser(
    description='send notification for provided inference')

parser.add_argument('--conf-threshold', type=float, default=.8, required=False)
parser.add_argument('--idx',nargs='+', type=str, required=True)


def _get_vibration_pattern(num_steps,
                           step_len=None,
                           motor_multiplier=[1,1,1,1],
                           motor_offset=[0,0,0,0],
                           buzz_max_intensity=255,
                           buzz_min_intensity=0,
                           **kwargs):
    frames=[]
    steps = np.linspace(0,2*np.pi,num_steps) if not step_len else np.arange(0,num_steps*step_len,step_len)
    for _i in steps:

        #-1..1
        frames.append(np.asarray([np.sin(_i+motor_offset[0]),
                                  np.sin(_i+motor_offset[1]),
                                  np.sin(_i+motor_offset[2]),
                                  np.sin(_i+motor_offset[3])]))

    frames = np.asarray(frames)
    frames += 1 #Shift range to 0..2
    frames *= buzz_max_intensity/2 #because range is 0..2
    frames *= motor_multiplier

    #remove last dimension
    frames = frames.reshape(frames.shape[0] * frames.shape[1])
    return frames.astype(np.int32)


def _get_hz_frame_from_mel(
        mel,
        desired_hz=None,
        buzz_max_intensity=None,):
    buzz_max_intensity=buzz_max_intensity or 255
    desired_hz = desired_hz or 4

    # Remove fill frames
    mel = mel[np.std(mel,axis=-1) > 0]

    depth,remainder = divmod(mel.shape[0],desired_hz)
    to_buzz_intensity = buzz_max_intensity/64 # MEL has 64 bins in this case

    #TODO Not throw away signal
    mel = mel[remainder:,...].reshape(desired_hz,depth,-1)

    max_idxs=np.argmax(np.max(mel,axis=-1),axis=-1) #max std for 64 bins within hz block

    max_mel_bins = []
    for _i,_n in enumerate(max_idxs):
        max_mel_bins.append(np.argmax(mel[_i,_n,...]))

    #Scale to buzz intensity range
    max_mel_bins = np.asarray(max_mel_bins,dtype=np.float32)
    max_mel_bins *= to_buzz_intensity

   # print ('buzz scaled frames',max_mel_bins)

    # Add filler
    max_mel_bins = max_mel_bins.reshape(-1,1) #add last dimension

    # Add motor dimension
    max_mel_bins = np.tile(max_mel_bins,(1,4))

    #fill_frames = 62//desired_hz
   # max_mel_bins = np.tile(max_mel_bins,(1,fill_frames))

    return max_mel_bins.reshape(-1).astype(np.int) #remove final dimension

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

    idxs = []

    print ('args',args)
    print ('args idx',args.idx)

    for _i in args.idx:
        try:
            idxs.append(int(_i))
        except:
            idxs.append(np.where(class_mapping == _i)[0])

    running_avg = 0.

    def _callback(ch, method, properties, body):
        confidence = [None] * len(args.idx)
        global buzz_channel
        global running_avg #poor man's convolution
        try:
            d = json.loads(body)
            print ('d',d.keys())
            for _i, _idx in enumerate(idxs):
                idx = np.argwhere(np.asarray(d['idxs']) == _idx)
                if idx.shape[0] >= 1:
                    confidence[_i] = d['inferences'][idx[0, 0]]

            if confidence[0] > args.conf_threshold:
                logger.info('Idx:%s found with confidence: %s > %s...Buzzing!',_idx,confidence[0],args.conf_threshold)
                running_avg = 1.0
            else:
                running_avg -= .2

            
            if running_avg >0:
                mel = np.asarray(d['mel'])
                motor_amp_frames = _get_vibration_pattern(
                    num_steps=4*10, 
                    step_len=.2,
                    buzz_max_intensity=155,
                    motor_multiplier=[1,1,1,1],
                    motor_offset=[0,.2,.4,.6]
                    )
                #motor_amp_frames = _get_7hz_frame_from_mel(mel)
                desired_hz=4
                frames_per_send=10
                #motor_amp_frames = _get_hz_frame_from_mel(
                #        mel,
                #        desired_hz=desired_hz)

                #logger.info('sending 7hz frame:%s',motor_amp_frames.shape)
                print ('publishing')
                buzz_channel.basic_publish(exchange='buzz',
                                           routing_key='',
                                           body=json.dumps(dict(time=time.time(),
                                                                hz=desired_hz,
                                                                fps=frames_per_send,
                                                                pattern=motor_amp_frames.tolist(),)))
            else:
                #Send off frames
                buzz_channel.basic_publish(exchange='buzz',
                                           routing_key='',
                                           body=json.dumps(dict(time=time.time(),
                                                                hz=1,
                                                                fps=1,
                                                                pattern=[0,0,0,0])))

        except Exception as e:
            logger.exception('doh')
            raise e


    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    logger.info('Consuming!')
    channel.start_consuming()


