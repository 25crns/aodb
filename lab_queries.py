"""Whitelisted read-only queries shown on the 'SQL Lab' page (used for the viva demo).
Only queries defined here can be run - the browser never sends raw SQL."""

LAB_QUERIES = [
 ("where", "Filtering & sorting", "WHERE - delayed flights",
  "SELECT flight_number, departure_airport, arrival_airport, status\nFROM FlightSchedule\nWHERE status = 'Delayed';"),
 ("in", "Filtering & sorting", "IN - scheduled or boarding flights",
  "SELECT flight_number, status\nFROM FlightSchedule\nWHERE status IN ('Scheduled', 'Boarding');"),
 ("orderby", "Filtering & sorting", "ORDER BY - flights by departure time",
  "SELECT flight_number, scheduled_departure\nFROM FlightSchedule\nORDER BY scheduled_departure;"),
 ("like", "Filtering & sorting", "LIKE - surnames starting with S",
  "SELECT first_name, last_name\nFROM Passenger\nWHERE last_name LIKE 'S%';"),
 ("between", "Filtering & sorting", "BETWEEN - flights departing in a time window",
  "SELECT flight_number, scheduled_departure\nFROM FlightSchedule\nWHERE scheduled_departure BETWEEN '2026-09-28 12:00:00' AND '2026-09-28 17:00:00';"),
 ("distinct", "Filtering & sorting", "DISTINCT - destination airports",
  "SELECT DISTINCT arrival_airport\nFROM FlightSchedule;"),

 ("join_ops", "Joins", "INNER + LEFT JOIN - flight, airline, aircraft, gate",
  "SELECT f.flight_number, a.airline_name,\n       CONCAT(ac.manufacturer, ' ', ac.model) AS aircraft,\n       g.gate_number, f.status\nFROM FlightSchedule f\nJOIN Airline a       ON f.airline_id = a.airline_id\nJOIN AircraftType ac ON f.aircraft_type_id = ac.aircraft_type_id\nLEFT JOIN Gate g     ON f.gate_id = g.gate_id;"),
 ("join_pax", "Joins", "JOIN - passenger on flight",
  "SELECT CONCAT(p.first_name, ' ', p.last_name) AS passenger,\n       f.flight_number, bp.seat_number, bp.boarding_status\nFROM Passenger p\nJOIN BoardingPass bp  ON p.passenger_id = bp.passenger_id\nJOIN FlightSchedule f ON bp.flight_id = f.flight_id;"),
 ("join_staff", "Joins", "JOIN - staff on flight",
  "SELECT CONCAT(s.first_name, ' ', s.last_name) AS staff_member,\n       f.flight_number, sa.assignment_role\nFROM Staff s\nJOIN StaffAssignment sa ON s.staff_id = sa.staff_id\nJOIN FlightSchedule f   ON sa.flight_id = f.flight_id;"),
 ("left_pax", "Joins", "LEFT JOIN - all passengers, even without a boarding pass",
  "SELECT CONCAT(p.first_name, ' ', p.last_name) AS passenger,\n       bp.flight_id, bp.seat_number\nFROM Passenger p\nLEFT JOIN BoardingPass bp ON p.passenger_id = bp.passenger_id;"),
 ("left_staff", "Joins", "LEFT JOIN + IS NULL - staff with no assignment",
  "SELECT CONCAT(s.first_name, ' ', s.last_name) AS staff_member, s.role\nFROM Staff s\nLEFT JOIN StaffAssignment sa ON s.staff_id = sa.staff_id\nWHERE sa.assignment_id IS NULL;"),

 ("agg", "Aggregates, GROUP BY, HAVING", "COUNT / SUM / AVG / MIN / MAX on aircraft",
  "SELECT COUNT(*)           AS aircraft_types,\n       SUM(seat_capacity) AS total_seats,\n       AVG(seat_capacity) AS avg_seats,\n       MIN(seat_capacity) AS min_seats,\n       MAX(seat_capacity) AS max_seats\nFROM AircraftType;"),
 ("group_airline", "Aggregates, GROUP BY, HAVING", "GROUP BY - flights per airline",
  "SELECT a.airline_name, COUNT(f.flight_id) AS total_flights\nFROM Airline a\nLEFT JOIN FlightSchedule f ON a.airline_id = f.airline_id\nGROUP BY a.airline_id, a.airline_name;"),
 ("group_pax", "Aggregates, GROUP BY, HAVING", "GROUP BY - passengers per flight",
  "SELECT f.flight_number, COUNT(bp.boarding_pass_id) AS passengers\nFROM FlightSchedule f\nLEFT JOIN BoardingPass bp ON f.flight_id = bp.flight_id\nGROUP BY f.flight_id, f.flight_number;"),
 ("having", "Aggregates, GROUP BY, HAVING", "HAVING - airlines with more than 1 flight",
  "SELECT airline_id, COUNT(*) AS total_flights\nFROM FlightSchedule\nGROUP BY airline_id\nHAVING COUNT(*) > 1;"),

 ("sub_cap", "Subqueries", "Subquery - aircraft above average capacity",
  "SELECT manufacturer, model, seat_capacity\nFROM AircraftType\nWHERE seat_capacity > (SELECT AVG(seat_capacity) FROM AircraftType);"),
 ("sub_airline", "Subqueries", "Nested subquery - airlines above average flight count",
  "SELECT a.airline_name, COUNT(f.flight_id) AS total_flights\nFROM Airline a\nJOIN FlightSchedule f ON a.airline_id = f.airline_id\nGROUP BY a.airline_id, a.airline_name\nHAVING COUNT(f.flight_id) > (\n    SELECT AVG(flight_count) FROM (\n        SELECT COUNT(*) AS flight_count\n        FROM FlightSchedule GROUP BY airline_id\n    ) AS airline_counts\n);"),
 ("sub_flights", "Subqueries", "Subquery - flights above average passenger count",
  "SELECT f.flight_number, COUNT(bp.boarding_pass_id) AS passengers\nFROM FlightSchedule f\nJOIN BoardingPass bp ON f.flight_id = bp.flight_id\nGROUP BY f.flight_id, f.flight_number\nHAVING COUNT(bp.boarding_pass_id) > (\n    SELECT AVG(c) FROM (\n        SELECT COUNT(*) AS c FROM BoardingPass GROUP BY flight_id\n    ) AS t\n);"),

 ("v_ops", "Views", "FlightOperationsView", "SELECT * FROM FlightOperationsView;"),
 ("v_board", "Views", "PassengerBoardingView", "SELECT * FROM PassengerBoardingView;"),
 ("v_staff", "Views", "StaffOperationsView", "SELECT * FROM StaffOperationsView;"),
 ("v_stats", "Views", "FlightStatisticsView", "SELECT * FROM FlightStatisticsView;"),

 ("t_history", "Trigger results", "FlightStatusHistory (filled by trigger)",
  "SELECT * FROM FlightStatusHistory\nORDER BY changed_at DESC;"),
 ("t_audit", "Trigger results", "PassengerAudit (filled by trigger)",
  "SELECT * FROM PassengerAudit\nORDER BY changed_at DESC;"),
]
