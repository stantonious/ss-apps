#!/home/pi/venvs/ss/bin/python2
import numpy as np
import sys
import tensorflow as tf
import multiprocessing
import os
import json
import time
from threading import Thread
import pika
from inference import record_processor, embedding_processor, audio_processor, framing_processor


RATE = 16000
#RATE = 48000
CHUNK = 1024
IDX = [0, 1, 2]
CHANNELS = 4
#CHANNELS = 1
INF_TTL = 20 * 60 * 1000  # usecs
# RATE = 44100

aud_rcv, aud_snd = multiprocessing.Pipe(False)
rec_rcv, rec_snd = multiprocessing.Pipe(False)
frm_rcv, frm_snd = multiprocessing.Pipe(False)
cmd_rcv, cmd_snd = multiprocessing.Pipe(False)
emb_rcv, emb_snd = multiprocessing.Pipe(False)
emb_rec_rcv, emb_rec_snd = multiprocessing.Pipe(False)
aud_cmd_rcv, aud_cmd_snd = multiprocessing.Pipe(False)

shift_window = 1
silence_energy_threshold = 0  # 1300000.0
silence_duration_threshold = 10


def energy(samples):
    return np.sum(np.power(samples, 2.)) / float(len(samples))


def audio_norm(data):
    max_data = np.max(data)
    min_data = np.min(data)
    data = (data - min_data) / (max_data - min_data + 1e-6)
    return data - 0.5


running_avg_win = 100
running_avg_conv_win = 4
running_avg = None

seq_len = 3


def dump_processor(cmd_snd):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='dump_commands',)
    channel.queue_bind(queue='dump_commands', exchange='soundscene')

    def _callback(ch, method, properties, body):
        d = json.loads(body)
        print ('sending dump', body)
        cmd_snd.send(d)

    channel.basic_consume(queue='dump_commands',
                          auto_ack=True,
                          on_message_callback=_callback)
    print ('Consuming!')
    channel.start_consuming()


def audio_control_processor(aud_cmd_snd=None):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='audio_control',)
    channel.queue_bind(queue='audio_control', exchange='soundscene')

    def _callback(ch, method, properties, body):
        d = json.loads(body)
        print ('sending audio control', d)
        if aud_cmd_snd:
            if d['command'] == 'on':
                print ('turning on embeddings')
                aud_cmd_snd.send(0)
            elif d['command'] == 'off':
                print ('turning off embeddings')
                aud_cmd_snd.send(sys.maxint)
            elif d['command'] == 'resume_at':
                print ('resuming at', d['value'])
                aud_cmd_snd.send(d['value'])
            else:
                print ('received audio control command not understood', d)

    channel.basic_consume(queue='audio_control',
                          auto_ack=True,
                          on_message_callback=_callback)

    channel.start_consuming()


def infer_1csvm(emb_rcv):
    import pickle
    from sklearn import svm

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout'
                             )

    mdl = pickle.load(open('/tmp/onecsvm-silence.pkl'))
    _e = None
    while True:
        if emb_rcv.poll(.1):
            t, embedding = emb_rcv.recv()

            _e = np.concatenate((_e, embedding.reshape(
                1, -1)), axis=0) if _e is not None else embedding.reshape(1, -1)

            if len(_e) > 100:
                np.save('/tmp/emb', _e)
                _e = None

            print ('emb', embedding.shape)
            r = mdl.predict(embedding.reshape(1, -1))
            print ('preds', r)
            channel.basic_publish(exchange='embeddings',
                                  routing_key='',
                                  body=json.dumps(dict(time=t,
                                                       embeddings=r.tolist(),
                                                       idxs=[500])))
        else:
            time.sleep(.1)


