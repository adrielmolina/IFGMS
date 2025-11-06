CREATE TABLE `members_info` (
	`member_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`first_name` VARCHAR(255),
	`middle_name` VARCHAR(255),
	`last_name` VARCHAR(255),
	`suffix` ENUM('NA', 'Jr', 'Sr', 'II', 'III', 'IV', 'V', 'VI', 'VII') COMMENT 'change to enum and use the options in create_account',
	`birth_date` DATE,
	`age` INTEGER COMMENT 'age on register',
	`sex` ENUM('male', 'female'),
	`contact_no` VARCHAR(255),
	`email` VARCHAR(255),
	`address` VARCHAR(255) COMMENT 'not sure yet how to use this field',
	`blood_type` ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'),
	PRIMARY KEY(`member_id`)
);


CREATE TABLE `accounts` (
	`account_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`username` VARCHAR(255) NOT NULL UNIQUE,
	`password` VARCHAR(255) NOT NULL,
	`email` VARCHAR(255) UNIQUE,
	`first_name` VARCHAR(255),
	`middle_name` VARCHAR(255),
	`last_name` VARCHAR(255),
	`suffix` ENUM('NA', 'Jr', 'Sr', 'II', 'III', 'IV', 'V', 'VI', 'VII') DEFAULT 'NA',
	`birth_date` DATE,
	`contact_no` VARCHAR(255),
	`acct_created` DATE,
	`office_location` ENUM('Chapter', 'Dasmarinas', 'Silang'),
	`user_level` ENUM('admin', 'superadmin', 'staff') DEFAULT 'staff',
	`acct_status` ENUM('pending', 'approved', 'declined', 'archived') DEFAULT 'pending',
	`acct_review_date` DATE,
	PRIMARY KEY(`account_id`)
);


