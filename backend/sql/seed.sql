INSERT INTO wards (name, floor) VALUES
  ('General Ward', 1),
  ('ICU', 2),
  ('Pediatrics', 3);

INSERT INTO beds (ward_id, bed_number)
SELECT w.id, 'B' || g
FROM wards w, generate_series(1, 10) AS g;