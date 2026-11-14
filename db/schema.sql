-- Admission Setu catalogue. Apply this file to a new empty database.
-- It does not connect anywhere by itself and does not alter any other database.

CREATE TABLE IF NOT EXISTS states_cities (
    id text PRIMARY KEY,
    state text NOT NULL,
    city text NOT NULL,
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS courses (
    slug text PRIMARY KEY,
    name text NOT NULL,
    category text,
    level text,
    duration text,
    eligibility text,
    short_description text,
    description text,
    about_content text,
    admission_process text,
    subjects_content text,
    scope_content text,
    mode text
);

CREATE TABLE IF NOT EXISTS colleges (
    slug text PRIMARY KEY,
    name text NOT NULL,
    city text,
    state text,
    type text,
    category text,
    rating numeric,
    reviews integer,
    fees_text text,
    image_url text,
    logo_url text,
    image_path text,
    logo_path text,
    approvals jsonb,
    established integer,
    description text,
    admission_process text,
    cutoff text,
    placement_content text,
    facilities_content text,
    hostel_life text,
    gallery jsonb,
    gallery_paths jsonb,
    tags jsonb,
    priority integer,
    featured_rank integer,
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS course_fees (
    id text PRIMARY KEY,
    college_slug text NOT NULL,
    course_slug text,
    course_name text,
    course_group text,
    specialization text,
    academic_level text,
    duration text,
    fee_amount numeric,
    fee_type text,
    year text
);

CREATE TABLE IF NOT EXISTS exams (
    slug text PRIMARY KEY,
    name text NOT NULL,
    full_name text,
    category text,
    exam_date text,
    is_top_exam boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,
    priority integer,
    level text,
    eligibility text,
    mode text,
    description text,
    summary_content text,
    application_process text,
    exam_pattern text,
    dates_content text,
    result_content text,
    official_website text
);

CREATE TABLE IF NOT EXISTS articles (
    slug text PRIMARY KEY,
    title text NOT NULL,
    description text,
    content text,
    category text,
    author text,
    published_at timestamptz,
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS scholarships (
    slug text PRIMARY KEY,
    title text NOT NULL,
    provider text,
    amount text,
    eligibility text,
    deadline text,
    category text,
    level text,
    description text,
    apply_url text,
    is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS faqs (
    id text PRIMARY KEY,
    question text NOT NULL,
    answer text,
    page text,
    item_slug text,
    display_order integer,
    is_active boolean NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS colleges_state_idx ON colleges (state);
CREATE INDEX IF NOT EXISTS colleges_city_idx ON colleges (city);
CREATE INDEX IF NOT EXISTS colleges_category_idx ON colleges (category);
CREATE INDEX IF NOT EXISTS course_fees_college_idx ON course_fees (college_slug);
CREATE INDEX IF NOT EXISTS faqs_college_idx ON faqs (page, item_slug);

ALTER TABLE courses ADD COLUMN IF NOT EXISTS short_description text;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS description text;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS about_content text;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS admission_process text;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS subjects_content text;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS scope_content text;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS mode text;

ALTER TABLE exams ADD COLUMN IF NOT EXISTS level text;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS eligibility text;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS mode text;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS description text;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS summary_content text;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS application_process text;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS exam_pattern text;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS dates_content text;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS result_content text;
ALTER TABLE exams ADD COLUMN IF NOT EXISTS official_website text;

CREATE TABLE IF NOT EXISTS engineering_facts (
    college_slug text PRIMARY KEY REFERENCES colleges (slug),
    source_slug text NOT NULL,
    nirf_rank integer,
    fee_range text,
    average_package text,
    ownership text,
    approval text,
    exams text
);

CREATE TABLE IF NOT EXISTS engineering_tables (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    college_slug text NOT NULL REFERENCES colleges (slug),
    page text NOT NULL,
    heading text,
    columns jsonb NOT NULL,
    rows jsonb NOT NULL,
    display_order integer NOT NULL
);

CREATE INDEX IF NOT EXISTS engineering_tables_college_idx ON engineering_tables (college_slug, display_order);
