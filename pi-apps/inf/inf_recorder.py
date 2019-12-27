#!/home/pi/venvs/ss/bin/python3
""" inf dump app """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import pika
import numpy as np
import datetime
import json
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from yamnet import yamnet as yamnet_model

Base = automap_base()
db_uri = 'postgresql+psycopg2://pi:raspberry@127.0.0.1:5432/ss'

engine = create_engine(db_uri,
                       pool_size=2,
                       echo=False,
                       isolation_level='READ_COMMITTED',
                       pool_recycle=20,
                       pool_pre_ping=True,
                       echo_pool=True)

Base.prepare(engine, reflect=True)

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base.query = db_session.query_property()

Inference = Base.classes.inference

topk=5

if __name__ == '__main__':
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
            idxs = np.asarray(d['idxs'])
            infs= np.asarray(d['inferences'])
            mel=np.asarray(d['mel'])
            time=int(d['time'])
            sorted_idxs=np.argsort(infs)[::-1]
            infs = infs[sorted_idxs][:topk]
            idxs=idxs[sorted_idxs][:topk]
            
            for _i,_inf in enumerate(infs):
                db_infs = Inference(at=datetime.datetime.fromtimestamp(time),
                                    idx=int(idxs[_i]),
                                    conf=float(infs[_i]))
                db_session.add(db_infs)
            db_session.commit()

        except Exception as e:
            print ('exception ', e)

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)
    channel.start_consuming()
