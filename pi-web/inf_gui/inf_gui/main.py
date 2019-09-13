import numpy as np
import json
import time
from functools import partial
import csv
import subprocess
from threading import Thread, Lock
from bokeh.plotting import figure, curdoc
from bokeh.layouts import layout, grid
from bokeh.models import ColumnDataSource, LabelSet
from bokeh.palettes import inferno, Category20_20
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models.widgets import Button
from tornado import gen
import pika
import datetime

_CLASS_MAPPING = {}
class_mapping_csv = csv.DictReader(
    open('/opt/audioset/class_labels_indices.csv'))
class_names = []
# baby

# test
# class_idxs=[1,2,3,74,111,137,288,307,327,335,384,500]
for _n in class_mapping_csv:
    _CLASS_MAPPING[int(_n['index'])] = _n['display_name']

running_avg_win = 2
running_avg_conv_win = 2
running_avg = None


@gen.coroutine
def update(ys, time_step, idxs):

    def conv(ys):
        global running_avg
        ys = np.expand_dims(ys, axis=0) if ys.ndim == 1 else ys
        if running_avg is None:
            running_avg = ys
            return ys
        # add another sample
        running_avg = np.concatenate((running_avg, ys), axis=0)
        running_avg = running_avg[-running_avg_win:]

        # compute running avg
        avgs = []
        for _n in running_avg.T:
            t = np.convolve(_n, np.ones(running_avg_conv_win,) /
                            running_avg_conv_win, mode='valid')
            avgs.append(t[-1])
        return avgs

    print (datetime.datetime.fromtimestamp(time_step))
    y_avgs = conv(ys)
    y_avgs_idxs = zip(y_avgs, idxs)
    for i, (y, idx) in enumerate(y_avgs_idxs):
        single_ds[idx].stream(
            dict(pos=[i], y=[ys[i]]), rollover=1)
        duration_ds[idx].stream(
            dict(time=[datetime.datetime.fromtimestamp(time_step)], y=[y]), rollover=20 * 60)  # 20 mios

# Test button


def click_h(event):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_bind(queue='dump_commands', exchange='soundscene')

    d = dict(command='client',
             size=100)  # 100 secs
    channel.basic_publish(exchange='soundscene',
                          routing_key='dump_commands',
                          body=json.dumps(d))


def click_pause(event):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_bind(queue='audio_control', exchange='soundscene')

    d = dict(command='resume_at',
             value=time.time() + 30)  # 100 secs
    channel.basic_publish(exchange='soundscene',
                          routing_key='audio_control',
                          body=json.dumps(d))


button = Button(label='Sample')
button.on_click(click_h)

button_pause = Button(label='Pause Audio')
button_pause.on_click(click_pause)
# temp plot
temp_p = figure(plot_width=400,
                plot_height=400)
temp_p.xaxis.formatter = DatetimeTickFormatter(
    microseconds=['%H:%M:%S'],
    milliseconds=['%H:%M:%S'],
    seconds=['%H:%M:%S'],
    minsec=['%H:%M:%S'],
    minutes=['%H:%M:%S'],
    hourmin=['%H:%M:%S'],
    hours=['%H:%M:%S'],)
temp_ds = ColumnDataSource(data=dict(time=[], temp=[]))
temp_p.line(x='time',
            y='temp',
            #color=palette[i % 20],
            legend='Temp',
            line_width=2,
            source=temp_ds,)

# cpu plot
cpu_p = figure(plot_width=400,
               plot_height=400)
cpu_p.xaxis.formatter = DatetimeTickFormatter(
    microseconds=['%H:%M:%S'],
    milliseconds=['%H:%M:%S'],
    seconds=['%H:%M:%S'],
    minsec=['%H:%M:%S'],
    minutes=['%H:%M:%S'],
    hourmin=['%H:%M:%S'],
    hours=['%H:%M:%S'],)
cpu_ds = ColumnDataSource(data=dict(time=[], cpu=[]))
cpu_p.line(x='time',
           y='cpu',
           #color=palette[i % 20],
           legend='CPU',
           # line_width=2,
           source=cpu_ds,)


