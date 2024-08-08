--
-- PostgreSQL database dump
--

-- Dumped from database version 14.11 (Ubuntu 14.11-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.11 (Ubuntu 14.11-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: update_auto_registration(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_auto_registration() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
	BEGIN
		UPDATE registered_resources SET auto_registration=NEW.auto_registration WHERE dbase_config=NEW.dbase_config;
		RETURN NULL;
	END;
$$;


ALTER FUNCTION public.update_auto_registration() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: available_resources; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.available_resources (
    dbase_config text NOT NULL,
    dbase_name text NOT NULL,
    description text,
    auto_registration boolean
);


ALTER TABLE public.available_resources OWNER TO postgres;

--
-- Name: curator_prefs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.curator_prefs (
    user_name text NOT NULL,
    submission_digests boolean NOT NULL,
    digest_interval integer DEFAULT 1440 NOT NULL,
    last_digest timestamp without time zone,
    submission_email_cc boolean NOT NULL,
    absent_until date
);


ALTER TABLE public.curator_prefs OWNER TO postgres;

--
-- Name: history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.history (
    "timestamp" timestamp with time zone NOT NULL,
    user_name text NOT NULL,
    field text NOT NULL,
    old text NOT NULL,
    new text NOT NULL
);


ALTER TABLE public.history OWNER TO postgres;

--
-- Name: invalid_usernames; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invalid_usernames (
    user_name text NOT NULL
);


ALTER TABLE public.invalid_usernames OWNER TO postgres;

--
-- Name: pending_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pending_requests (
    dbase_config text NOT NULL,
    user_name text NOT NULL,
    datestamp date NOT NULL
);


ALTER TABLE public.pending_requests OWNER TO postgres;

--
-- Name: permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.permissions (
    user_name text NOT NULL,
    permission text NOT NULL,
    curator text NOT NULL,
    datestamp date NOT NULL
);


ALTER TABLE public.permissions OWNER TO postgres;

--
-- Name: registered_curators; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.registered_curators (
    dbase_config text NOT NULL,
    user_name text NOT NULL,
    datestamp date NOT NULL
);


ALTER TABLE public.registered_curators OWNER TO postgres;

--
-- Name: registered_resources; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.registered_resources (
    dbase_config text NOT NULL,
    auto_registration boolean
);


ALTER TABLE public.registered_resources OWNER TO postgres;

--
-- Name: registered_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.registered_users (
    dbase_config text NOT NULL,
    user_name text NOT NULL,
    datestamp date NOT NULL
);


ALTER TABLE public.registered_users OWNER TO postgres;

--
-- Name: submission_digests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.submission_digests (
    user_name text NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    dbase_description text NOT NULL,
    submission_id text NOT NULL,
    submitter text NOT NULL,
    summary text NOT NULL
);


ALTER TABLE public.submission_digests OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_name text NOT NULL,
    surname text NOT NULL,
    first_name text NOT NULL,
    email text NOT NULL,
    affiliation text NOT NULL,
    date_entered date NOT NULL,
    datestamp date NOT NULL,
    status text NOT NULL,
    validate_start integer
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Data for Name: available_resources; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: curator_prefs; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: history; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: invalid_usernames; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: pending_requests; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: registered_curators; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: registered_resources; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: registered_users; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: submission_digests; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.users VALUES ('jdoe', 'Doe', 'John', 'john.doe@test.com', 'MegaCorp Inc.', '2024-08-08', '2024-08-08', 'validated', NULL);


--
-- Name: available_resources available_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.available_resources
    ADD CONSTRAINT available_resources_pkey PRIMARY KEY (dbase_config);


--
-- Name: curator_prefs curator_prefs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.curator_prefs
    ADD CONSTRAINT curator_prefs_pkey PRIMARY KEY (user_name);


--
-- Name: history history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.history
    ADD CONSTRAINT history_pkey PRIMARY KEY ("timestamp", user_name, field);


--
-- Name: invalid_usernames invalid_usernames_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invalid_usernames
    ADD CONSTRAINT invalid_usernames_pkey PRIMARY KEY (user_name);


--
-- Name: pending_requests pending_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pending_requests
    ADD CONSTRAINT pending_requests_pkey PRIMARY KEY (dbase_config, user_name);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (user_name, permission);


--
-- Name: registered_curators registered_curators_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registered_curators
    ADD CONSTRAINT registered_curators_pkey PRIMARY KEY (dbase_config, user_name);


--
-- Name: registered_resources registered_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registered_resources
    ADD CONSTRAINT registered_resources_pkey PRIMARY KEY (dbase_config);


--
-- Name: registered_users registered_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registered_users
    ADD CONSTRAINT registered_users_pkey PRIMARY KEY (dbase_config, user_name);


--
-- Name: submission_digests submission_digests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submission_digests
    ADD CONSTRAINT submission_digests_pkey PRIMARY KEY (user_name, "timestamp");


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_name);


--
-- Name: available_resources update_auto_registration; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_auto_registration AFTER UPDATE ON public.available_resources FOR EACH ROW EXECUTE FUNCTION public.update_auto_registration();


--
-- Name: history h_user_name; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.history
    ADD CONSTRAINT h_user_name FOREIGN KEY (user_name) REFERENCES public.users(user_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: permissions p_curator; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT p_curator FOREIGN KEY (curator) REFERENCES public.users(user_name) ON UPDATE CASCADE;


--
-- Name: permissions p_user_name; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT p_user_name FOREIGN KEY (user_name) REFERENCES public.users(user_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: registered_curators rc_dbase_config; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registered_curators
    ADD CONSTRAINT rc_dbase_config FOREIGN KEY (dbase_config) REFERENCES public.registered_resources(dbase_config) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: registered_curators rc_user_name; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registered_curators
    ADD CONSTRAINT rc_user_name FOREIGN KEY (user_name) REFERENCES public.users(user_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: registered_resources rr_dbase_config; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registered_resources
    ADD CONSTRAINT rr_dbase_config FOREIGN KEY (dbase_config) REFERENCES public.available_resources(dbase_config) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: registered_users ru_dbase_config; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registered_users
    ADD CONSTRAINT ru_dbase_config FOREIGN KEY (dbase_config) REFERENCES public.registered_resources(dbase_config) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: pending_requests ru_dbase_config; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pending_requests
    ADD CONSTRAINT ru_dbase_config FOREIGN KEY (dbase_config) REFERENCES public.registered_resources(dbase_config) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: registered_users ru_user_name; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.registered_users
    ADD CONSTRAINT ru_user_name FOREIGN KEY (user_name) REFERENCES public.users(user_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: pending_requests ru_user_name; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pending_requests
    ADD CONSTRAINT ru_user_name FOREIGN KEY (user_name) REFERENCES public.users(user_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: submission_digests sd_user_name; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submission_digests
    ADD CONSTRAINT sd_user_name FOREIGN KEY (user_name) REFERENCES public.users(user_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: curator_prefs sd_user_name; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.curator_prefs
    ADD CONSTRAINT sd_user_name FOREIGN KEY (user_name) REFERENCES public.users(user_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: TABLE available_resources; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.available_resources TO apache;


--
-- Name: TABLE curator_prefs; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.curator_prefs TO apache;


--
-- Name: TABLE history; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.history TO apache;


--
-- Name: TABLE invalid_usernames; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.invalid_usernames TO apache;


--
-- Name: TABLE pending_requests; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.pending_requests TO apache;


--
-- Name: TABLE permissions; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.permissions TO apache;


--
-- Name: TABLE registered_curators; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.registered_curators TO apache;


--
-- Name: TABLE registered_resources; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.registered_resources TO apache;


--
-- Name: TABLE registered_users; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.registered_users TO apache;


--
-- Name: TABLE submission_digests; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.submission_digests TO apache;


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.users TO apache;


--
-- PostgreSQL database dump complete
--

