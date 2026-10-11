CREATE EXTENSION IF NOT EXISTS btree_gist;  
CREATE EXTENSION IF NOT EXISTS pgcrypto;   

DROP VIEW IF EXISTS v_utilisation;
DROP TABLE IF EXISTS notification, maintenance_record, waitlist, approval, reservation,
                     resource, resource_category, users, role CASCADE;
CREATE TABLE role (
  RoleID SERIAL PRIMARY KEY,
  RoleName VARCHAR(50) NOT NULL UNIQUE);

CREATE TABLE users (
  UserID SERIAL PRIMARY KEY,
  Name VARCHAR(100) NOT NULL,
  Email VARCHAR(100) NOT NULL UNIQUE,
  Phone VARCHAR(15),
  Password VARCHAR(255) NOT NULL,
  RoleID INT NOT NULL REFERENCES role(RoleID));

CREATE TABLE resource_category (
  CategoryID SERIAL PRIMARY KEY,
  CategoryName VARCHAR(50) NOT NULL UNIQUE);

CREATE TABLE resource (
  ResourceID SERIAL PRIMARY KEY,
  ResourceName VARCHAR(100) NOT NULL,
  CategoryID INT NOT NULL REFERENCES resource_category(CategoryID),
  Location VARCHAR(100),
  Capacity INT CHECK (Capacity > 0),
  Status VARCHAR(20) DEFAULT 'Available'
         CHECK (Status IN ('Available','Under Maintenance','Inactive')));

CREATE TABLE reservation (
  ReservationID SERIAL PRIMARY KEY,
  UserID INT NOT NULL REFERENCES users(UserID),
  ResourceID INT NOT NULL REFERENCES resource(ResourceID),
  BookingDate DATE NOT NULL,
  StartTime TIMESTAMP NOT NULL,
  EndTime TIMESTAMP NOT NULL CHECK (EndTime > StartTime),
  Status VARCHAR(20) NOT NULL DEFAULT 'Pending'
         CHECK (Status IN ('Pending','Approved','Rejected','Cancelled','Completed')),
  CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  EXCLUDE USING gist (ResourceID WITH =, tsrange(StartTime, EndTime) WITH &&)
          WHERE (Status IN ('Pending','Approved')));

CREATE TABLE approval (
  ApprovalID SERIAL PRIMARY KEY,
  ReservationID INT NOT NULL REFERENCES reservation(ReservationID),
  ApproverID INT NOT NULL REFERENCES users(UserID),
  ApprovalStatus VARCHAR(20) CHECK (ApprovalStatus IN ('Approved','Rejected','Pending')),
  ApprovalDate TIMESTAMP,
  Remarks VARCHAR(255),
  UNIQUE (ReservationID, ApproverID));

CREATE TABLE waitlist (
  WaitlistID SERIAL PRIMARY KEY,
  ResourceID INT NOT NULL REFERENCES resource(ResourceID),
  UserID INT NOT NULL REFERENCES users(UserID),
  ReqStartTime TIMESTAMP NOT NULL,
  ReqEndTime TIMESTAMP NOT NULL CHECK (ReqEndTime > ReqStartTime),
  Position INT NOT NULL,
  Status VARCHAR(20) DEFAULT 'Waiting'
         CHECK (Status IN ('Waiting','Notified','Expired','Converted')));

CREATE TABLE maintenance_record (
  MaintenanceID SERIAL PRIMARY KEY,
  ResourceID INT NOT NULL REFERENCES resource(ResourceID),
  ScheduledBy INT NOT NULL REFERENCES users(UserID),
  StartDate DATE NOT NULL,
  EndDate DATE NOT NULL CHECK (EndDate >= StartDate),
  Description VARCHAR(255),
  Status VARCHAR(20) DEFAULT 'Scheduled'
         CHECK (Status IN ('Scheduled','In Progress','Completed','Cancelled')));

CREATE TABLE notification (
  NotificationID SERIAL PRIMARY KEY,
  UserID INT NOT NULL REFERENCES users(UserID),
  ReservationID INT REFERENCES reservation(ReservationID),
  Message VARCHAR(255) NOT NULL,
  Type VARCHAR(30),
  IsRead BOOLEAN DEFAULT FALSE,
  CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP);


CREATE FUNCTION fn_block_maintenance() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM maintenance_record m
             WHERE m.ResourceID = NEW.ResourceID
               AND m.Status IN ('Scheduled','In Progress')
               AND NEW.StartTime::date <= m.EndDate
               AND NEW.EndTime::date   >= m.StartDate) THEN
    RAISE EXCEPTION 'Resource is under maintenance for this period';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_block_maintenance BEFORE INSERT ON reservation
  FOR EACH ROW EXECUTE FUNCTION fn_block_maintenance();

