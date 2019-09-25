'''
Created on Jan 4, 2019

@author: bstaley
'''
import numpy as np
import pyaudio
import sys
import time

from . import logger

#FORMAT = pyaudio.paInt16
FORMAT = pyaudio.paInt32

audio = pyaudio.PyAudio()


def record_audio(aud_snd,
                 rec_snd=None,
                 rate=16000,
                 chunk=1024,
                 input_idx=[1, 2],
                 channels=1,
                 record_secs=None,
                 reconnect_audio=True,
                 ):
    print ('channels', channels)
    time.sleep(5)  # provide some time for the other processors to init

    for _i in input_idx:
        logger.info('%s (%s) %s', _i, input_idx,
                    audio.get_device_info_by_index(_i)['name'])
    # start Recording
    stream = None

    for _i in input_idx:
        try:
            logger.info('trying idx:%s', _i)
            # if 'seeed' not in audio.get_device_info_by_index(_i)['name']:
            #    print 'skipping',audio.get_device_info_by_index(_i)['name']
            #    continue
            stream = audio.open(format=audio.get_format_from_width(2),
                                channels=channels,
                                rate=rate,
                                input=True,
                                input_device_index=_i,
                                frames_per_buffer=chunk)
            logger.info('connected to idx:%s', _i)
            break
        except Exception as e:
            time.sleep(1)  # time for audio card to init
            logger.info(e)
            logger.info('unable to connect to idx:%s', _i)

    if stream == None:
        return -1
    interations = int(
        rate / chunk * record_secs) if record_secs else sys.maxsize
    for _ in range(0, interations):
        sys.stdout.write('.')
        sys.stdout.flush()
        try:
            data = np.fromstring(stream.read(
                chunk, exception_on_overflow=True), np.int16)

            if channels > 1:
                data = data.reshape(-1, channels)
            aud_snd.send(data)

            if rec_snd:
                rec_snd.send(data)
        except Exception as e:
            print (e)
            stream.close()
            if reconnect_audio:
                for _i in input_idx:
                    print ('audio name',
                           audio.get_device_info_by_index(_i)['name'])
                    # if 'seeed' not in audio.get_device_info_by_index(_i)['name']:
                    #    print 'skipping',audio.get_device_info_by_index(_i)['name']
                    #    continue
                    try:
                        logger.info('trying idx:%s', _i)
                        stream = audio.open(format=audio.get_format_from_width(2),
                                            channels=channels,
                                            rate=rate,
                                            input=True,
                                            input_device_index=_i,
                                            frames_per_buffer=chunk)
                        logger.info('connected to idx:%s', _i)
                        break
                    except Exception as e:
                        time.sleep(1)  # time for audio card to init
                        logger.info(e)
                        logger.info('unable to connect to idx:%s', _i)
                continue
            else:
                raise e
    logger.info('time expired')
