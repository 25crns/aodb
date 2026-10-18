-- 07_triggers.sql
USE airport_aodb;

DROP TRIGGER IF EXISTS trg_boarding_time;
DROP TRIGGER IF EXISTS trg_flight_status_history;
DROP TRIGGER IF EXISTS trg_gate_conflict_insert;
DROP TRIGGER IF EXISTS trg_gate_conflict_update;
DROP TRIGGER IF EXISTS trg_passenger_update_audit;
DROP TRIGGER IF EXISTS trg_passenger_delete_audit;

DELIMITER //

/* Trigger 1: automatic boarding time (BEFORE UPDATE, so we can modify NEW) */
CREATE TRIGGER trg_boarding_time
BEFORE UPDATE ON BoardingPass
FOR EACH ROW
BEGIN
    IF NEW.boarding_status = 'Boarded'
       AND OLD.boarding_status <> 'Boarded'
       AND NEW.boarding_time IS NULL THEN
        SET NEW.boarding_time = CURRENT_TIMESTAMP;
    END IF;
END//

/* Trigger 2: flight status audit (AFTER UPDATE) */
CREATE TRIGGER trg_flight_status_history
AFTER UPDATE ON FlightSchedule
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO FlightStatusHistory (flight_id, old_status, new_status)
        VALUES (NEW.flight_id, OLD.status, NEW.status);
    END IF;
END//

/* Trigger 3a: gate conflict on INSERT (BEFORE INSERT) */
CREATE TRIGGER trg_gate_conflict_insert
BEFORE INSERT ON FlightSchedule
FOR EACH ROW
BEGIN
    IF NEW.gate_id IS NOT NULL AND NEW.status <> 'Cancelled'
       AND EXISTS (
            SELECT 1 FROM FlightSchedule f
            WHERE f.gate_id = NEW.gate_id
              AND f.status <> 'Cancelled'
              AND NEW.scheduled_departure < f.scheduled_arrival
              AND NEW.scheduled_arrival   > f.scheduled_departure
       ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Gate is already occupied during this time period';
    END IF;
END//

/* Trigger 3b: gate conflict on UPDATE of gate/time/status (excludes the flight itself) */
CREATE TRIGGER trg_gate_conflict_update
BEFORE UPDATE ON FlightSchedule
FOR EACH ROW
BEGIN
    IF NEW.gate_id IS NOT NULL AND NEW.status <> 'Cancelled'
       AND EXISTS (
            SELECT 1 FROM FlightSchedule f
            WHERE f.gate_id = NEW.gate_id
              AND f.flight_id <> NEW.flight_id
              AND f.status <> 'Cancelled'
              AND NEW.scheduled_departure < f.scheduled_arrival
              AND NEW.scheduled_arrival   > f.scheduled_departure
       ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Gate is already occupied during this time period';
    END IF;
END//

/* Trigger 4a: passenger audit - UPDATE */
CREATE TRIGGER trg_passenger_update_audit
AFTER UPDATE ON Passenger
FOR EACH ROW
BEGIN
    INSERT INTO PassengerAudit (passenger_id, operation)
    VALUES (NEW.passenger_id, 'UPDATE');
END//

/* Trigger 4b: passenger audit - DELETE */
CREATE TRIGGER trg_passenger_delete_audit
AFTER DELETE ON Passenger
FOR EACH ROW
BEGIN
    INSERT INTO PassengerAudit (passenger_id, operation)
    VALUES (OLD.passenger_id, 'DELETE');
END//

DELIMITER ;

SHOW TRIGGERS;
