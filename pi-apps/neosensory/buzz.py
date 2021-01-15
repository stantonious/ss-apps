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


class Pattern(Enum):
    sinusoidal='sinusoidal'
    mel='mel'
    alert='alert'
    melspan='melspan'
    default='default'

    def __str__(self):
        return self.value

class_mapping = yamnet_model.class_names('/opt/soundscene/yamnet_class_map.csv')

parser = argparse.ArgumentParser(
    description='send notification for provided inference')

parser.add_argument('--conf-threshold', type=float, default=.8, required=False)
parser.add_argument('--idx',nargs='+', type=str, required=True)
parser.add_argument('--pattern', type=Pattern, choices=list(Pattern),default=Pattern.sinusoidal)
parser.add_argument('--hz', type=int, default=4)
parser.add_argument('--fps', type=int, default=10)
parser.add_argument('--buzz-max-intensity', type=int, default=155)


def _get_sinusoidal_pattern(num_steps,
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


def _get_alert_pattern(
        desired_hz=None,
        motor_multiplier=[1, 1, 1, 1],
        buzz_max_intensity=None, ):

    frames = np.full((desired_hz,4),0)

    for _n in range(frames.shape[0]):
        frames[_n]=np.asarray(motor_multiplier)*buzz_max_intensity*(_n%2)
    frames = frames.reshape(frames.shape[0] * frames.shape[1])
    return frames



def _get_mel_pattern(
        mel,
        fps=None,
        desired_hz=None,
        buzz_max_intensity=None,):
    buzz_max_intensity=buzz_max_intensity or 255
    desired_hz = desired_hz or 4
    fps = fps or 1

    # Remove fill frames
    mel = mel[np.std(mel,axis=-1) > 0]

    total_frames = desired_hz * fps
    depth,remainder = divmod(mel.shape[0],total_frames)
    to_buzz_intensity = buzz_max_intensity/64 # MEL has 64 bins in this case

    #TODO Not throw away signal
    mel = mel[remainder:,...].reshape(total_frames,depth,-1) #reshape to (time steps,samples,mel bins)

    max_idxs=np.argmax(np.max(mel,axis=-1),axis=-1) #max std for 64 bins within hz block

    max_mel_bins = []
    for _i,_n in enumerate(max_idxs):
        max_mel_bins.append(np.argmax(mel[_i,_n,...]))

    #Scale to buzz intensity range
    max_mel_bins = np.asarray(max_mel_bins,dtype=np.float32)
    max_mel_bins *= to_buzz_intensity

    # Add filler
    max_mel_bins = max_mel_bins.reshape(-1,1) #add last dimension

    # Add motor dimension
    max_mel_bins = np.tile(max_mel_bins,(1,4))

    #fill_frames = 62//desired_hz
   # max_mel_bins = np.tile(max_mel_bins,(1,fill_frames))

    return max_mel_bins.reshape(-1).astype(np.int) #remove final dimension

def _get_mel_span_pattern(
        mel,
        fps=None,
        desired_hz=None,
        buzz_max_intensity=None,):
    buzz_max_intensity=buzz_max_intensity or 255
    desired_hz = desired_hz or 4
    fps = fps or 1

    # Remove fill frames
    mel = mel[np.std(mel,axis=-1) > 0]

    total_frames = desired_hz * fps
    depth,remainder = divmod(mel.shape[0],total_frames)
    to_buzz_intensity = buzz_max_intensity/16 # MEL has 64 bins spread across 4 

    #TODO Not throw away signal
    mel = mel[remainder:,...].reshape(total_frames,depth,-1) #reshape to (time steps,samples,mel bins)

    max_idxs=np.argmax(np.max(mel,axis=-1),axis=-1) #max std for 64 bins within hz block

    max_mel_bins = []
    for _i,_n in enumerate(max_idxs):
        max_mel_bins.append(np.argmax(mel[_i,_n,...]))

    #Scale to buzz intensity range
    def _get_buzz_intensities_per_motor(bins):
        int_per_step=[]
        for _n in bins:
            motor,intensity=divmod(_n,16)
            int_per_step.append([
                intensity if motor == 0 else 0,
                intensity if motor == 1 else 0,
                intensity if motor == 2 else 0,
                intensity if motor == 3 else 0,
                ])
        return np.asarray(int_per_step,dtype=np.float32)

    #max_mel_bins = np.asarray(max_mel_bins,dtype=np.float32)
    max_mel_bins = _get_buzz_intensities_per_motor(max_mel_bins)
    max_mel_bins *= to_buzz_intensity

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

    logger.info('args:%s',args)
    logger.info('args idx:%s',args.idx)

    for _i in args.idx:
        try:
            idxs.append(int(_i))
        except:
            idxs.append(np.where(class_mapping == _i)[0])

    running_avg = 0.
    off_frame_sent = False

    def _callback(ch, method, properties, body):
        confidence = [None] * len(args.idx)
        global buzz_connection
        global buzz_channel
        global running_avg #poor man's convolution
        global off_frame_sent
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

                if args.pattern == Pattern.sinusoidal:
                    motor_amp_frames = _get_sinusoidal_pattern(
                        num_steps=args.fps * args.hz,
                        step_len=.2,
                        buzz_max_intensity=args.buzz_max_intensity,
                        motor_multiplier=[1,1,1,1],
                        motor_offset=[0,.2,.4,.6],
                        ).tolist()
                elif args.pattern == Pattern.mel:
                    motor_amp_frames = _get_mel_pattern(
                        mel,
                        desired_hz=args.hz,
                        fps=args.fps,
                        buzz_max_intensity=args.buzz_max_intensity).tolist()
                elif args.pattern == Pattern.alert:
                    motor_amp_frames = _get_alert_pattern(
                        desired_hz=args.hz,
                        motor_multiplier=[0,1,0,.5],
                        buzz_max_intensity=args.buzz_max_intensity).tolist()
                elif args.pattern == Pattern.melspan:
                    motor_amp_frames = _get_mel_span_pattern(
                        mel,
                        desired_hz=args.hz,
                        fps=args.fps,
                        buzz_max_intensity = args.buzz_max_intensity).tolist()
                if args.pattern == Pattern.default:
                    motor_amp_frames=[None]

                #logger.info('sending 7hz frame:%s',motor_amp_frames.shape)
                buzz_channel.basic_publish(exchange='buzz',
                                           routing_key='',
                                           body=json.dumps(dict(time=time.time(),
                                                                hz=args.hz,
                                                                fps=args.fps,
                                                                pattern=motor_amp_frames,)))
                off_frame_sent = False
            elif off_frame_sent == False:
                #Send off frames
                print ('offing ',flush=True)
                buzz_channel.basic_publish(exchange='buzz',
                                           routing_key='',
                                           body=json.dumps(dict(time=time.time(),
                                                                hz=1,
                                                                fps=1,
                                                                pattern=[0,0,0,0])))
                off_frame_sent = True

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


