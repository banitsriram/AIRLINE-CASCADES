SET FOREIGN_KEY_CHECKS = 0;

-- ============= LAYER 1 =============

CREATE TABLE airport (
  airport_id  INT AUTO_INCREMENT PRIMARY KEY,
  iata_code   CHAR(3) NOT NULL UNIQUE,
  icao_code   CHAR(4) UNIQUE,
  city        VARCHAR(60) NOT NULL,
  country     VARCHAR(60) NOT NULL,
  timezone    VARCHAR(40) NOT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE aircraft_type (
  type_id           INT AUTO_INCREMENT PRIMARY KEY,
  model             VARCHAR(40) NOT NULL,
  manufacturer      VARCHAR(40) NOT NULL,
  seat_capacity     INT NOT NULL CHECK (seat_capacity > 0),
  max_range_km      INT NOT NULL CHECK (max_range_km > 0),
  cruise_speed_kmh  INT CHECK (cruise_speed_kmh > 0),
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  UNIQUE KEY uq_type (model, manufacturer)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE delay_reason (
  reason_id   INT AUTO_INCREMENT PRIMARY KEY,
  category    ENUM('WEATHER','ATC','TECHNICAL','CREW',
                   'SECURITY','FUEL','MAINTENANCE','CASCADE') NOT NULL,
  description VARCHAR(200) NOT NULL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  UNIQUE KEY uq_reason (category, description)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============= LAYER 2 =============

CREATE TABLE route (
  route_id           INT AUTO_INCREMENT PRIMARY KEY,
  origin_airport_id  INT NOT NULL,
  dest_airport_id    INT NOT NULL,
  distance_km        INT NOT NULL CHECK (distance_km > 0),
  std_duration_min   INT NOT NULL CHECK (std_duration_min > 0),
  created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  deactivated_at     TIMESTAMP NULL,
  CONSTRAINT chk_route_distinct CHECK (origin_airport_id <> dest_airport_id),
  UNIQUE KEY uq_route (origin_airport_id, dest_airport_id),
  FOREIGN KEY (origin_airport_id) REFERENCES airport(airport_id) ON DELETE RESTRICT,
  FOREIGN KEY (dest_airport_id)   REFERENCES airport(airport_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE aircraft (
  aircraft_id      INT AUTO_INCREMENT PRIMARY KEY,
  registration     VARCHAR(10) NOT NULL UNIQUE,
  type_id          INT NOT NULL,
  base_airport_id  INT NOT NULL,
  status           ENUM('ACTIVE','MAINTENANCE','GROUNDED','RETIRED')
                     DEFAULT 'ACTIVE' NOT NULL,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  retired_at       TIMESTAMP NULL,
  FOREIGN KEY (type_id)         REFERENCES aircraft_type(type_id) ON DELETE RESTRICT,
  FOREIGN KEY (base_airport_id) REFERENCES airport(airport_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE crew (
  crew_id          INT AUTO_INCREMENT PRIMARY KEY,
  name             VARCHAR(80) NOT NULL,
  role             ENUM('CAPTAIN','FIRST_OFFICER','CABIN_CREW','PURSER') NOT NULL,
  base_airport_id  INT NOT NULL,
  hire_date        DATE NOT NULL,
  terminated_at    TIMESTAMP NULL,
  created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (base_airport_id) REFERENCES airport(airport_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE passenger (
  passenger_id  INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(80) NOT NULL,
  passport_no   VARCHAR(20) UNIQUE,
  email         VARCHAR(80),
  phone         VARCHAR(20),
  date_of_birth DATE NOT NULL,
  -- age is NOT a generated column: MySQL 8 disallows non-deterministic functions
  -- (CURDATE/NOW) in generated column expressions (error 3763). Computed at query
  -- time instead via TIMESTAMPDIFF(YEAR, date_of_birth, CURDATE()) -- see DEVIATIONS.md.
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
  -- "date_of_birth must be in the past" is NOT a CHECK constraint: MySQL 8 disallows
  -- non-deterministic functions (CURDATE/NOW) in CHECK expressions (error 3814).
  -- Enforced in the Flask form instead -- see DEVIATIONS.md.
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============= LAYER 3 =============

CREATE TABLE flight (
  flight_id         INT AUTO_INCREMENT PRIMARY KEY,
  flight_number     VARCHAR(10) NOT NULL,
  route_id          INT NOT NULL,
  aircraft_id       INT NOT NULL,
  sched_departure   DATETIME NOT NULL,
  sched_arrival     DATETIME NOT NULL,
  boarding_start    DATETIME NULL,
  gate_close        DATETIME NULL,
  actual_departure  DATETIME NULL,
  actual_arrival    DATETIME NULL,
  status            ENUM('SCHEDULED','BOARDING','DEPARTED',
                         'ARRIVED','CANCELLED','DIVERTED')
                      DEFAULT 'SCHEDULED' NOT NULL,
  delay_minutes     INT DEFAULT 0 NOT NULL,  -- DENORMALIZED: maintained by trigger
  parent_flight_id  INT NULL,
  created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT chk_flight_times CHECK (sched_arrival > sched_departure),
  -- chk_no_self_parent dropped: MySQL 8 disallows a column used in a CHECK constraint
  -- when it also has a FK referential action (parent_flight_id has ON DELETE SET NULL,
  -- error 3823). The cascade trigger never sets parent_flight_id = flight_id, so the
  -- invariant holds regardless -- see DEVIATIONS.md.
  FOREIGN KEY (route_id)         REFERENCES route(route_id) ON DELETE RESTRICT,
  FOREIGN KEY (aircraft_id)      REFERENCES aircraft(aircraft_id) ON DELETE RESTRICT,
  FOREIGN KEY (parent_flight_id) REFERENCES flight(flight_id) ON DELETE SET NULL,
  INDEX idx_flight_aircraft (aircraft_id),
  INDEX idx_flight_sched (sched_departure),
  INDEX idx_flight_parent (parent_flight_id),
  INDEX idx_flight_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE crew_certification (
  crew_id         INT NOT NULL,
  type_id         INT NOT NULL,
  certified_date  DATE NOT NULL,
  expiry_date     DATE NOT NULL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  PRIMARY KEY (crew_id, type_id),
  CONSTRAINT chk_cert_expiry CHECK (expiry_date > certified_date),
  FOREIGN KEY (crew_id) REFERENCES crew(crew_id) ON DELETE CASCADE,
  FOREIGN KEY (type_id) REFERENCES aircraft_type(type_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE duty_log (
  log_id           INT AUTO_INCREMENT PRIMARY KEY,
  crew_id          INT NOT NULL,
  duty_date        DATE NOT NULL,
  duty_start_time  DATETIME NULL,
  duty_end_time    DATETIME NULL,
  hours_flown      DECIMAL(5,2) DEFAULT 0 NOT NULL,   -- DENORMALIZED
  hours_on_duty    DECIMAL(5,2) DEFAULT 0 NOT NULL,   -- DENORMALIZED
  UNIQUE KEY uq_duty_crew_date (crew_id, duty_date),
  CONSTRAINT chk_duty_hours CHECK (hours_flown >= 0 AND hours_on_duty >= 0),
  FOREIGN KEY (crew_id) REFERENCES crew(crew_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE maintenance_log (
  maint_id        INT AUTO_INCREMENT PRIMARY KEY,
  aircraft_id     INT NOT NULL,
  maint_start     DATETIME NOT NULL,
  maint_end       DATETIME NOT NULL,
  type            ENUM('SCHEDULED','UNSCHEDULED','A_CHECK','B_CHECK',
                       'C_CHECK','D_CHECK','LINE_MAINTENANCE') NOT NULL,
  downtime_hours  DECIMAL(5,2) GENERATED ALWAYS AS
    (TIMESTAMPDIFF(MINUTE, maint_start, maint_end) / 60) VIRTUAL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT chk_maint_times CHECK (maint_end > maint_start),
  FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE booking (
  booking_id    INT AUTO_INCREMENT PRIMARY KEY,
  pnr           CHAR(6) NOT NULL UNIQUE,
  passenger_id  INT NOT NULL,
  booking_date  DATE DEFAULT (CURRENT_DATE) NOT NULL,
  status        ENUM('CONFIRMED','CANCELLED','CHECKED_IN','COMPLETED')
                  DEFAULT 'CONFIRMED' NOT NULL,
  cancelled_at  TIMESTAMP NULL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
  FOREIGN KEY (passenger_id) REFERENCES passenger(passenger_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============= LAYER 4 =============

CREATE TABLE crew_assignment (
  flight_id      INT NOT NULL,
  crew_id        INT NOT NULL,
  role           VARCHAR(20) NOT NULL,
  assigned_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  unassigned_at  TIMESTAMP NULL,
  PRIMARY KEY (flight_id, crew_id),
  FOREIGN KEY (flight_id) REFERENCES flight(flight_id) ON DELETE CASCADE,
  FOREIGN KEY (crew_id)   REFERENCES crew(crew_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE flight_delay (
  delay_id     INT AUTO_INCREMENT PRIMARY KEY,
  flight_id    INT NOT NULL,
  reason_id    INT NOT NULL,
  minutes      INT NOT NULL CHECK (minutes > 0),
  recorded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  resolved_at  TIMESTAMP NULL,
  CONSTRAINT chk_delay_resolve CHECK (resolved_at IS NULL OR resolved_at >= recorded_at),
  FOREIGN KEY (flight_id) REFERENCES flight(flight_id) ON DELETE CASCADE,
  FOREIGN KEY (reason_id) REFERENCES delay_reason(reason_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ticket (
  ticket_id      INT AUTO_INCREMENT PRIMARY KEY,
  booking_id     INT NOT NULL,
  flight_id      INT NOT NULL,
  seat_no        VARCHAR(4) NOT NULL,
  fare           DECIMAL(10,2) NOT NULL CHECK (fare >= 0),
  class          ENUM('ECONOMY','PREMIUM','BUSINESS','FIRST') NOT NULL,
  issued_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  checked_in_at  TIMESTAMP NULL,
  boarded_at     TIMESTAMP NULL,
  UNIQUE KEY uq_ticket_seat (flight_id, seat_no),
  FOREIGN KEY (booking_id) REFERENCES booking(booking_id) ON DELETE CASCADE,
  FOREIGN KEY (flight_id)  REFERENCES flight(flight_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
