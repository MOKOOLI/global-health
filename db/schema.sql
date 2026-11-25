-- Generated from app/models.py for PostgreSQL. Do not edit by hand.


CREATE TABLE api_key (
	id SERIAL NOT NULL, 
	key_hash VARCHAR(64) NOT NULL, 
	prefix VARCHAR(12) NOT NULL, 
	owner VARCHAR(200) NOT NULL, 
	tier VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	last_used_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (key_hash)
)

;


CREATE TABLE country (
	iso3 VARCHAR(3) NOT NULL, 
	iso2 VARCHAR(2), 
	iso_numeric VARCHAR(3), 
	name_en VARCHAR(120) NOT NULL, 
	name_fa VARCHAR(120), 
	region VARCHAR(80), 
	who_region VARCHAR(8), 
	income_group VARCHAR(60), 
	population BIGINT, 
	population_year INTEGER, 
	PRIMARY KEY (iso3)
)

;

CREATE INDEX ix_country_iso_numeric ON country (iso_numeric);

CREATE INDEX ix_country_region ON country (region);

CREATE INDEX ix_country_who_region ON country (who_region);


CREATE TABLE disease (
	id SERIAL NOT NULL, 
	slug VARCHAR(80) NOT NULL, 
	name_en VARCHAR(160) NOT NULL, 
	name_fa VARCHAR(160) NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	icd10 VARCHAR(120), 
	icd11 VARCHAR(120), 
	gbd_causes TEXT, 
	notifiable BOOLEAN NOT NULL, 
	description_en TEXT, 
	description_fa TEXT, 
	PRIMARY KEY (id)
)

;

CREATE UNIQUE INDEX ix_disease_slug ON disease (slug);

CREATE INDEX ix_disease_category ON disease (category);


CREATE TABLE etl_run (
	id SERIAL NOT NULL, 
	job VARCHAR(60) NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	finished_at TIMESTAMP WITHOUT TIME ZONE, 
	rows_written INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	message TEXT, 
	PRIMARY KEY (id)
)

;


CREATE TABLE source (
	id SERIAL NOT NULL, 
	code VARCHAR(40) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	url VARCHAR(300), 
	license VARCHAR(200), 
	citation TEXT, 
	is_synthetic BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
)

;


CREATE TABLE indicator (
	id SERIAL NOT NULL, 
	code VARCHAR(120) NOT NULL, 
	disease_id INTEGER, 
	source_id INTEGER NOT NULL, 
	measure VARCHAR(30) NOT NULL, 
	unit VARCHAR(30) NOT NULL, 
	name_en VARCHAR(300) NOT NULL, 
	name_fa VARCHAR(300), 
	external_code VARCHAR(80), 
	external_name VARCHAR(400), 
	higher_is_worse BOOLEAN NOT NULL, 
	age_standardized BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(disease_id) REFERENCES disease (id), 
	FOREIGN KEY(source_id) REFERENCES source (id)
)

;

CREATE INDEX ix_indicator_disease_id ON indicator (disease_id);

CREATE INDEX ix_indicator_measure ON indicator (measure);

CREATE UNIQUE INDEX ix_indicator_code ON indicator (code);


CREATE TABLE outbreak_alert (
	id SERIAL NOT NULL, 
	title VARCHAR(400) NOT NULL, 
	url VARCHAR(500) NOT NULL, 
	source VARCHAR(60) NOT NULL, 
	published_at TIMESTAMP WITHOUT TIME ZONE, 
	country_iso3 VARCHAR(3), 
	disease_id INTEGER, 
	summary TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_alert_url UNIQUE (url), 
	FOREIGN KEY(country_iso3) REFERENCES country (iso3), 
	FOREIGN KEY(disease_id) REFERENCES disease (id)
)

;

CREATE INDEX ix_outbreak_alert_disease_id ON outbreak_alert (disease_id);

CREATE INDEX ix_outbreak_alert_country_iso3 ON outbreak_alert (country_iso3);

CREATE INDEX ix_outbreak_alert_published_at ON outbreak_alert (published_at);


CREATE TABLE surveillance_series (
	id SERIAL NOT NULL, 
	disease_id INTEGER NOT NULL, 
	country_iso3 VARCHAR(3) NOT NULL, 
	source_id INTEGER NOT NULL, 
	metric VARCHAR(30) NOT NULL, 
	unit VARCHAR(20) NOT NULL, 
	note VARCHAR(300), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_surv_series UNIQUE (disease_id, country_iso3, source_id, metric), 
	FOREIGN KEY(disease_id) REFERENCES disease (id), 
	FOREIGN KEY(country_iso3) REFERENCES country (iso3), 
	FOREIGN KEY(source_id) REFERENCES source (id)
)

;

CREATE INDEX ix_surv_disease ON surveillance_series (disease_id);


CREATE TABLE observation (
	id SERIAL NOT NULL, 
	country_iso3 VARCHAR(3) NOT NULL, 
	indicator_id INTEGER NOT NULL, 
	year INTEGER NOT NULL, 
	sex VARCHAR(8) NOT NULL, 
	age_group VARCHAR(24) NOT NULL, 
	value FLOAT NOT NULL, 
	low FLOAT, 
	high FLOAT, 
	data_quality VARCHAR(12) NOT NULL, 
	retrieved_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_observation UNIQUE (country_iso3, indicator_id, year, sex, age_group), 
	FOREIGN KEY(country_iso3) REFERENCES country (iso3), 
	FOREIGN KEY(indicator_id) REFERENCES indicator (id)
)

;

CREATE INDEX ix_obs_country_indicator ON observation (country_iso3, indicator_id);

CREATE INDEX ix_obs_indicator_year ON observation (indicator_id, year);


CREATE TABLE surveillance_weekly (
	id SERIAL NOT NULL, 
	series_id INTEGER NOT NULL, 
	week_start DATE NOT NULL, 
	value FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_surv_week UNIQUE (series_id, week_start), 
	FOREIGN KEY(series_id) REFERENCES surveillance_series (id)
)

;

CREATE INDEX ix_surv_week_series ON surveillance_weekly (series_id, week_start);
