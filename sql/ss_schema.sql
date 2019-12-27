DROP TABLE inference;

CREATE TABLE inference(
	id SERIAL NOT NULL,
	at TIMESTAMP,
	idx INTEGER,
	conf FLOAT,
	PRIMARY KEY (id)
  );

 CREATE INDEX ON inference(at);
 CREATE INDEX ON inference(at,idx);