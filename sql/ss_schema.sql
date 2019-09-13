DROP TABLE archive;
DROP TABLE models;
DROP TABLE api;
DROP TABLE ssuser;

CREATE TABLE ssuser
  (
    id SERIAL NOT NULL,
    first_name CHARACTER VARYING NULL,
    last_name CHARACTER VARYING NULL,
    phone CHARACTER VARYING NULL,
    email CHARACTER VARYING NULL,
    PRIMARY KEY (id)
  );

CREATE TABLE api
  (
    id SERIAL NOT NULL,
    key CHARACTER VARYING NOT NULL ,
    valid_through TIMESTAMP NULL,
    ssuser_ref INTEGER,
    FOREIGN KEY (ssuser_ref) REFERENCES ssuser,
    PRIMARY KEY (id)
  );

CREATE TABLE models
  (
    id SERIAL NOT NULL,
    mdl_loc CHARACTER VARYING NOT NULL ,
    created TIMESTAMP NULL,
    metadata CHARACTER VARYING NOT NULL ,
    PRIMARY KEY (id)
  );

CREATE TABLE archive
  (
    id SERIAL NOT NULL,
    emb_loc CHARACTER VARYING NOT NULL ,
    aud_loc CHARACTER VARYING NOT NULL ,
    archive_ref INTEGER,
    FOREIGN KEY (archive_ref) REFERENCES ssuser,
    PRIMARY KEY (id)
  );

GRANT USAGE, SELECT ON SEQUENCE ssuser_id_seq TO ss;
GRANT USAGE, SELECT ON SEQUENCE api_id_seq TO ss;
GRANT USAGE, SELECT ON SEQUENCE models_id_seq TO ss;
GRANT USAGE, SELECT ON SEQUENCE archive_id_seq TO ss;