def infer(emb_rcv):
    import json
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout'
                             )

    # Load TFLite model and allocate tensors.
    interpreter = tf.contrib.lite.Interpreter(
        model_path="/opt/soundscape/soundscape.tflite")
    interpreter.allocate_tensors()

    # Get input and output tensors.
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    #interpreter = tf.contrib.predictor.from_saved_model('/opt/soundscape/ss')

    batch_embeddings = []
    batch_times = []

    interpreter.invoke()

    class_idxs = interpreter.get_tensor(output_details[1]['index'])
    emb_idxs = interpreter.get_tensor(output_details[2]['index'])

    sleep_dur = .1  # secs

    print ('starting inference')
    while True:
        if emb_rcv.poll(.1):
            t, embedding = emb_rcv.recv()
            batch_embeddings.append(embedding)
            batch_times.append(t)

            if len(batch_embeddings) >= seq_len:

                # sequential_input = tf.keras.preprocessing.sequence.pad_sequences(batch_embeddings[:10], 10)
                sequential_input = np.expand_dims(
                    np.asarray(batch_embeddings[:seq_len]), 0)
                sequential_input = sequential_input.astype(dtype=np.float32)
                # print 'shape',sequential_input.shape
                interpreter.set_tensor(
                    input_details[0]['index'], sequential_input[...,emb_idxs])
                interpreter.invoke()
                output_data = interpreter.get_tensor(
                    output_details[0]['index'])
                #output_data = interpreter(dict(input=sequential_input))
                # inferences =
                # output_data['preds'].tolist()#output_data[0].tolist()
                inferences = output_data[0].tolist()

                channel.basic_publish(exchange='inference',
                                      routing_key='',
                                      body=json.dumps(dict(time=batch_times[seq_len - 1],
                                                           inferences=inferences,
                                                           idxs=class_idxs.tolist())))
                # idxs=output_data['idxs'].tolist())))#class_idxs.tolist())))
                batch_embeddings = batch_embeddings[shift_window:]
                batch_times = batch_times[shift_window:]

        else:
            time.sleep(sleep_dur)


def monitor_processes():
    mon_rcv, mon_snd = multiprocessing.Pipe(False)

    emb_p = multiprocessing.Process(
        target=embedding_processor.generate_embeddings, args=(frm_rcv,
                                                              emb_snd,
                                                              mon_snd,
                                                              emb_rec_snd,
                                                              aud_cmd_rcv,
                                                              RATE))
    emb_p.start()
    aud_p = multiprocessing.Process(
        target=audio_processor.record_audio, args=(aud_snd,
                                                   rec_snd,  # None
                                                   RATE,
                                                   CHUNK,
                                                   IDX,
                                                   CHANNELS))
    aud_p.start()
    rec_p = multiprocessing.Process(
        target=record_processor.record_audio, args=(rec_rcv,
                                                    cmd_rcv,
                                                    emb_rec_rcv,
                                                    RATE,
                                                    CHANNELS,
                                                    20,
                                                    '/archive'
                                                    ))

    rec_p.start()
    frm_p = multiprocessing.Process(
        target=framing_processor.frame_audio, args=(aud_rcv,
                                                    frm_snd,
                                                    RATE))
    frm_p.start()

    last_heartbeat = time.time() + 20  # to allow for startup time
    while True:
        if mon_rcv.poll(.1):
            last_heartbeat = mon_rcv.recv()

        if time.time() - last_heartbeat > 10:
            print ("EMBEDDING PROCESS HUNG...Restarting",)
            os.kill(emb_p.pid, 9)  # hard kill
            emb_p.join()
            emb_p = multiprocessing.Process(
                target=embedding_processor.generate_embeddings, args=(frm_rcv,
                                                                      emb_snd,
                                                                      mon_snd,
                                                                      emb_rec_snd,
                                                                      aud_cmd_rcv,
                                                                      RATE))
            emb_p.start()
            last_heartbeat = time.time() + 20
        if not aud_p.is_alive():
            print ("AUDIO PROCESS DIED...Restarting")
            aud_p = multiprocessing.Process(
                target=audio_processor.record_audio, args=(aud_snd,
                                                           rec_snd,  # None
                                                           RATE,
                                                           CHUNK,
                                                           IDX,
                                                           CHANNELS))
            aud_p.start()
        elif not emb_p.is_alive():
            print ("EMBEDDING PROCESS DIED...Restarting")
            emb_p = multiprocessing.Process(
                target=embedding_processor.generate_embeddings, args=(frm_rcv,
                                                                      emb_snd,
                                                                      mon_snd,
                                                                      aud_cmd_rcv,
                                                                      RATE))
            emb_p.start()
        elif not rec_p.is_alive():
            print ("RECORDING PROCESS DIED...Restarting")
            rec_p = multiprocessing.Process(
                target=record_processor.record_audio, args=(rec_rcv,
                                                            cmd_rcv,
                                                            emb_rec_rcv,
                                                            RATE,
                                                            CHANNELS,
                                                            20,
                                                            '/archive'
                                                            ))
            rec_p.start()
        else:
            time.sleep(.2)


if __name__ == "__main__":
    inf_thread = Thread(target=infer, args=(emb_rcv,))
    #inf_thread = Thread(target=infer_1csvm, args=(emb_rcv,))
    inf_thread.start()
    aud_ctrl_thread = Thread(target=audio_control_processor, args=(aud_cmd_snd,))
    aud_ctrl_thread.start()
    dmp_thread = Thread(target=dump_processor, args=(cmd_snd,))
    dmp_thread.start()
    mon_thread = Thread(target=monitor_processes, args=())
    mon_thread.start()

    mon_thread.join()
    inf_thread.join()
    dmp_thread.join()
