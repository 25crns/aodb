-- 08_test_cases.sql
-- Run AFTER 01-07. Run one numbered test at a time.
-- Tests marked "EXPECTED ERROR" are supposed to fail: that is the proof the rule works.
USE airport_aodb;

/* ================= CONSTRAINT TESTS ================= */
-- C1 duplicate passport -> ERROR 1062
INSERT INTO Passenger (first_name,last_name,passport_number) VALUES ('Test','Person','P100001');

-- C2 invalid seat capacity -> ERROR 3819 (check constraint)
INSERT INTO AircraftType (manufacturer,model,seat_capacity,cargo_capacity) VALUES ('Test','Invalid',-10,1000);

-- C3 invalid flight status -> ERROR 3819
INSERT INTO FlightSchedule (flight_number,airline_id,aircraft_type_id,departure_airport,arrival_airport,
                            scheduled_departure,scheduled_arrival,status)
VALUES ('TEST001',1,1,'BOM','DEL','2026-09-28 10:00:00','2026-09-28 12:00:00','INVALID');

-- C4 missing required field (flight_number) -> ERROR 1364/1048
INSERT INTO FlightSchedule (airline_id,aircraft_type_id,departure_airport,arrival_airport,
                            scheduled_departure,scheduled_arrival)
VALUES (1,1,'BOM','DEL','2026-09-28 10:00:00','2026-09-28 12:00:00');

-- C5 duplicate airline code -> ERROR 1062
INSERT INTO Airline (iata_code,icao_code,airline_name,country) VALUES ('AI','XXX','Fake Air','India');

-- C6 arrival before departure -> ERROR 3819
INSERT INTO FlightSchedule (flight_number,airline_id,aircraft_type_id,departure_airport,arrival_airport,
                            scheduled_departure,scheduled_arrival)
VALUES ('TEST002',1,1,'BOM','DEL','2026-09-28 12:00:00','2026-09-28 10:00:00');

-- C7 foreign key violation (airline 99 does not exist) -> ERROR 1452
INSERT INTO FlightSchedule (flight_number,airline_id,aircraft_type_id,departure_airport,arrival_airport,
                            scheduled_departure,scheduled_arrival)
VALUES ('TEST003',99,1,'BOM','DEL','2026-09-29 10:00:00','2026-09-29 12:00:00');

-- C8 same seat twice on a flight -> ERROR 1062
INSERT INTO BoardingPass (passenger_id,flight_id,seat_number) VALUES (6,1,'12A');

/* ================= TRIGGER 1: BOARDING TIME ================= */
-- reset
UPDATE BoardingPass SET boarding_status='Not Boarded', boarding_time=NULL WHERE boarding_pass_id=3;
SELECT boarding_pass_id, boarding_status, boarding_time FROM BoardingPass WHERE boarding_pass_id=3;  -- NULL time
-- fire
UPDATE BoardingPass SET boarding_status='Boarded' WHERE boarding_pass_id=3;
SELECT boarding_pass_id, boarding_status, boarding_time FROM BoardingPass WHERE boarding_pass_id=3;  -- timestamp filled

/* ================= TRIGGER 2: FLIGHT STATUS HISTORY ================= */
SELECT * FROM FlightStatusHistory;
UPDATE FlightSchedule SET status='Boarding' WHERE flight_number='6E203';   -- Scheduled -> Boarding
UPDATE FlightSchedule SET status='Departed' WHERE flight_number='AI101';   -- Boarding  -> Departed
SELECT * FROM FlightStatusHistory;                                         -- 2 new rows

/* ================= TRIGGER 3: GATE CONFLICT ================= */
-- G1 overlaps AI101 (gate A12, 12:30-14:40) -> EXPECTED ERROR 1644 'Gate is already occupied...'
INSERT INTO FlightSchedule (flight_number,airline_id,aircraft_type_id,gate_id,departure_airport,arrival_airport,
                            scheduled_departure,scheduled_arrival)
VALUES ('TEST100',3,1,1,'BOM','GOI','2026-09-28 13:00:00','2026-09-28 14:00:00');

-- G2 moving 6E203 (13:25-15:10) into gate A12 -> EXPECTED ERROR (overlaps AI101)
UPDATE FlightSchedule SET gate_id = 1 WHERE flight_number='6E203';

-- G3 valid: same gate A12 but after AI101 and AI202(cancelled) -> allowed
INSERT INTO FlightSchedule (flight_number,airline_id,aircraft_type_id,gate_id,departure_airport,arrival_airport,
                            scheduled_departure,scheduled_arrival)
VALUES ('TEST101',3,1,1,'BOM','GOI','2026-09-28 20:00:00','2026-09-28 21:00:00');
-- clean up G3
DELETE FROM FlightSchedule WHERE flight_number='TEST101';

/* ================= TRIGGER 4: PASSENGER AUDIT ================= */
SELECT * FROM PassengerAudit;
UPDATE Passenger SET phone='9999999999' WHERE passenger_id=1;              -- logs UPDATE
INSERT INTO Passenger (first_name,last_name,passport_number) VALUES ('Temp','User','P777777');
DELETE FROM Passenger WHERE passport_number='P777777';                     -- logs DELETE
SELECT * FROM PassengerAudit;

/* ================= TRANSACTION TEST (procedure) ================= */
CALL sp_board_passenger(4);      -- succeeds (flight EK507 is Delayed, still open)
CALL sp_board_passenger(4);      -- EXPECTED ERROR: already boarded (rolled back)
CALL sp_board_passenger(999);    -- EXPECTED ERROR: not found
SELECT * FROM PassengerBoardingView;
