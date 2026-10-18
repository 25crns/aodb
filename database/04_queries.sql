-- 04_queries.sql
-- Run ONE statement at a time (Workbench: put cursor in the statement, press Ctrl+Enter).
USE airport_aodb;

/* ============ A. READ / FILTER / SORT ============ */
SELECT * FROM FlightSchedule;
SELECT * FROM Passenger;
SELECT * FROM Staff;
SELECT * FROM Gate WHERE status = 'Available';                       -- available gates

SELECT * FROM FlightSchedule WHERE status = 'Delayed';               -- WHERE
SELECT * FROM FlightSchedule WHERE airline_id = 1;                   -- Air India flights
SELECT * FROM FlightSchedule ORDER BY scheduled_departure;           -- ORDER BY
SELECT * FROM Passenger WHERE last_name LIKE 'S%';                   -- LIKE
SELECT * FROM FlightSchedule
WHERE scheduled_departure BETWEEN '2026-09-28 00:00:00' AND '2026-09-28 23:59:59';   -- BETWEEN
SELECT * FROM FlightSchedule WHERE status IN ('Scheduled','Boarding');               -- IN
SELECT DISTINCT arrival_airport FROM FlightSchedule;                 -- DISTINCT

/* ============ B. CRUD (self-cleaning demo) ============ */
-- CREATE
INSERT INTO Passenger (first_name,last_name,date_of_birth,passport_number,nationality,email,phone)
VALUES ('Demo','Person','2000-01-01','P999999','Indian','demo@example.com','9999999999');
-- READ
SELECT * FROM Passenger WHERE passport_number = 'P999999';
-- UPDATE
UPDATE Passenger SET phone = '8888888888' WHERE passport_number = 'P999999';
-- UPDATE flight status / gate
UPDATE FlightSchedule SET status = 'Delayed' WHERE flight_number = '6E203';
UPDATE FlightSchedule SET status = 'Scheduled' WHERE flight_number = '6E203';   -- put it back
-- DELETE (works: demo passenger has no boarding pass)
DELETE FROM Passenger WHERE passport_number = 'P999999';
-- DELETE blocked by foreign key (passenger 1 has a boarding pass) -> expected ERROR 1451
DELETE FROM Passenger WHERE passenger_id = 1;

/* ============ C. JOINS ============ */
-- Flight + Airline + Aircraft + Gate
SELECT f.flight_number, a.airline_name, CONCAT(ac.manufacturer,' ',ac.model) AS aircraft,
       g.gate_number, f.scheduled_departure, f.scheduled_arrival, f.status
FROM FlightSchedule f
JOIN Airline a       ON f.airline_id = a.airline_id
JOIN AircraftType ac ON f.aircraft_type_id = ac.aircraft_type_id
LEFT JOIN Gate g     ON f.gate_id = g.gate_id;

-- Passenger + Flight (INNER JOIN)
SELECT CONCAT(p.first_name,' ',p.last_name) AS passenger, f.flight_number,
       bp.seat_number, bp.boarding_group, bp.boarding_status
FROM Passenger p
JOIN BoardingPass bp  ON p.passenger_id = bp.passenger_id
JOIN FlightSchedule f ON bp.flight_id = f.flight_id;

-- Staff + Flight (INNER JOIN)
SELECT CONCAT(s.first_name,' ',s.last_name) AS staff_member, f.flight_number,
       sa.assignment_role, sa.start_time, sa.end_time
FROM Staff s
JOIN StaffAssignment sa ON s.staff_id = sa.staff_id
JOIN FlightSchedule f   ON sa.flight_id = f.flight_id;

-- LEFT JOIN: ALL passengers, including those with no boarding pass (Meera)
SELECT CONCAT(p.first_name,' ',p.last_name) AS passenger, bp.flight_id, bp.seat_number
FROM Passenger p
LEFT JOIN BoardingPass bp ON p.passenger_id = bp.passenger_id;

