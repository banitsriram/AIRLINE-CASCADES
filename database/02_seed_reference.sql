-- 12 airports (insert order fixes airport_id 1=DEL .. 12=JAI, relied on by 03_seed_operational.sql)
INSERT INTO airport (iata_code, icao_code, city, country, timezone) VALUES
('DEL','VIDP','Delhi','India','Asia/Kolkata'),
('BOM','VABB','Mumbai','India','Asia/Kolkata'),
('BLR','VOBL','Bengaluru','India','Asia/Kolkata'),
('MAA','VOMM','Chennai','India','Asia/Kolkata'),
('CCU','VECC','Kolkata','India','Asia/Kolkata'),
('HYD','VOHS','Hyderabad','India','Asia/Kolkata'),
('PNQ','VAPO','Pune','India','Asia/Kolkata'),
('GOI','VOGO','Goa','India','Asia/Kolkata'),
('AMD','VAAH','Ahmedabad','India','Asia/Kolkata'),
('COK','VOCI','Kochi','India','Asia/Kolkata'),
('LKO','VILK','Lucknow','India','Asia/Kolkata'),
('JAI','VIJP','Jaipur','India','Asia/Kolkata');

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
