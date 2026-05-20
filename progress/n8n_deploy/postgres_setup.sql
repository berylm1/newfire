-- Provision n8n_sherifah role + database on the existing Paperclip Postgres.
-- Run on Minisforum: sudo -u postgres psql -f postgres_setup.sql
-- Replace REPLACE_DB_PASSWORD with the value from .env.sherifah before running.

CREATE ROLE n8n_sherifah WITH LOGIN PASSWORD 'REPLACE_DB_PASSWORD'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;

CREATE DATABASE n8n_sherifah OWNER n8n_sherifah ENCODING 'UTF8';

REVOKE ALL ON DATABASE n8n_sherifah FROM PUBLIC;
GRANT ALL PRIVILEGES ON DATABASE n8n_sherifah TO n8n_sherifah;

\c n8n_sherifah
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO n8n_sherifah;
