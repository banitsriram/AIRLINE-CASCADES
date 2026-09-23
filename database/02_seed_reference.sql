-- 20 airports (insert order fixes airport_id 1=DEL .. 20=VNS, relied on by
-- 03_seed_operational.sql). 1-6 are hubs: 24h, more gates, bigger MCT.
-- Some spokes have a night curfew (open_time/close_time).
-- runway_slots_per_hour is tightened to each airport's real peak after the
-- schedule is generated (end of 03_seed_operational.sql).
INSERT INTO airport (iata_code, icao_code, city, country, timezone,
                     open_time, close_time, runway_slots_per_hour, min_connect_min, min_turnaround_min) VALUES
('DEL','VIDP','Delhi','India','Asia/Kolkata',          NULL, NULL, 12, 75, 60),
('BOM','VABB','Mumbai','India','Asia/Kolkata',         NULL, NULL, 10, 75, 60),
('BLR','VOBL','Bengaluru','India','Asia/Kolkata',      NULL, NULL, 10, 60, 55),
('MAA','VOMM','Chennai','India','Asia/Kolkata',        NULL, NULL,  8, 60, 50),
('CCU','VECC','Kolkata','India','Asia/Kolkata',        NULL, NULL,  8, 60, 50),
('HYD','VOHS','Hyderabad','India','Asia/Kolkata',      NULL, NULL,  8, 60, 50),
('PNQ','VAPO','Pune','India','Asia/Kolkata',           '06:00:00', '23:00:00', 4, 45, 45),
('GOI','VOGO','Goa','India','Asia/Kolkata',            '06:00:00', '23:30:00', 4, 45, 45),
('AMD','VAAH','Ahmedabad','India','Asia/Kolkata',      NULL, NULL,  6, 45, 45),
('COK','VOCI','Kochi','India','Asia/Kolkata',          NULL, NULL,  6, 45, 45),
('LKO','VILK','Lucknow','India','Asia/Kolkata',        NULL, NULL,  4, 45, 45),
('JAI','VIJP','Jaipur','India','Asia/Kolkata',         NULL, NULL,  4, 45, 45),
('TRV','VOTV','Thiruvananthapuram','India','Asia/Kolkata', NULL, NULL, 4, 45, 45),
('IXC','VICG','Chandigarh','India','Asia/Kolkata',     '06:00:00', '22:30:00', 3, 45, 45),
('PAT','VEPT','Patna','India','Asia/Kolkata',          '06:00:00', '22:30:00', 3, 45, 45),
('BBI','VEBS','Bhubaneswar','India','Asia/Kolkata',    NULL, NULL,  4, 45, 45),
('GAU','VEGT','Guwahati','India','Asia/Kolkata',       NULL, NULL,  4, 45, 45),
('NAG','VANP','Nagpur','India','Asia/Kolkata',         NULL, NULL,  4, 45, 45),
('IXB','VEBD','Bagdogra','India','Asia/Kolkata',       '06:00:00', '21:30:00', 3, 45, 45),
('VNS','VEBN','Varanasi','India','Asia/Kolkata',       '06:00:00', '22:30:00', 3, 45, 45);

-- Gates: 14 per hub across two terminals, 6 per spoke.
INSERT INTO gate (airport_id, gate_code, terminal)
WITH RECURSIVE seq AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM seq WHERE n < 14)
SELECT a.airport_id,
       CONCAT(IF(a.airport_id <= 6 AND seq.n > 7, 'B', 'A'), seq.n),
       IF(a.airport_id <= 6 AND seq.n > 7, 'T2', 'T1')
FROM airport a
JOIN seq ON seq.n <= IF(a.airport_id <= 6, 14, 6);

-- 4 aircraft types
INSERT INTO aircraft_type (model, manufacturer, seat_capacity, max_range_km, cruise_speed_kmh) VALUES
('A320-200','Airbus',180,6100,830),
('A321neo','Airbus',220,7400,830),
('B737-800','Boeing',189,5765,842),
('B777-300ER','Boeing',396,13650,892);

-- 8 delay reasons, one per category
INSERT INTO delay_reason (category, description) VALUES
('WEATHER','Delay due to adverse weather conditions at origin or destination'),
('ATC','Delay due to air traffic control restrictions or slot allocation'),
('TECHNICAL','Delay due to a technical or mechanical fault on the aircraft'),
('CREW','Delay due to crew unavailability or late crew reporting'),
('SECURITY','Delay due to security screening or incident at the airport'),
('FUEL','Delay due to fuel supply or refuelling issues'),
('MAINTENANCE','Delay due to unscheduled maintenance before departure'),
('CASCADE','Delay caused by a knock-on effect from an earlier delayed flight');

-- IATA AHM 730 delay codes, mapped to the 8 categories above
-- (reason_id: 1 WEATHER, 2 ATC, 3 TECHNICAL, 4 CREW, 5 SECURITY, 6 FUEL, 7 MAINTENANCE, 8 CASCADE).
INSERT INTO delay_code (iata_code, description, reason_id) VALUES
('71','Departure station weather below operating limits',1),
('72','Destination station weather below operating limits',1),
('73','En-route weather or diversion avoidance',1),
('75','De-icing of aircraft',1),
('77','Ground handling impaired by weather',1),
('81','ATC flow management - en-route demand/capacity',2),
('82','ATC staff or equipment en-route',2),
('83','ATC restriction at destination airport',2),
('84','Restriction at destination - weather',2),
('89','Restrictions at departure airport incl. runway/apron',2),
('41','Aircraft defect',3),
('44','Spares and maintenance equipment',3),
('46','Aircraft change for technical reasons',3),
('47','Standby aircraft unavailable',3),
('61','Flight plan, late completion or change',4),
('62','Operational requirements - fuel, load alteration',4),
('63','Late crew boarding or departure procedures',4),
('64','Flight deck crew shortage or sickness',4),
('65','Flight deck crew special request',4),
('66','Late cabin crew boarding',4),
('67','Cabin crew shortage or sickness',4),
('85','Mandatory security procedures',5),
('86','Immigration, customs, health',5),
('88','Airport facilities - security screening',5),
('36','Fuelling or defuelling, fuel supplier',6),
('42','Scheduled maintenance, late release',7),
('43','Non-scheduled maintenance',7),
('93','Aircraft rotation - late arrival from another flight',8),
('94','Cabin crew rotation - awaiting crew from another flight',8),
('95','Crew rotation - awaiting flight deck crew',8),
('96','Operations control - rerouting, diversion, consolidation',8);
