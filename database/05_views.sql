-- 05_views.sql
USE airport_aodb;

CREATE OR REPLACE VIEW FlightOperationsView AS
SELECT f.flight_id, f.flight_number, a.airline_name,
       CONCAT(ac.manufacturer,' ',ac.model) AS aircraft_type,
       g.gate_number, f.departure_airport, f.arrival_airport,
       f.scheduled_departure, f.scheduled_arrival, f.status
FROM FlightSchedule f
JOIN Airline a       ON f.airline_id = a.airline_id
JOIN AircraftType ac ON f.aircraft_type_id = ac.aircraft_type_id
LEFT JOIN Gate g     ON f.gate_id = g.gate_id;

CREATE OR REPLACE VIEW PassengerBoardingView AS
SELECT bp.boarding_pass_id,
       CONCAT(p.first_name,' ',p.last_name) AS passenger,
       f.flight_number, bp.seat_number, bp.boarding_group,
       bp.boarding_time, bp.boarding_status
FROM BoardingPass bp
JOIN Passenger p      ON bp.passenger_id = p.passenger_id
JOIN FlightSchedule f ON bp.flight_id = f.flight_id;

CREATE OR REPLACE VIEW StaffOperationsView AS
SELECT sa.assignment_id,
       CONCAT(s.first_name,' ',s.last_name) AS staff_member,
       f.flight_number, sa.assignment_role, sa.start_time, sa.end_time
FROM StaffAssignment sa
JOIN Staff s          ON sa.staff_id = s.staff_id
JOIN FlightSchedule f ON sa.flight_id = f.flight_id;

CREATE OR REPLACE VIEW FlightStatisticsView AS
SELECT f.flight_id, f.flight_number, f.status,
       COUNT(DISTINCT bp.boarding_pass_id) AS passenger_count,
       COUNT(DISTINCT sa.assignment_id)    AS staff_count
FROM FlightSchedule f
LEFT JOIN BoardingPass bp   ON f.flight_id = bp.flight_id
LEFT JOIN StaffAssignment sa ON f.flight_id = sa.flight_id
GROUP BY f.flight_id, f.flight_number, f.status;

-- Test
SELECT * FROM FlightOperationsView;
SELECT * FROM PassengerBoardingView;
SELECT * FROM StaffOperationsView;
SELECT * FROM FlightStatisticsView;