def temp_update(temp):
    temp_ds.stream(
        dict(time=[datetime.datetime.fromtimestamp(time.time())], temp=[temp]), rollover=240)


def cpu_update(cpu):
    cpu_ds.stream(
        dict(time=[datetime.datetime.fromtimestamp(time.time())], cpu=[cpu]), rollover=240)


palette = Category20_20
single_ds = {}
labels = {}
bar_p = figure(y_range=(0., 1.),
               plot_width=800,
               plot_height=800)

duration_ds = {}
line_p = figure(y_range=(0., 1.),
                plot_width=800,
                plot_height=800)
line_p.xaxis.formatter = DatetimeTickFormatter(
    microseconds=['%H:%M:%S'],
    milliseconds=['%H:%M:%S'],
    seconds=['%H:%M:%S'],
    minsec=['%H:%M:%S'],
    minutes=['%H:%M:%S'],
    hourmin=['%H:%M:%S'],
    hours=['%H:%M:%S'],)


def init_datasources(idxs):
    global single_ds
    global duration_ds
    global bar_p
    global line_p

    for i, _n in enumerate(idxs):
        cname = _CLASS_MAPPING[_n]
        single_ds[_n] = ColumnDataSource(data=dict(pos=[], y=[]))
        duration_ds[_n] = ColumnDataSource(data=dict(time=[], y=[]))
        bar_p.vbar(x='pos',
                   top='y',
                   bottom=0,
                   width=0.5,
                   fill_color=palette[i % 20],
                   legend=cname,
                   source=single_ds[_n],)
        line_p.line(x='time',
                    y='y',
                    color=palette[i % 20],
                    legend=cname,
                    # line_width=2,
                    line_dash='dashed',
                    source=duration_ds[_n],)

    line_p.legend.location = "top_right"
    line_p.legend.background_fill_alpha = .2
    bar_p.legend.location = "top_right"
    bar_p.legend.background_fill_alpha = .2


app_layout = layout([
    [bar_p],
    [line_p],
    [temp_p, cpu_p, ],
    [button, button_pause],
], sizing_mode='stretch_both')

doc = curdoc()
doc.add_root(app_layout)
doc.title = 'SoundScene Mobile'

seq_len = 3


def poll_cpu():
    while True:
        time.sleep(1)
        proc = subprocess.Popen(["top", "-bn2"], stdout=subprocess.PIPE)
        output = proc.stdout.read().split('\n')
        cpu_out = [_n for _n in output if 'Cpu' in _n]
        cpu_percent = [_n.split() for _n in cpu_out]

        try:
            doc.add_next_tick_callback(
                partial(cpu_update, float(cpu_percent[-1][1])))

        except:
            pass


def poll_temp():
    while True:
        time.sleep(1)

        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = int(f.read()) / 1000.0
            doc.add_next_tick_callback(partial(temp_update, temp))


def process_inf():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    def _callback(ch, method, properties, body):
        try:
            d = json.loads(body)
            doc.add_next_tick_callback(partial(update,
                                               ys=np.asarray(d['inferences']),
                                               time_step=d['time'],
                                               idxs=d['idxs'],))
        except:
            pass
    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()


# Get datasources
connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.exchange_declare(exchange='inference',
                         exchange_type='fanout')
result = channel.queue_declare(queue='', exclusive=True)
channel.queue_bind(queue=result.method.queue, exchange='inference')

_, _, r = channel.basic_get(queue=result.method.queue, auto_ack=True)

while r is None:
    time.sleep(.1)
    _, _, r = channel.basic_get(queue=result.method.queue, auto_ack=True)

init_datasources(json.loads(r)['idxs'])

channel.queue_delete(queue=result.method.queue)


inf_thread = Thread(target=process_inf, args=())
inf_thread.start()

temp_thread = Thread(target=poll_temp, args=())
temp_thread.start()

cpu_thread = Thread(target=poll_cpu, args=())
cpu_thread.start()
