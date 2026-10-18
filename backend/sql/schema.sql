CREATE TABLE wards (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  floor INT
);

CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('nurse','ward_admin','hospital_admin')),
  ward_id INT REFERENCES wards(id)
);

CREATE TABLE beds (
  id SERIAL PRIMARY KEY,
  ward_id INT NOT NULL REFERENCES wards(id),
  bed_number TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'available'
    CHECK (status IN ('available','occupied','cleaning','reserved')),
  version INT NOT NULL DEFAULT 1,
  UNIQUE (ward_id, bed_number)
);

CREATE TABLE patients (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  age INT,
  gender TEXT
);

CREATE TABLE admissions (
  id SERIAL PRIMARY KEY,
  patient_id INT NOT NULL REFERENCES patients(id),
  bed_id INT NOT NULL REFERENCES beds(id),
  admitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  discharged_at TIMESTAMPTZ
);

CREATE TABLE bed_events (
  id SERIAL PRIMARY KEY,
  bed_id INT NOT NULL REFERENCES beds(id),
  old_status TEXT,
  new_status TEXT NOT NULL,
  changed_by INT NOT NULL REFERENCES users(id),
  changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);