-- LEFT JOIN: staff with NO assignment (Dev)
SELECT CONCAT(s.first_name,' ',s.last_name) AS staff_member, s.role
FROM Staff s
LEFT JOIN StaffAssignment sa ON s.staff_id = sa.staff_id
WHERE sa.assignment_id IS NULL;

/* ============ D. AGGREGATES ============ */
SELECT COUNT(*) AS total_flights FROM FlightSchedule;
SELECT AVG(seat_capacity) AS average_capacity FROM AircraftType;
SELECT SUM(seat_capacity) AS total_seats_available FROM AircraftType;
SELECT MIN(scheduled_departure) AS earliest_flight FROM FlightSchedule;
SELECT MAX(scheduled_departure) AS latest_flight FROM FlightSchedule;
SELECT COUNT(*) AS passengers_on_flight_1 FROM BoardingPass WHERE flight_id = 1;
SELECT SUM(ac.seat_capacity) AS seats_on_active_flights
FROM FlightSchedule f JOIN AircraftType ac ON f.aircraft_type_id = ac.aircraft_type_id
WHERE f.status <> 'Cancelled';

/* ============ E. GROUP BY ============ */
SELECT a.airline_name, COUNT(f.flight_id) AS total_flights
FROM Airline a LEFT JOIN FlightSchedule f ON a.airline_id = f.airline_id
GROUP BY a.airline_id, a.airline_name;

SELECT f.flight_number, COUNT(bp.boarding_pass_id) AS passengers
FROM FlightSchedule f LEFT JOIN BoardingPass bp ON f.flight_id = bp.flight_id
GROUP BY f.flight_id, f.flight_number;

SELECT f.flight_number, COUNT(sa.assignment_id) AS total_staff
FROM FlightSchedule f LEFT JOIN StaffAssignment sa ON f.flight_id = sa.flight_id
GROUP BY f.flight_id, f.flight_number;

/* ============ F. HAVING ============ */
-- Plan uses >5, but sample data is small; thresholds adjusted so rows are returned
SELECT airline_id, COUNT(*) AS total_flights
FROM FlightSchedule GROUP BY airline_id
HAVING COUNT(*) > 1;                    -- change to > 5 for a larger dataset

SELECT flight_id, COUNT(*) AS passengers
FROM BoardingPass GROUP BY flight_id
HAVING COUNT(*) >= 2;                   -- change to > 100 for a larger dataset

/* ============ G. SUBQUERIES ============ */
-- 1. Aircraft with above-average seat capacity
SELECT * FROM AircraftType
WHERE seat_capacity > (SELECT AVG(seat_capacity) FROM AircraftType);

-- 2. Airlines with above-average flight count
SELECT a.airline_name, COUNT(f.flight_id) AS total_flights
FROM Airline a JOIN FlightSchedule f ON a.airline_id = f.airline_id
GROUP BY a.airline_id, a.airline_name
HAVING COUNT(f.flight_id) > (
    SELECT AVG(flight_count) FROM (
        SELECT COUNT(*) AS flight_count FROM FlightSchedule GROUP BY airline_id
    ) AS airline_counts
);

-- 3. Flights with above-average passenger count
SELECT f.flight_number, COUNT(bp.boarding_pass_id) AS passengers
FROM FlightSchedule f JOIN BoardingPass bp ON f.flight_id = bp.flight_id
GROUP BY f.flight_id, f.flight_number
HAVING COUNT(bp.boarding_pass_id) > (
    SELECT AVG(c) FROM (SELECT COUNT(*) AS c FROM BoardingPass GROUP BY flight_id) AS t
);

/* ============ H. DASHBOARD / REPORT QUERIES (used by Flask later) ============ */
SELECT status, COUNT(*) AS total FROM FlightSchedule GROUP BY status;          -- flight status chart
SELECT boarding_status, COUNT(*) AS total FROM BoardingPass GROUP BY boarding_status;
SELECT department, COUNT(*) AS total FROM Staff GROUP BY department;
SELECT assignment_role, COUNT(*) AS total FROM StaffAssignment GROUP BY assignment_role;
SELECT status, COUNT(*) AS total FROM Gate GROUP BY status;
