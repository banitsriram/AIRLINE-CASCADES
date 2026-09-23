-- Sample delay notices filed through simulate_delay(), so reports and the
-- delay log have data out of the box. Flights are picked by aircraft, day
-- offset and leg so the file doesn't depend on flight_id values.

SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 3 AND DATE(sched_departure) = CURDATE() + INTERVAL 2 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 95, (SELECT code_id FROM delay_code WHERE iata_code = '71'), 'Dense fog at DEL, RVR below CAT I minima', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Due to dense fog, departure is delayed. We regret the inconvenience.', FALSE, FALSE, FALSE, 'R. Mehta (DM DEL)', 'Fog forecast to lift by 09:00', @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 8 AND DATE(sched_departure) = CURDATE() + INTERVAL 2 DAY ORDER BY sched_departure LIMIT 2, 1);
CALL simulate_delay(@f, 40, (SELECT code_id FROM delay_code WHERE iata_code = '81'), 'Flow restriction over Nagpur FIR', 'AT_GATE', 'DELAYED', NULL, NULL, FALSE, NULL, 'ATC restrictions have delayed departure. Please remain near the gate.', FALSE, FALSE, FALSE, 'S. Iyer (OCC)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 11 AND DATE(sched_departure) = CURDATE() + INTERVAL 3 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 150, (SELECT code_id FROM delay_code WHERE iata_code = '41'), 'Hydraulic system B low pressure on pre-flight check', 'AT_GATE', 'ON_HOLD', NULL, NULL, FALSE, NULL, 'A technical check is in progress. A new departure time will be announced shortly.', TRUE, FALSE, FALSE, 'A. Khan (MCC)', 'AOG spares requested from base', @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 14 AND DATE(sched_departure) = CURDATE() + INTERVAL 3 DAY ORDER BY sched_departure LIMIT 1, 1);
CALL simulate_delay(@f, 30, (SELECT code_id FROM delay_code WHERE iata_code = '63'), 'Late crew reporting after rest-period dispute', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Departure delayed due to operational reasons.', FALSE, FALSE, FALSE, 'P. Nair (Crew Control)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 19 AND DATE(sched_departure) = CURDATE() + INTERVAL 4 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 60, (SELECT code_id FROM delay_code WHERE iata_code = '85'), 'Unattended bag in security hold area', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Security checks at the airport have delayed boarding.', FALSE, FALSE, FALSE, 'K. Rao (DM)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 22 AND DATE(sched_departure) = CURDATE() + INTERVAL 4 DAY ORDER BY sched_departure LIMIT 2, 1);
CALL simulate_delay(@f, 75, (SELECT code_id FROM delay_code WHERE iata_code = '36'), 'Fuel bowser breakdown at stand', 'AT_GATE', 'DELAYED', NULL, NULL, FALSE, NULL, 'Refuelling delay. We will board shortly.', FALSE, FALSE, FALSE, 'D. Das (Ramp)', 'Second bowser dispatched', @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 27 AND DATE(sched_departure) = CURDATE() + INTERVAL 5 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 200, (SELECT code_id FROM delay_code WHERE iata_code = '43'), 'Bird strike inspection after previous sector', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Aircraft inspection required. Meal vouchers are available at the counter.', TRUE, TRUE, TRUE, 'V. Menon (MCC)', 'Engine borescope inspection', @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 30 AND DATE(sched_departure) = CURDATE() + INTERVAL 5 DAY ORDER BY sched_departure LIMIT 4, 1);
CALL simulate_delay(@f, 45, (SELECT code_id FROM delay_code WHERE iata_code = '93'), 'Inbound aircraft late from previous rotation', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Your aircraft is arriving late from its previous flight.', FALSE, FALSE, FALSE, 'S. Iyer (OCC)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 35 AND DATE(sched_departure) = CURDATE() + INTERVAL 6 DAY ORDER BY sched_departure LIMIT 0, 1);
CALL simulate_delay(@f, 120, (SELECT code_id FROM delay_code WHERE iata_code = '72'), 'Thunderstorms at destination, holding expected', 'PRE_BOARDING', 'DELAYED', NULL, NULL, FALSE, NULL, 'Weather at the destination has delayed departure.', TRUE, FALSE, FALSE, 'R. Mehta (DM DEL)', NULL, @d);
SET @f = (SELECT flight_id FROM flight WHERE aircraft_id = 38 AND DATE(sched_departure) = CURDATE() + INTERVAL 6 DAY ORDER BY sched_departure LIMIT 2, 1);
CALL simulate_delay(@f, 35, (SELECT code_id FROM delay_code WHERE iata_code = '89'), 'Runway 27 closed for friction testing', 'TAXI', 'DELAYED', NULL, NULL, FALSE, NULL, 'Runway restrictions have delayed departure.', FALSE, FALSE, FALSE, 'A. Gupta (ATC liaison)', NULL, @d);
