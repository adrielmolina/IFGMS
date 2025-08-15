DELIMITER //

CREATE PROCEDURE delete_old_archives()
BEGIN
    DELETE FROM archive_table
    WHERE archived_date < (NOW() - INTERVAL 366 DAY);
END //

DELIMITER ;


CREATE EVENT delete_old_archives_event
ON SCHEDULE EVERY 1 DAY
DO
    CALL delete_old_archives();

# This event will run every day to delete archives older than 366 days.
# TODO install this later on the server.