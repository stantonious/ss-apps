'''
Created on Jan 4, 2019

@author: bstaley
'''
import numpy as np
import tensorflow as tf

running_avg_win = 100
running_avg_conv_win = 4
running_avg = None


def infer(in_q,
          seq_len=10,
          shift_window=1,
          infrence_cb=None):
    
    def def_cb(ys, ys_avgs, time_step):
        print (ys, time_step)
        
    def conv(ys):
        global running_avg
        ys = np.expand_dims(ys, axis=0) if ys.ndim == 1 else ys
        if running_avg is None:
            running_avg = ys
            return ys[0]
        # add another sample
        running_avg = np.concatenate((running_avg, ys), axis=0)
        running_avg = running_avg[-running_avg_win:]

        # compute running avg
        avgs = []
        for _n in running_avg.T:
            t = np.convolve(_n, np.ones(running_avg_conv_win,) / running_avg_conv_win, mode='valid')
            avgs.append(t[-1])
        return avgs

    infrence_cb = infrence_cb or def_cb
    
    # Load TFLite model and allocate tensors.
    interpreter = tf.contrib.lite.Interpreter(model_path="/opt/soundscape/soundscape.tflite")
    interpreter.allocate_tensors()

    # Get input and output tensors.
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    print ('starting inferer processor', input_details[0])
    batch_embeddings = []
    batch_times = []

    while True:
    #    print 'emb q size', in_q.qsize()
        t, embedding = in_q.get(True)
        batch_embeddings.append(embedding)
        batch_times.append(t)
        # print 'got an inf record'
        
        if len(batch_embeddings) >= seq_len:
               
            # sequential_input = tf.keras.preprocessing.sequence.pad_sequences(batch_embeddings[:10], 10)
            sequential_input = np.expand_dims(np.asarray(batch_embeddings[:seq_len]), 0)
            sequential_input = sequential_input.astype(dtype=np.float32)
            # print 'shape',sequential_input.shape
            interpreter.set_tensor(input_details[0]['index'], sequential_input)
            interpreter.invoke()
            output_data = interpreter.get_tensor(output_details[0]['index'])
            
            infrence_cb(output_data[0],
                        conv(output_data[0]),
                        batch_times[seq_len - 1])

            batch_embeddings = batch_embeddings[shift_window:]
            batch_times = batch_times[shift_window:]
