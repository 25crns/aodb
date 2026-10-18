-- 02_create_tables.sql
USE airport_aodb;

-- 1. Airline
CREATE TABLE Airline (
    airline_id    INT AUTO_INCREMENT PRIMARY KEY,
    iata_code     VARCHAR(3)   NOT NULL UNIQUE,
    icao_code     VARCHAR(4)   NOT NULL UNIQUE,
    airline_name  VARCHAR(100) NOT NULL,
    country       VARCHAR(100) NOT NULL,
    contact_email VARCHAR(150)
);

-- 2. AircraftType
CREATE TABLE AircraftType (
    aircraft_type_id INT AUTO_INCREMENT PRIMARY KEY,
    manufacturer     VARCHAR(100)  NOT NULL,
    model            VARCHAR(100)  NOT NULL,
    seat_capacity    INT           NOT NULL,
    cargo_capacity   DECIMAL(10,2) NOT NULL,
    CONSTRAINT chk_seat_capacity  CHECK (seat_capacity > 0),
    CONSTRAINT chk_cargo_capacity CHECK (cargo_capacity >= 0)
);

-- 3. Gate
CREATE TABLE Gate (
    gate_id     INT AUTO_INCREMENT PRIMARY KEY,
    gate_number VARCHAR(20) NOT NULL UNIQUE,
    terminal    VARCHAR(20) NOT NULL,
    gate_type   VARCHAR(30),
    status      VARCHAR(20) NOT NULL DEFAULT 'Available',
    CONSTRAINT chk_gate_status CHECK (status IN ('Available','Occupied','Maintenance','Closed'))
);

-- 4. Passenger
CREATE TABLE Passenger (
    passenger_id    INT AUTO_INCREMENT PRIMARY KEY,
    first_name      VARCHAR(50) NOT NULL,
    last_name       VARCHAR(50) NOT NULL,
    date_of_birth   DATE,
    passport_number VARCHAR(30) NOT NULL UNIQUE,
    nationality     VARCHAR(50),
    email           VARCHAR(150),
    phone           VARCHAR(30)
);

-- 5. Staff
CREATE TABLE Staff (
    staff_id          INT AUTO_INCREMENT PRIMARY KEY,
    first_name        VARCHAR(50)  NOT NULL,
    last_name         VARCHAR(50)  NOT NULL,
    role              VARCHAR(50)  NOT NULL,
    department        VARCHAR(100),
    email             VARCHAR(150),
    phone             VARCHAR(30),
    employment_status VARCHAR(30)  NOT NULL DEFAULT 'Active',
    CONSTRAINT chk_employment_status CHECK (employment_status IN ('Active','Inactive','On Leave'))
);

-- 6. FlightSchedule (central table)
CREATE TABLE FlightSchedule (
    flight_id           INT AUTO_INCREMENT PRIMARY KEY,
    flight_number       VARCHAR(20) NOT NULL UNIQUE,
    airline_id          INT NOT NULL,
    aircraft_type_id    INT NOT NULL,
    gate_id             INT,
    departure_airport   VARCHAR(10) NOT NULL,
    arrival_airport     VARCHAR(10) NOT NULL,
    scheduled_departure DATETIME    NOT NULL,
    scheduled_arrival   DATETIME    NOT NULL,
    actual_departure    DATETIME,
    actual_arrival      DATETIME,
    status              VARCHAR(20) NOT NULL DEFAULT 'Scheduled',
    CONSTRAINT chk_flight_status CHECK (status IN ('Scheduled','Boarding','Departed','Arrived','Delayed','Cancelled')),
    CONSTRAINT chk_flight_times  CHECK (scheduled_arrival >= scheduled_departure),
    CONSTRAINT fk_flight_airline  FOREIGN KEY (airline_id)       REFERENCES Airline(airline_id),
    CONSTRAINT fk_flight_aircraft FOREIGN KEY (aircraft_type_id) REFERENCES AircraftType(aircraft_type_id),
    CONSTRAINT fk_flight_gate     FOREIGN KEY (gate_id)          REFERENCES Gate(gate_id)
);

-- 7. StaffAssignment (junction: Staff N:M FlightSchedule)
CREATE TABLE StaffAssignment (
    assignment_id   INT AUTO_INCREMENT PRIMARY KEY,
    staff_id        INT NOT NULL,
    flight_id       INT NOT NULL,
    assignment_role VARCHAR(50) NOT NULL,
    start_time      DATETIME NOT NULL,
    end_time        DATETIME,
    CONSTRAINT fk_sa_staff  FOREIGN KEY (staff_id)  REFERENCES Staff(staff_id),
    CONSTRAINT fk_sa_flight FOREIGN KEY (flight_id) REFERENCES FlightSchedule(flight_id),
    CONSTRAINT chk_sa_times CHECK (end_time IS NULL OR end_time >= start_time)
);

-- 8. BoardingPass (junction: Passenger N:M FlightSchedule)
CREATE TABLE BoardingPass (
    boarding_pass_id INT AUTO_INCREMENT PRIMARY KEY,
    passenger_id     INT NOT NULL,
    flight_id        INT NOT NULL,
    seat_number      VARCHAR(10) NOT NULL,
    boarding_group   VARCHAR(10),
    boarding_time    DATETIME,
    boarding_status  VARCHAR(20) NOT NULL DEFAULT 'Not Boarded',
    CONSTRAINT chk_boarding_status CHECK (boarding_status IN ('Not Boarded','Boarded','Cancelled')),
    CONSTRAINT fk_bp_passenger FOREIGN KEY (passenger_id) REFERENCES Passenger(passenger_id),
    CONSTRAINT fk_bp_flight    FOREIGN KEY (flight_id)    REFERENCES FlightSchedule(flight_id),
    CONSTRAINT uq_flight_seat      UNIQUE (flight_id, seat_number),   -- no two people in one seat
    CONSTRAINT uq_passenger_flight UNIQUE (passenger_id, flight_id)   -- one pass per passenger per flight
);

-- 9. FlightStatusHistory (filled by trigger)
CREATE TABLE FlightStatusHistory (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_id  INT NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fsh_flight FOREIGN KEY (flight_id) REFERENCES FlightSchedule(flight_id)
);

-- 10. PassengerAudit (filled by trigger)
-- NOTE: deliberately NO foreign key on passenger_id, so that the audit row for a
-- DELETE can still be stored after the passenger row is gone.
CREATE TABLE PassengerAudit (
    audit_id     INT AUTO_INCREMENT PRIMARY KEY,
    passenger_id INT NOT NULL,
    operation    VARCHAR(20) NOT NULL,
    changed_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

SHOW TABLES;
