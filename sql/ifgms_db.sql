CREATE TABLE `members_info` (
	`member_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`first_name` VARCHAR(255),
	`middle_name` VARCHAR(255),
	`last_name` VARCHAR(255),
	`suffix` ENUM('NA', 'Jr', 'Sr', 'II', 'III', 'IV', 'V', 'VI', 'VII') COMMENT 'change to enum and use the options in create_account',
	`birth_date` DATE,
	`age` INTEGER,
	`sex` VARCHAR(255),
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
	`user_level` ENUM('admin', 'user') DEFAULT 'user',
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
	`expiry_date` DATE,
	`location_particular` VARCHAR(255),
	`location_category` ENUM('Public Nursery', 'Private Nursery', 'Public Kinder', 'Private Kinder', 'Public Elementary School', 'Private Elementary School', 'Public High School', 'Private High School', 'Public Senior High School', 'Private Senior High School', 'Public Integrated School', 'Private Integrated School', 'Public College', 'Private College', 'Government Company/Organization', 'Private Company/Organization', 'Church', 'Red Cross 143', 'RCY', 'Brgy', 'LGU', 'MBD', 'Events', 'Training', 'Company/Organization Training', 'Individual', 'Walk-In'),
	`municipality` VARCHAR(255),
	`district` VARCHAR(255),
	`paid` BOOLEAN DEFAULT false COMMENT 'automatically mark as paid if all contents are paid',
	`origin` ENUM('Chapter', 'Dasmarinas', 'Silang'),
	`remarks` TEXT(65535),
	`tags` ENUM('late-declare', 'overage', 'underage'),
	PRIMARY KEY(`record_id`)
);


CREATE TABLE `inventory` (
	`inv_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`maab_category` ENUM('Classic', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Enhanced Platinum', 'Senior', 'Senior+'),
	`maab_no` VARCHAR(255) UNIQUE,
	`used` BOOLEAN,
	`remarks` TEXT(65535),
	`allocated_to` ENUM('Chapter', 'Dasmarinas', 'Silang'),
	PRIMARY KEY(`inv_id`)
);


CREATE TABLE `maab_claims` (
	`claim_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`date_filed` DATE,
	`claim_source` ENUM('chapter', 'dasma', 'silang'),
	`principal_insured_fname` VARCHAR(255),
	`principal_insured_mname` VARCHAR(255),
	`principal_insured_lname` VARCHAR(255),
	`maab_no` VARCHAR(255),
	`effectivity_date` DATE,
	`claimant_first_name` VARCHAR(255),
	`claimant_middle_name` VARCHAR(255),
	`claimant_last_name` VARCHAR(255),
	`relationship` VARCHAR(255) DEFAULT 'SAME',
	`contact_no` VARCHAR(255),
	`email` VARCHAR(255),
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
	PRIMARY KEY(`claim_id`)
);


CREATE TABLE `otp_verifications` (
	`id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`email` VARCHAR(255) NOT NULL,
	`otp` VARCHAR(6) NOT NULL,
	`expires_at` DATETIME NOT NULL,
	`created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY(`id`)
);


CREATE TABLE `audit_logs` (
	`action_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`date` DATETIME NOT NULL,
	`staff_name` VARCHAR(255) NOT NULL,
	`user_level` ENUM('staff', 'admin') NOT NULL,
	`action_name` VARCHAR(255) NOT NULL,
	`description` TEXT(65535) NOT NULL,
	`account_id` INTEGER NOT NULL UNIQUE,
	PRIMARY KEY(`action_id`)
);


CREATE TABLE `entry_contents` (
	`entry_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`record_id` INTEGER,
	`maab_category` ENUM('Classic', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Enhanced Platinum', 'Senior', 'Senior+'),
	`maab_no` VARCHAR(255) UNIQUE COMMENT 'maybe foreign key with inventory. what happens when id is platinum?',
	`member_id` INTEGER,
	`id_received` BOOLEAN,
	`declared` BOOLEAN,
	`declaration_date` DATE,
	`paid` BOOLEAN,
	`OR_num` INTEGER,
	`OR_date` DATE,
	`remarks` TEXT(65535),
	`tag` ENUM('late-declare', 'overage', 'underage'),
	PRIMARY KEY(`entry_id`)
) COMMENT='table for contents of an entry';


ALTER TABLE `audit_logs`
ADD FOREIGN KEY(`account_id`) REFERENCES `accounts`(`account_id`)
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `entry_contents`
ADD FOREIGN KEY(`record_id`) REFERENCES `membership_records`(`record_id`)
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `entry_contents`
ADD FOREIGN KEY(`member_id`) REFERENCES `members_info`(`member_id`)
ON UPDATE NO ACTION ON DELETE NO ACTION;