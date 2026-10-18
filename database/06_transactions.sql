-- 06_transactions.sql
USE airport_aodb;

/* ---- Demo 1: COMMIT ---- */
SELECT * FROM BoardingPass WHERE boarding_pass_id = 3;

START TRANSACTION;
UPDATE BoardingPass
SET boarding_status = 'Boarded', boarding_time = CURRENT_TIMESTAMP
WHERE boarding_pass_id = 3;
COMMIT;

SELECT * FROM BoardingPass WHERE boarding_pass_id = 3;   -- change is permanent

/* ---- Demo 2: ROLLBACK ---- */
START TRANSACTION;
UPDATE BoardingPass SET boarding_status = 'Cancelled' WHERE boarding_pass_id = 3;
SELECT * FROM BoardingPass WHERE boarding_pass_id = 3;   -- shows 'Cancelled' inside the transaction
ROLLBACK;
SELECT * FROM BoardingPass WHERE boarding_pass_id = 3;   -- back to 'Boarded'

/* ---- Demo 3: stored procedure with automatic rollback on error (used by the Flask BOARD button) ---- */
DROP PROCEDURE IF EXISTS sp_board_passenger;
DELIMITER //
CREATE PROCEDURE sp_board_passenger(IN p_boarding_pass_id INT)
BEGIN
    DECLARE v_bp_status     VARCHAR(20);
    DECLARE v_flight_status VARCHAR(20);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT bp.boarding_status, f.status
    INTO v_bp_status, v_flight_status
    FROM BoardingPass bp
    JOIN FlightSchedule f ON bp.flight_id = f.flight_id
    WHERE bp.boarding_pass_id = p_boarding_pass_id
    FOR UPDATE;

    IF v_bp_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Boarding pass not found';
    END IF;
    IF v_bp_status = 'Boarded' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Passenger already boarded';
    END IF;
    IF v_flight_status IN ('Cancelled','Departed','Arrived') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Flight is not open for boarding';
    END IF;

    UPDATE BoardingPass
    SET boarding_status = 'Boarded', boarding_time = CURRENT_TIMESTAMP
    WHERE boarding_pass_id = p_boarding_pass_id;

    COMMIT;
END//
DELIMITER ;

-- Try it (boarding pass 4 = flight EK507, Delayed -> allowed; calling it twice -> error + rollback)
-- CALL sp_board_passenger(4);
-- CALL sp_board_passenger(4);     -- ERROR: Passenger already boarded
-- CALL sp_board_passenger(999);   -- ERROR: Boarding pass not found
