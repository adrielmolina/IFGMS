INSERT INTO accounts
VALUES 
	(NULL, 'adriel', '$2b$12$HNc1/.azlbkEjv.GDSZ5IevH3qBk.Xy6ZoSq12IuIJqNWwvV18fTC', 'adrielmolina99@gmail.com', 'ADRIEL', 'DEL ROSARIO', 'PANGANIBAN', 'NA', '2000-12-30', '9114565728', '2025-03-30', 'Chapter', 'admin', 'approved', '2025-03-30'),
	(NULL, 'louis', '$2b$12$bUylDTUJJEhspPFdaKUMf.IOoY8TBSdnN.hpVZh2cHQrR4haK7Szm', 'sanorjo.louis111@gmail.com', 'LOUIS', 'DANO', 'SANORJO', 'NA', '2000-12-30', '9764251487', '2025-03-30', 'Chapter', 'admin', 'approved', '2025-03-30'),
	(NULL, 'abby', '$2b$12$hcJh2znWMM8UclkXH0AqeepT8/c16tieInF6nciBYWHBHb0Vb8bX.', 'abegailmontejo9@gmail.com', 'ABEGAIL', 'JANE', 'MONTEJO', 'NA', '2000-12-30', '9364875124', '2025-03-30', 'Chapter', 'admin', 'approved', '2025-03-30'),
	(NULL, 'jb', '$2b$12$OT5DFIM/d33uvDt0JisIkeOQmScP9SB6k4TKH.0ha4MokhfEM1uZW', 'johnbenedictcustodio8@gmail.com', 'JOHN', 'BENEDICT', 'CUSTODIO', 'NA', '2000-12-30', '9764851234', '2025-03-30', 'Chapter', 'user', 'approved', '2025-03-30'),
	(NULL, 'josh', '$2b$12$HfEvgMF6NBXvYmMMIUSv7.s47/dD96S0Wzh2/1r6GW1Gfg./SD/Yq', 'crisostomojosh23@gmail.com', 'JOSH', 'GOBRES', 'CRISOSTOMO', 'NA', '2000-12-30', '9758462134', '2025-03-30', 'Chapter', 'user', 'approved', '2025-03-30')
;

INSERT INTO membership_records
VALUES
    (NULL, 2025, FALSE, FALSE, NULL, NULL, 'CVSU', 'Public College', 'Cavite City', '1', FALSE, 'Chapter', NULL, NULL),
    (NULL, 2024, TRUE, FALSE, NULL, NULL, 'CNHS', 'Public High School', 'Cavite City', '1', FALSE, 'Chapter', NULL, NULL),
    (NULL, 2023, FALSE, TRUE, '2025-04-20', '2023-01-01', 'NCST', 'Private College', 'Dasmarinas', '1', FALSE, 'Dasmarinas', 'test', 'late-declare'),
    (NULL, 2022, TRUE, FALSE, NULL, NULL, 'San Sebastian College Recoletos', 'Private College', 'Cavite City', '1', FALSE, 'Chapter', NULL, NULL),
    (NULL, 2021, TRUE, FALSE, NULL, NULL, 'CVSU', 'Public College', 'Cavite City', '1', TRUE, 'Chapter', NULL, NULL)
;

INSERT INTO members_info
VALUES
    (NULL, 'adriel', 'robert', 'molina', 'NA', '1995-12-30', 24, 'male', '9845661321', 'adrielmolina99@gmail.com', 'cavite city', 'B+', 'test', NULL),
    (NULL, 'john', 'louis', 'sanorjo', 'NA', '2001-11-29', 23, 'male', '9845661321', 'sanorjo.louis111@gmail.com', 'cavite city', 'A+', 'test', NULL),
    (NULL, 'abegail', 'jane', 'montejo', 'NA', '2002-10-28', 22, 'female', '9845661321', 'abegailmontejo9@gmail.com', 'noveleta', 'B-', 'test', NULL),
    (NULL, 'john', 'benedict', 'custodio', 'NA', '2003-09-27', 21, 'male', '9845661321', 'johnbenedictcustodio8@gmail.com', 'cavite city', 'A-', 'test', NULL),
    (NULL, 'josh', 'gobres', 'crisostomo', 'NA', '2004-08-26', 20, 'male', '9845661321', 'crisostomojosh23@gmail.com', 'cavite city', 'O+', 'test', NULL)
;

INSERT INTO entry_contents
VALUES
    (NULL, 1, 'Gold', 'PG0369786', 1, TRUE, TRUE, '2025-04-20', TRUE, 10223, '2025-04-01', NULL, NULL),
    (NULL, 2, 'Bronze', 'PB4344789', 2, TRUE, TRUE, '2025-04-20', TRUE, 10224, '2025-04-01', NULL, NULL),
    (NULL, 3, 'Silver', 'PS0082478', 3, TRUE, TRUE, '2025-04-20', TRUE, 10225, '2025-04-01', NULL, NULL),
    (NULL, 4, 'Bronze', 'PB4344788', 4, TRUE, TRUE, '2025-04-20', TRUE, 10226, '2025-04-01', NULL, NULL),
    (NULL, 5, 'Silver', 'PS0082477', 5, TRUE, TRUE, '2025-04-20', TRUE, 10227, '2025-04-01', NULL, NULL)
;