CREATE TABLE `membership_records` (
	`record_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`year` YEAR,
	`id_received` BOOLEAN COMMENT 'mark automatically if all cards in entry is received',
	`declared` BOOLEAN COMMENT 'auto mark if all entry content is declared
',
	`declaration_date` DATE COMMENT 'if declared. overwrite this field everytime declaration button is clicked',
	`effectivity_date` DATE,
	`location_particular` VARCHAR(255),
	`location_category` ENUM('Public Nursery', 'Private Nursery', 'Public Kinder', 'Private Kinder', 'Public Elementary School', 'Private Elementary School', 'Public High School', 'Private High School', 'Public Senior High School', 'Private Senior High School', 'Public Integrated School', 'Private Integrated School', 'Public College', 'Private College', 'Government Company/Organization', 'Private Company/Organization', 'Church', 'Red Cross 143', 'RCY', 'Brgy', 'LGU', 'MBD', 'Events', 'Training', 'Company/Organization Training', 'Individual', 'Walk-In', 'Online'),
	`municipality` ENUM('Cavite City', 'Kawit', 'Noveleta', 'Rosario', 'Bacoor', 'Imus', 'Dasmariñas', 'Carmona', 'General Mariano Alvarez (GMA)', 'Silang', 'General Trias', 'Amadeo', 'Indang', 'Tanza', 'Trece Martires', 'Alfonso', 'Gen. Emilio Aguinaldo (Bailen)', 'Magallanes', 'Maragondon', 'Mendez', 'Naic', 'Tagaytay City', 'Ternate'),
	`district` INTEGER,
	`paid` BOOLEAN DEFAULT false COMMENT 'automatically mark as paid if all contents are paid',
	`origin` ENUM('chapter', 'dasma', 'silang'),
	`remarks` TEXT(65535),
	`tags` ENUM() COMMENT 'late-declare, overage, underage',
	PRIMARY KEY(`record_id`)
);


CREATE TABLE `inventory` (
	`inv_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`maab_category` ENUM('Classic', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Enhanced Platinum', 'Senior', 'Senior+'),
	`maab_no` VARCHAR(255) UNIQUE,
	`used` BOOLEAN,
	`allocated_to` ENUM('Chapter', 'Dasmarinas', 'Silang'),
	`remarks` TEXT(65535),
	PRIMARY KEY(`inv_id`)
);


CREATE TABLE `maab_claims` (
	`claim_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`date_filed` DATE,
	`received_by` VARCHAR(255),
	`claim_origin` ENUM('chapter', 'dasma', 'silang'),
	`date_of_loss` DATE,
	`maab_no` VARCHAR(255),
	`same_as_insured` BOOLEAN,
	`claimant_first_name` VARCHAR(255),
	`claimant_middle_name` VARCHAR(255),
	`claimant_last_name` VARCHAR(255),
	`claimant_suffix` ENUM('NA', 'Jr', 'Sr', 'II', 'III', 'IV', 'V', 'VI', 'VII'),
	`relation_to_insured` VARCHAR(255),
	`claimant_contact_no` VARCHAR(255),
	`claimant_email` VARCHAR(255),
	`claim_remarks` TEXT(65535),
	`status` ENUM('pending', 'approved', 'denied'),
	`date_released` DATE,
	`chinabank_check_no` INTEGER,
	`chinabank_amount` DECIMAL,
	`bpi_check_no` INTEGER,
	`bpi_amount` DECIMAL,
	`release_remarks` TEXT(65535),
	`scanned_docs` VARCHAR(255) COMMENT 'create a folder on gdrive to store all the claim docs',
	`prm_file` VARCHAR(255) COMMENT 'link to prm file',
	`quit_claim_file` VARCHAR(255) COMMENT 'link to quit claim file',
	`picked_up` BOOLEAN,
	`date_picked_up` DATE,
	`req_claim_form` BOOLEAN,
	`req_prc_id` BOOLEAN,
	`req_med_cert` BOOLEAN,
	`req_hos_bill_or` BOOLEAN,
	`req_state_of_acc` BOOLEAN,
	`req_doctor_pres` BOOLEAN,
	`req_purchased_meds` BOOLEAN,
	`req_med_records` BOOLEAN,
	`req_animal_bite_treat_rec` BOOLEAN,
	`req_incident_rep` BOOLEAN,
	`req_police_rep` BOOLEAN,
	`req_brgy_rep` BOOLEAN,
	`req_drivers_lic` BOOLEAN,
	`req_birth_cert` BOOLEAN,
	`req_marriage_cert` BOOLEAN,
	`req_death_cert` BOOLEAN,
	`req_burial_receipts` BOOLEAN,
	`sent_advanced_notice` BOOLEAN,
	`claim_type` ENUM('ACCIDENT', 'DEATH'),
	PRIMARY KEY(`claim_id`)
);


CREATE TABLE `maab_claims_archive` (
	`archived_claim_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`claim_id` INTEGER NOT NULL UNIQUE,
	`date_filed` DATE,
	`received_by` VARCHAR(255),
	`claim_origin` ENUM('chapter', 'dasma', 'silang'),
	`date_of_loss` DATE,
	`maab_no` VARCHAR(255),
	`same_as_insured` BOOLEAN,
	`claimant_first_name` VARCHAR(255),
	`claimant_middle_name` VARCHAR(255),
	`claimant_last_name` VARCHAR(255),
	`claimant_suffix` ENUM('NA', 'Jr', 'Sr', 'II', 'III', 'IV', 'V', 'VI', 'VII'),
	`relation_to_insured` VARCHAR(255) DEFAULT 'SAME',
	`claimant_contact_no` VARCHAR(255),
	`claimant_email` VARCHAR(255),
	`claim_remarks` TEXT(65535),
	`status` ENUM('pending', 'approved', 'denied'),
	`date_released` DATE,
	`chinabank_check_no` INTEGER,
	`chinabank_amount` DECIMAL,
	`bpi_check_no` INTEGER,
	`bpi_amount` DECIMAL,
	`release_remarks` TEXT(65535),
	`scanned_docs` VARCHAR(255) COMMENT 'create a folder on gdrive to store all the claim docs',
	`prm_file` VARCHAR(255) COMMENT 'link to prm file',
	`quit_claim_file` VARCHAR(255) COMMENT 'link to quit claim file',
	`picked_up` BOOLEAN,
	`date_picked_up` DATE,
	`req_claim_form` BOOLEAN,
	`req_prc_id` BOOLEAN,
	`req_med_cert` BOOLEAN,
	`req_hos_bill_or` BOOLEAN,
	`req_state_of_acc` BOOLEAN,
	`req_doctor_pres` BOOLEAN,
	`req_purchased_meds` BOOLEAN,
	`req_med_records` BOOLEAN,
	`req_animal_bite_treat_rec` BOOLEAN,
	`req_incident_rep` BOOLEAN,
	`req_police_rep` BOOLEAN,
	`req_brgy_rep` BOOLEAN,
	`req_drivers_lic` BOOLEAN,
	`req_birth_cert` BOOLEAN,
	`req_marriage_cert` BOOLEAN,
	`req_death_cert` BOOLEAN,
	`req_burial_receipts` BOOLEAN,
	`sent_advanced_notice` BOOLEAN,
	`claim_type` ENUM('ACCIDENT', 'DEATH'),
	PRIMARY KEY(`archived_claim_id`)
);


CREATE TABLE `otp_verifications` (
	`id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`email` VARCHAR(255) NOT NULL,
	`otp` VARCHAR(6) NOT NULL,
	`expires_at` DATETIME NOT NULL,
	`created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	`otp_used` BOOLEAN DEFAULT 0,
	PRIMARY KEY(`id`)
);


CREATE TABLE `audit_logs` (
	`action_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`date` DATETIME NOT NULL,
	`staff_name` VARCHAR(255) NOT NULL,
	`user_level` ENUM('admin', 'superadmin', 'staff'),
	`action_name` VARCHAR(255) NOT NULL,
	`description` TEXT(65535) NOT NULL,
	`account_id` INTEGER,
	PRIMARY KEY(`action_id`)
);


CREATE TABLE `entry_contents` (
	`entry_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`record_id` INTEGER,
	`maab_category` ENUM('Classic', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Enhanced Platinum', 'Senior', 'Senior+', 'Safe Card'),
	`maab_no` VARCHAR(255) UNIQUE COMMENT 'maybe foreign key with inventory. what happens when id is platinum?',
	`member_id` INTEGER,
	`id_received` BOOLEAN,
	`declared` BOOLEAN,
	`declaration_date` DATE,
	`paid` BOOLEAN,
	`OR_num` INTEGER,
	`OR_date` DATE,
	`remarks` TEXT(65535),
	`tags` ENUM() COMMENT 'late-declare, overage, underage',
	`dispatch_ready` BOOLEAN,
	`dispatch_id` INTEGER UNIQUE,
	PRIMARY KEY(`entry_id`)
) COMMENT='table for contents of a membership_record entry';


CREATE TABLE `dispatch` (
	`dispatch_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`dispatch_type` ENUM('declaration', 'transmission'),
	`dispatch_origin` ENUM('chapter', 'dasma', 'silang'),
	`dispatch_year` YEAR,
	`dispatch_cutoff` DATE,
	`date_dispatched` DATE,
	`dispatch_total` INTEGER,
	`late_declare` BOOLEAN,
	`dispatch_remarks` TEXT(65535),
	PRIMARY KEY(`dispatch_id`)
);


CREATE TABLE `dispatch_contents` (
	`dispatch_content_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`entry_id` INTEGER NOT NULL UNIQUE,
	`maab_category` ENUM('classic', 'bronze', 'silver', 'gold', 'platinum', 'safe card', 'senior', 'senior+'),
	`maab_no` VARCHAR(255) UNIQUE,
	`member_name` VARCHAR(255),
	`member_birth_date` DATE,
	`effectivity_date` DATE,
	`location_particular` VARCHAR(255),
	`late_declare` BOOLEAN,
	PRIMARY KEY(`dispatch_content_id`)
);


ALTER TABLE `audit_logs`
ADD FOREIGN KEY(`account_id`) REFERENCES `accounts`(`account_id`)
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `entry_contents`
ADD FOREIGN KEY(`record_id`) REFERENCES `membership_records`(`record_id`)
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `entry_contents`
ADD FOREIGN KEY(`member_id`) REFERENCES `members_info`(`member_id`)
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `maab_claims`
ADD FOREIGN KEY(`maab_no`) REFERENCES `entry_contents`(`maab_no`)
ON UPDATE NO ACTION ON DELETE NO ACTION;