-- =====================================================
-- Seed Users v1.9
-- 30 demo users with different roles
-- Roles used: user, limit-user, up-user, manager, admin, super-admin
-- =====================================================

PRAGMA foreign_keys = ON;

-- Helper constant password hash (placeholder, NOT for production)
-- All demo users share the same password hash for simplicity.
-- Actual password hashing is handled by the application.

-- User 1
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'ali.ahmadi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000000', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Ali', 'Ahmadi', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'user', 'ali01', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 2
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'sara.mohammadi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000001', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Sara', 'Mohammadi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'admin', 'sara02', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 3
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'reza.karimi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000002', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Reza', 'Karimi', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'reza03', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 4
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'maryam.hosseini@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000003', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Maryam', 'Hosseini', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'limit-user', 'maryam04', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 5
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'ahmad.sadeghi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000004', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Ahmad', 'Sadeghi', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'user', 'ahmad05', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 6
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'fatemeh.ghasemi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000005', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Fatemeh', 'Ghasemi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'manager', 'fatemeh06', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 7
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'hossein.tavakoli@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000006', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Hossein', 'Tavakoli', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'manager', 'hossein07', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 8
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'zahra.miri@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000007', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Zahra', 'Miri', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'zahra08', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 9
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'mohammad.ramezani@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000008', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Mohammad', 'Ramezani', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'super-admin', 'mohammad09', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 10
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'leila.naderi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000009', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Leila', 'Naderi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'leila10', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 11
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'nima.khosravi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000010', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Nima', 'Khosravi', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'nima11', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 12
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'sepideh.farhadi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000011', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Sepideh', 'Farhadi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'limit-user', 'sepideh12', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 13
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'arash.beheshti@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000012', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Arash', 'Beheshti', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'limit-user', 'arash13', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 14
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'parisa.mirzaei@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000013', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Parisa', 'Mirzaei', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'parisa14', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 15
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'kamran.shirazi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000014', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Kamran', 'Shirazi', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'kamran15', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 16
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'farhad.yousefi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000015', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Farhad', 'Yousefi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'farhad16', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 17
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'elham.ahmadi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000016', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Elham', 'Ahmadi', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'user', 'elham17', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 18
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'kourosh.bahrami@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000017', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Kourosh', 'Bahrami', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'kourosh18', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 19
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'mina.gholami@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000018', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Mina', 'Gholami', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'mina19', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 20
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'samira.rahimi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000019', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Samira', 'Rahimi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'limit-user', 'samira20', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 21
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'amir.jafari@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000020', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Amir', 'Jafari', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'admin', 'amir21', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 22
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'hanieh.khosravi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000021', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Hanieh', 'Khosravi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'hanieh22', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 23
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'babak.ebrahimi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000022', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Babak', 'Ebrahimi', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'limit-user', 'babak23', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 24
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'golbahar.mohammadi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000023', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Golbahar', 'Mohammadi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'up-user', 'golbahar24', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 25
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'shahram.dehghan@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000024', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Shahram', 'Dehghan', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'super-admin', 'shahram25', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 26
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'shirin.azizi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000025', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Shirin', 'Azizi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'manager', 'shirin26', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 27
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'javad.soltani@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000026', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Javad', 'Soltani', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'limit-user', 'javad27', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 28
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'nazanin.khademi@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000027', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Nazanin', 'Khademi', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'super-admin', 'nazanin28', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 29
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'mehdi.farzin@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000028', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Mehdi', 'Farzin', 'male', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'admin', 'mehdi29', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- User 30
INSERT INTO contact (enabled) VALUES (1);
INSERT INTO email (contact_id, email_address, enabled) VALUES (last_insert_rowid(), 'yasmin.rostami@example.com', 1);
INSERT INTO phone (contact_id, phone_number, phone_type_id, enabled) VALUES (last_insert_rowid(), '09121000029', 1, 1);
INSERT INTO people (contact_id, first_name, last_name, gender, enabled) VALUES (last_insert_rowid(), 'Yasmin', 'Rostami', 'female', 1);
INSERT INTO user (people_id, role_id, username, password_hash, email_id, phone_id, enabled) VALUES (last_insert_rowid(), 'limit-user', 'yasmin30', '$2b$12$dummyhash12345678901234', (SELECT email_id FROM email ORDER BY email_id DESC LIMIT 1), (SELECT phone_id FROM phone ORDER BY phone_id DESC LIMIT 1), 1);

-- End of seed