CREATE FUNCTION fn_notify_status() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' OR NEW.Status <> OLD.Status THEN
    INSERT INTO notification(UserID, ReservationID, Message, Type)
    VALUES (NEW.UserID, NEW.ReservationID,
            'Your reservation #' || NEW.ReservationID || ' is now ' || NEW.Status, 'Reservation');
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_notify_status AFTER INSERT OR UPDATE OF Status ON reservation
  FOR EACH ROW EXECUTE FUNCTION fn_notify_status();

CREATE FUNCTION fn_waitlist_promote() RETURNS trigger AS $$
DECLARE w RECORD;
BEGIN
  SELECT * INTO w FROM waitlist
   WHERE ResourceID = NEW.ResourceID AND Status = 'Waiting'
     AND ReqStartTime >= NEW.StartTime AND ReqEndTime <= NEW.EndTime
   ORDER BY Position LIMIT 1;
  IF FOUND THEN
    UPDATE waitlist SET Status = 'Notified' WHERE WaitlistID = w.WaitlistID;
    INSERT INTO notification(UserID, Message, Type)
    VALUES (w.UserID, 'A slot you waited for is now free. Book it quickly!', 'Waitlist');
  END IF;
  RETURN NULL;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_waitlist_promote AFTER UPDATE OF Status ON reservation
  FOR EACH ROW WHEN (NEW.Status IN ('Cancelled','Rejected') AND OLD.Status IN ('Pending','Approved'))
  EXECUTE FUNCTION fn_waitlist_promote();

CREATE FUNCTION fn_approval_apply() RETURNS trigger AS $$
BEGIN
  IF NEW.ApprovalStatus IN ('Approved','Rejected') THEN
    UPDATE reservation SET Status = NEW.ApprovalStatus WHERE ReservationID = NEW.ReservationID;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_approval_apply AFTER INSERT ON approval
  FOR EACH ROW EXECUTE FUNCTION fn_approval_apply();

CREATE FUNCTION book_resource(p_user INT, p_res INT, p_start TIMESTAMP, p_end TIMESTAMP)
RETURNS INT AS $$
DECLARE v_status VARCHAR; v_id INT;
BEGIN
  SELECT Status INTO v_status FROM resource WHERE ResourceID = p_res;
  IF v_status IS DISTINCT FROM 'Available' THEN
    RAISE EXCEPTION 'Resource is not available for booking';
  END IF;
  INSERT INTO reservation(UserID, ResourceID, BookingDate, StartTime, EndTime)
  VALUES (p_user, p_res, p_start::date, p_start, p_end) RETURNING ReservationID INTO v_id;
  RETURN v_id;
END $$ LANGUAGE plpgsql;

CREATE VIEW v_utilisation AS
SELECT r.ResourceID, r.ResourceName, c.CategoryName,
       COUNT(rv.ReservationID) AS approved_bookings,
       COALESCE(ROUND(SUM(EXTRACT(EPOCH FROM (rv.EndTime - rv.StartTime))/3600)::numeric, 1), 0) AS hours_booked
FROM resource r
JOIN resource_category c ON c.CategoryID = r.CategoryID
LEFT JOIN reservation rv ON rv.ResourceID = r.ResourceID AND rv.Status = 'Approved'
GROUP BY r.ResourceID, r.ResourceName, c.CategoryName;

INSERT INTO role(RoleName) VALUES ('Student'),('Faculty'),('Admin'),('Maintenance');
INSERT INTO users(Name,Email,Phone,Password,RoleID) VALUES
 ('Akshanya S','akshanya@campus.edu','9000000001',crypt('pass123',gen_salt('bf')),1),
 ('Dr. Rao','rao@campus.edu','9000000002',crypt('pass123',gen_salt('bf')),2),
 ('Admin User','admin@campus.edu','9000000003',crypt('pass123',gen_salt('bf')),3),
 ('Maintenance Staff','maint@campus.edu','9000000004',crypt('pass123',gen_salt('bf')),4);
INSERT INTO resource_category(CategoryName) VALUES
 ('Classroom'),('Lab'),('Study Room'),('Sports Venue'),('Equipment'),('Parking');
INSERT INTO resource(ResourceName,CategoryID,Location,Capacity) VALUES
 ('Classroom A101',1,'Block A',60),('Computer Lab 2',2,'Block B',40),
 ('Study Room 5',3,'Library',8),('Basketball Court',4,'Sports Complex',20),
 ('Projector Kit P1',5,'Store Room',1),('Parking Bay 12',6,'Main Gate',1);

