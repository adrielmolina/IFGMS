CREATE TABLE `members_info` (
	`member_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`first_name` VARCHAR(255),
	`middle_name` VARCHAR(255),
	`last_name` VARCHAR(255),
	`suffix` VARCHAR(255) DEFAULT 'n/a',
	`birth_date` DATE,
	`age` INTEGER,
	`gender` VARCHAR(255),
	`contact_no` VARCHAR(255),
	`email` VARCHAR(255),
	`address` VARCHAR(255) COMMENT 'not sure yet how to use this field',
	`blood_type` ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'),
	PRIMARY KEY(`member_id`)
);


CREATE TABLE `accounts` (
	`account_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`username` VARCHAR(255),
	`password` VARCHAR(255),
	`email` VARCHAR(255),
	`first_name` VARCHAR(255),
	`middle_name` VARCHAR(255),
	`last_name` VARCHAR(255),
	`suffix` VARCHAR(255) DEFAULT 'n/a',
	`birth_date` DATE,
	`contact_no` VARCHAR(255),
	`acct_created` DATE,
	`office_location` ENUM('Chapter', 'Dasmarinas', 'Silang'),
	`user_level` ENUM('admin', 'user'),
	`acct_status` ENUM('pending', 'approved', 'declined', 'archived') DEFAULT 'pending',
	`acct_review_date` DATE,
	PRIMARY KEY(`account_id`)
);


CREATE TABLE `membership_records` (
	`transaction_no` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`year` YEAR,
	`maab_no` INTEGER,
	`member_id` INTEGER UNIQUE,
	`effectivity_date` DATE,
	`expiry_date` DATE,
	`location_particular` VARCHAR(255),
	`location_category` ENUM('Public Nursery', 'Private Nursery', 'Public Kinder', 'Private Kinder', 'Public Elementary School', 'Private Elementary School', 'Public High School', 'Private High School', 'Public Senior High School', 'Private Senior High School', 'Public Integrated School', 'Private Integrated School', 'Public College', 'Private College', 'Government Company/Organization', 'Private Company/Organization', 'Church', 'Red Cross 143', 'RCY', 'Brgy', 'LGU', 'MBD', 'Events', 'Training', 'Company/Organization Training', 'Individual', 'Walk-In'),
	`municipality` VARCHAR(255),
	`district` VARCHAR(255),
	`OR_num` INTEGER,
	`OR_date` DATE,
	`paid` BOOLEAN DEFAULT false,
	`remarks` TEXT(65535),
	`origin` ENUM('Chapter', 'Dasmarinas', 'Silang'),
	`count_in_group` INTEGER COMMENT 'count of this record in the same group ex. school. idk how to use this yet',
	`id_received` BOOLEAN COMMENT 'for platinum cards',
	`declared` BOOLEAN,
	`tags` ENUM('late-declare', 'overage', 'underage'),
	`declaration_date` DATE COMMENT 'if declared. overwrite this field everytime declaration button is clicked',
	PRIMARY KEY(`transaction_no`)
);


CREATE TABLE `inventory` (
	`inv_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	`maab_category` ENUM('Classic', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Enhanced Platinum', 'Senior', 'Senior+'),
	`maab_no` VARCHAR(255),
	`used` BOOLEAN,
	`remarks` TEXT(65535),
	`allocated_to` ENUM('Chapter', 'Dasmarinas', 'Silang'),
	PRIMARY KEY(`inv_id`)
);


CREATE TABLE `maab_claims` (
	`claim_id` INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
	PRIMARY KEY(`claim_id`)
);

CREATE TABLE ifgms.otp_verifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    otp VARCHAR(6) NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE `members_info`
ADD FOREIGN KEY(`member_id`) REFERENCES `membership_records`(`member_id`)
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `membership_records`
ADD FOREIGN KEY(`maab_no`) REFERENCES `inventory`(`inv_id`)
ON UPDATE NO ACTION ON DELETE NO ACTION;
