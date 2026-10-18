-- 03_insert_data.sql  (fictional data only)
USE airport_aodb;

INSERT INTO Airline (iata_code, icao_code, airline_name, country, contact_email) VALUES
('AI','AIC','Air India','India','contact@airindia.example'),
('EK','UAE','Emirates','UAE','contact@emirates.example'),
('6E','IGO','IndiGo','India','contact@indigo.example'),
('SQ','SIA','Singapore Airlines','Singapore','contact@singapore.example'),
('BA','BAW','British Airways','United Kingdom','contact@ba.example');

INSERT INTO AircraftType (manufacturer, model, seat_capacity, cargo_capacity) VALUES
('Airbus','A320neo',186,15000),
('Boeing','737 MAX',210,18000),
('Boeing','777-300ER',354,50000),
('Airbus','A350-900',325,45000);

INSERT INTO Gate (gate_number, terminal, gate_type, status) VALUES
('A12','T1','Domestic','Available'),
('A13','T1','Domestic','Available'),
('B04','T2','International','Available'),
('B05','T2','International','Available'),
('C21','T1','Domestic','Maintenance');

INSERT INTO Passenger (first_name, last_name, date_of_birth, passport_number, nationality, email, phone) VALUES
('Rahul','Sharma','2001-04-12','P100001','Indian','rahul@example.com','9000000001'),
('Ananya','Patel','2000-08-22','P100002','Indian','ananya@example.com','9000000002'),
('Arjun','Mehta','1998-01-17','P100003','Indian','arjun@example.com','9000000003'),
('Sara','Khan','2002-06-30','P100004','Indian','sara@example.com','9000000004'),
('Vikram','Singh','1995-11-05','P100005','Indian','vikram@example.com','9000000005'),
('Meera','Iyer','1999-03-09','P100006','Indian','meera@example.com','9000000006');

INSERT INTO Staff (first_name, last_name, role, department, email, phone) VALUES
('Amit','Verma','Gate Agent','Operations','amit@example.com','9111111111'),
('Priya','Nair','Ground Staff','Ground Operations','priya@example.com','9222222222'),
('Rohan','Singh','Security Officer','Security','rohan@example.com','9333333333'),
('Neha','Shah','Operations Officer','Operations','neha@example.com','9444444444'),
('Kavita','Rao','Baggage Handler','Ground Operations','kavita@example.com','9555555555'),
('Dev','Malhotra','Airport Manager','Management','dev@example.com','9666666666');

INSERT INTO FlightSchedule
(flight_number, airline_id, aircraft_type_id, gate_id, departure_airport, arrival_airport,
 scheduled_departure, scheduled_arrival, status) VALUES
('AI101',1,1,1,'BOM','DEL','2026-09-28 12:30:00','2026-09-28 14:40:00','Boarding'),
('EK507',2,3,3,'BOM','DXB','2026-09-28 13:10:00','2026-09-28 15:00:00','Delayed'),
('6E203',3,1,2,'BOM','BLR','2026-09-28 13:25:00','2026-09-28 15:10:00','Scheduled'),
('SQ423',4,4,4,'BOM','SIN','2026-09-28 18:00:00','2026-09-28 23:30:00','Scheduled'),
('BA138',5,3,3,'BOM','LHR','2026-09-28 17:00:00','2026-09-28 22:30:00','Scheduled'),
('AI202',1,2,1,'BOM','MAA','2026-09-28 16:00:00','2026-09-28 18:15:00','Cancelled');

INSERT INTO BoardingPass
(passenger_id, flight_id, seat_number, boarding_group, boarding_time, boarding_status) VALUES
(1,1,'12A','A','2026-09-28 12:05:00','Boarded'),
(2,1,'12B','A','2026-09-28 12:07:00','Boarded'),
(3,1,'14C','B',NULL,'Not Boarded'),
(4,2,'21A','A',NULL,'Not Boarded'),
(5,3,'10D','A',NULL,'Not Boarded'),
(5,4,'30A','A',NULL,'Not Boarded');

INSERT INTO StaffAssignment (staff_id, flight_id, assignment_role, start_time, end_time) VALUES
(1,1,'Gate Agent','2026-09-28 11:30:00','2026-09-28 14:30:00'),
(2,1,'Ground Staff','2026-09-28 11:30:00','2026-09-28 14:30:00'),
(3,1,'Security','2026-09-28 11:00:00','2026-09-28 14:30:00'),
(4,2,'Operations Officer','2026-09-28 12:00:00','2026-09-28 15:30:00'),
(5,2,'Baggage Handler','2026-09-28 11:30:00','2026-09-28 14:30:00');
-- Staff 6 (Dev Malhotra) intentionally has no assignment, and Passenger 6 (Meera) has no
-- boarding pass: this makes the LEFT JOIN demonstrations meaningful.

SELECT 'Data loaded' AS info;
