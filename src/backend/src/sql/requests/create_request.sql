INSERT INTO requests (id, job_id, status, created_at, updated_at)
VALUES (%s, %s, %s, %s, %s)
RETURNING id, job_id, status, created_at, updated_at; 