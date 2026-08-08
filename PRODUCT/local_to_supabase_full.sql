-- SQL Script to REBUILD and copy Local Database to Supabase

DROP TABLE IF EXISTS access_logs CASCADE;
CREATE TABLE access_logs (
    access_date TEXT PRIMARY KEY,
    access_count INTEGER DEFAULT 0
);

DROP TABLE IF EXISTS site_content CASCADE;
CREATE TABLE site_content (
    id INTEGER PRIMARY KEY,
    about_us TEXT
);

DROP TABLE IF EXISTS app_config CASCADE;
CREATE TABLE app_config (
    id INTEGER PRIMARY KEY,
    config_updated_at BIGINT,
    last_updated_by TEXT
);

DROP TABLE IF EXISTS document_files CASCADE;
CREATE TABLE document_files (
    id INTEGER PRIMARY KEY,
    version_id INTEGER,
    filename TEXT,
    filepath TEXT,
    uploaded_at TEXT
);

DROP TABLE IF EXISTS document_versions CASCADE;
CREATE TABLE document_versions (
    id INTEGER PRIMARY KEY,
    model_checklist_id INTEGER,
    version_no TEXT,
    status TEXT DEFAULT 'Draft',
    is_latest INTEGER DEFAULT 1,
    content TEXT,
    reason TEXT,
    updated_at TEXT,
    approver_username TEXT,
    approved_at TEXT,
    uploader_username TEXT
);

DROP TABLE IF EXISTS model_checklist CASCADE;
CREATE TABLE model_checklist (
    id INTEGER PRIMARY KEY,
    model_id INTEGER,
    team TEXT,
    level_1 TEXT,
    level_2 TEXT,
    locked_by TEXT,
    locked_at BIGINT
);

DROP TABLE IF EXISTS master_checklist CASCADE;
CREATE TABLE master_checklist (
    id INTEGER PRIMARY KEY,
    team TEXT,
    level_1 TEXT,
    level_2 TEXT
);

DROP TABLE IF EXISTS models CASCADE;
CREATE TABLE models (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    model_type TEXT,
    customer TEXT,
    line TEXT,
    mp1st_date TEXT,
    mp1st_qty INTEGER,
    ship1st_date TEXT,
    ship1st_qty INTEGER,
    status TEXT DEFAULT 'Active',
    activate TEXT DEFAULT 'Yes',
    sort_order INTEGER DEFAULT 0
);

DROP TABLE IF EXISTS teams CASCADE;
CREATE TABLE teams (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    active TEXT DEFAULT 'Yes'
);

DROP TABLE IF EXISTS users CASCADE;
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    fullname TEXT,
    email TEXT,
    team TEXT,
    username TEXT UNIQUE,
    password TEXT,
    access_role TEXT
);

-- Inserting data for users
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (1, 'Admin', 'admin@domain.com', 'Others', 'ADMINPNX', 'adminpnx', 'Admin');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (183, 'Tung Pnx Admin', 'xuantung@pnx.com', 'Process DEV', 'tung', 'tung', 'Admin');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (184, 'Nguyen The Hoang', 'hoang@xxx.com', 'Process DEV', 'hoang', 'hoang', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (185, 'Bui Thi Thu', 'thu@xxx.com', 'OQA', 'thu', 'thu', 'OQA');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (186, 'Nguyen Duy Thanh', 'thanh@xxx.com', 'RnD', 'thanh', 'thanh', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (187, 'Nguyen Thi Thuy', 'thuy@xxx.com', 'App Insp', 'thuy', 'thuy', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (188, 'Dang Thu Anh', 'anh@xxx.com', 'CS', 'thuanh', 'thuanh', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (189, 'Bui Thi Ngoc Diep', 'diep@xxx.com', 'DQA', 'diep', 'diep', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (190, 'Nguyen Viet Anh', 'anh@xxx.com', 'Final Insp', 'vietanh', 'vietanh', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (191, 'Phan Thi Minh Ngoc', 'ngoc@xxx.com', 'Module Inte', 'ngoc', 'ngoc', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (192, 'Le Thu Hang', 'hang@xxx.com', 'Planning', 'hang', 'hang', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (193, 'Mai Trong Duong', 'duong@xxx.com', 'Production', 'duong', 'duong', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (194, 'Pham Thi Quynh', 'quynh@xxx.com', 'SQA', 'quynh', 'quynh', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (195, 'Vu Hong Quan', 'quan@xxx.com', 'Tech 1', 'quan', 'quan', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (196, 'Tran Dang Nam', 'nam@xxx.com', 'Tech 2', 'nam', 'nam', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (197, 'Nguyen Hai Long', 'long@xxx.com', 'RnD', 'long', 'long', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (198, 'Nguyen Quang Vinh', 'vinh@xxx.com', 'Process DEV', 'vinh', 'vinh', 'Viewer');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (199, 'Trinh Tat Thanh', 'thanh2@xxx.com', 'Process DEV', 'thanh2', 'thanh2', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (200, 'Vu Dinh Tu', 'tu@xxx.com', 'Others', 'tu', 'tu', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (201, 'Pham Xuan Tien', 'tien@xxx.com', 'Process DEV', 'tien', 'tien', 'Viewer');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (202, 'Aiden Do', 'truongdo@xxx.com', 'Production', 'truong', 'truong', 'Viewer');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (203, 'Cuong Beau', 'cuong@xxx.com', 'App Insp', 'cuong', 'cuong', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (204, 'Vu Van Thiem', 'thiem@xxx.com', 'App Insp', 'thiem', 'thiem', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (205, 'Nguyen Thi Doan Linh', 'linhtalinhtinh@xxx.com', 'Process DEV', 'linh', 'linh', 'Main PIC');
INSERT INTO users (id, fullname, email, team, username, password, access_role) VALUES (206, 'Ngo Manh Cuong', 'cuongngo@xxx.com', 'Process DEV', 'cuong2', 'cuong2', 'Main PIC');

-- Inserting data for teams
INSERT INTO teams (id, name, active) VALUES (431, 'RnD', 'Yes');
INSERT INTO teams (id, name, active) VALUES (432, 'Process DEV', 'Yes');
INSERT INTO teams (id, name, active) VALUES (433, 'Planning', 'Yes');
INSERT INTO teams (id, name, active) VALUES (434, 'Tech 1', 'Yes');
INSERT INTO teams (id, name, active) VALUES (435, 'Tech 2', 'Yes');
INSERT INTO teams (id, name, active) VALUES (436, 'Panel Inte', 'Yes');
INSERT INTO teams (id, name, active) VALUES (437, 'Module Inte', 'Yes');
INSERT INTO teams (id, name, active) VALUES (438, 'Production', 'Yes');
INSERT INTO teams (id, name, active) VALUES (439, 'Detection', 'Yes');
INSERT INTO teams (id, name, active) VALUES (440, 'Laser RP', 'Yes');
INSERT INTO teams (id, name, active) VALUES (441, 'App Insp', 'Yes');
INSERT INTO teams (id, name, active) VALUES (442, 'Final Insp', 'Yes');
INSERT INTO teams (id, name, active) VALUES (443, 'SQA', 'Yes');
INSERT INTO teams (id, name, active) VALUES (444, 'DQA', 'Yes');
INSERT INTO teams (id, name, active) VALUES (445, 'CS', 'Yes');
INSERT INTO teams (id, name, active) VALUES (446, 'OQA', 'Yes');
INSERT INTO teams (id, name, active) VALUES (447, 'Tech FA', 'Yes');

-- Inserting data for models
INSERT INTO models (id, name, status, model_type, customer, mp1st_date, mp1st_qty, ship1st_date, ship1st_qty, activate, sort_order, line) VALUES (41, 'LW245PUT', NULL, '245 V26', 'ASUS', '07/08/2026', 1000, '07/10/2026', 950, 'Yes', 0, 'CP104/ASSY104');
INSERT INTO models (id, name, status, model_type, customer, mp1st_date, mp1st_qty, ship1st_date, ship1st_qty, activate, sort_order, line) VALUES (42, 'LW315AQQ', NULL, '31.5 V24', 'ASÚ', '07/12/2026', 1500, '07/20/2026', 1480, 'Yes', 1, 'CP112/ASSY112');
INSERT INTO models (id, name, status, model_type, customer, mp1st_date, mp1st_qty, ship1st_date, ship1st_qty, activate, sort_order, line) VALUES (43, 'LW450CDM', NULL, '450 V26', 'DELL', '07/15/2026', 1400, '07/30/2026', 1350, 'Yes', 2, 'CP112/ASSY112');
INSERT INTO models (id, name, status, model_type, customer, mp1st_date, mp1st_qty, ship1st_date, ship1st_qty, activate, sort_order, line) VALUES (44, 'LW270PHD', NULL, '24 V25', 'LGE', '07/12/2026', 2000, '07/18/2026', 1950, 'Yes', 3, 'CP112/ASSY112');
INSERT INTO models (id, name, status, model_type, customer, mp1st_date, mp1st_qty, ship1st_date, ship1st_qty, activate, sort_order, line) VALUES (50, 'LW315EUY', NULL, '315 Dell', 'Dell', '07/31/2026', 3000, '08/05/2026', 2900, 'Yes', 4, 'CP112/ASSY112');

-- Inserting data for master_checklist
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (1, 'RnD', 'Document', 'Final DR minutes');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (2, 'RnD', 'Document', 'Model concept');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (3, 'RnD', 'Document', 'Setting Bo sang/ DLL version');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (4, 'RnD', 'Document', 'Pioneer BOM');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (5, 'RnD', 'Document', 'CAS/Product Spec');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (6, 'Process DEV', 'Document', 'CTQ standard');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (7, 'Process DEV', 'Document', 'Module Issue list');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (8, 'Process DEV', 'Document', 'New working guide');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (9, 'Process DEV', 'Document', 'QC Flow Chart');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (10, 'Process DEV', 'PDS', 'Product Approval');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (11, 'Planning', 'ERP systerm', 'Label Register');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (12, 'Planning', 'MP1st Plan', 'Input / Shipment');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (13, 'Tech 1', 'Document', 'CTP checklist');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (14, 'Tech 1', 'RMS', 'CTP for NSUS model');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (15, 'Tech 2', 'Model Register', 'Aging condition');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (16, 'Tech 2', 'Model Register', 'Bosang Setting File');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (17, 'Tech 2', 'Model Register', 'PTN List completed setup');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (18, 'Tech 2', 'Setup', 'Confirm Equipment new setup');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (19, 'Module Inte', 'Document', 'EMEMO update');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (20, 'Module Inte', 'MMD', 'CTQ Register');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (21, 'Production', 'Document', 'Material for MP 1st');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (22, 'Production', 'Document', 'Training Record (Module/Rework)');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (23, 'Production', 'Standard', 'New W/guide & I-guide register');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (24, 'CS', 'Customer Confirm', 'IIS');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (25, 'Detection', 'Document', 'Share PTN list');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (26, 'App Insp', 'Document', 'Training Record (App)');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (27, 'Final Insp', 'Document', 'Training Record (Final)');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (28, 'DQA', 'EC Repair', 'IPA RP');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (29, 'DQA', 'EC Repair', 'Laser RP');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (30, 'DQA', 'EC Repair', 'Module RP');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (31, 'DQA', 'EC Repair', 'Panel RP');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (32, 'DQA', 'Line EC', 'Line Modify');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (33, 'CS', 'Customer Confirm', 'Qualification Confirm');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (34, 'OQA', 'Inspection standard', 'APP standard');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (35, 'OQA', 'Inspection standard', 'FOS standard');
INSERT INTO master_checklist (id, team, level_1, level_2) VALUES (36, 'RnD', 'Document', 'LUT/GVC');

-- Inserting data for model_checklist
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (348, 41, 'RnD', 'Document', 'CAS/Product Spec', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (349, 41, 'RnD', 'Document', 'Final DR minutes', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (350, 41, 'RnD', 'Document', 'LUT/GVC', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (351, 41, 'RnD', 'Document', 'Model concept', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (352, 41, 'RnD', 'Document', 'Pioneer BOM', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (353, 41, 'RnD', 'Document', 'Setting Bo sang/ DLL version', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (354, 41, 'Process DEV', 'Document', 'CTQ standard', 'Admin PNX (tung)', '1785690055');
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (355, 41, 'Process DEV', 'Document', 'Module Issue list', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (356, 41, 'Process DEV', 'Document', 'New working guide', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (357, 41, 'Process DEV', 'Document', 'QC Flow Chart', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (358, 41, 'Process DEV', 'PDS', 'Product Approval', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (359, 41, 'Planning', 'ERP systerm', 'Label Register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (360, 41, 'Planning', 'MP1st Plan', 'Input / Shipment', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (361, 41, 'Tech 1', 'Document', 'CTP checklist', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (362, 41, 'Tech 1', 'RMS', 'CTP for NSUS model', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (363, 41, 'Tech 2', 'Model Register', 'Aging condition', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (364, 41, 'Tech 2', 'Model Register', 'Bosang Setting File', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (365, 41, 'Tech 2', 'Model Register', 'PTN List completed setup', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (366, 41, 'Tech 2', 'Setup', 'Confirm Equipment new setup', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (367, 41, 'Module Inte', 'Document', 'EMEMO update', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (368, 41, 'Module Inte', 'MMD', 'CTQ Register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (369, 41, 'Production', 'Document', 'Material for MP 1st', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (370, 41, 'Production', 'Document', 'Training Record (Module/Rework)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (371, 41, 'Production', 'Standard', 'New W/guide & I-guide register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (372, 41, 'Detection', 'Document', 'Share PTN list', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (373, 41, 'App Insp', 'Document', 'Training Record (App)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (374, 41, 'Final Insp', 'Document', 'Training Record (Final)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (375, 41, 'DQA', 'EC Repair', 'IPA RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (376, 41, 'DQA', 'EC Repair', 'Laser RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (377, 41, 'DQA', 'EC Repair', 'Module RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (378, 41, 'DQA', 'EC Repair', 'Panel RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (379, 41, 'DQA', 'Line EC', 'Line Modify', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (380, 41, 'CS', 'Customer Confirm', 'IIS', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (381, 41, 'CS', 'Customer Confirm', 'Qualification Confirm', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (382, 41, 'OQA', 'Inspection standard', 'APP standard', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (383, 41, 'OQA', 'Inspection standard', 'FOS standard', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (384, 42, 'RnD', 'Document', 'CAS/Product Spec', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (385, 42, 'RnD', 'Document', 'Final DR minutes', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (386, 42, 'RnD', 'Document', 'LUT/GVC', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (387, 42, 'RnD', 'Document', 'Model concept', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (388, 42, 'RnD', 'Document', 'Pioneer BOM', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (389, 42, 'RnD', 'Document', 'Setting Bo sang/ DLL version', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (390, 42, 'Process DEV', 'Document', 'CTQ standard', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (391, 42, 'Process DEV', 'Document', 'Module Issue list', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (392, 42, 'Process DEV', 'Document', 'New working guide', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (393, 42, 'Process DEV', 'Document', 'QC Flow Chart', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (394, 42, 'Process DEV', 'PDS', 'Product Approval', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (395, 42, 'Planning', 'ERP systerm', 'Label Register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (396, 42, 'Planning', 'MP1st Plan', 'Input / Shipment', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (397, 42, 'Tech 1', 'Document', 'CTP checklist', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (398, 42, 'Tech 1', 'RMS', 'CTP for NSUS model', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (399, 42, 'Tech 2', 'Model Register', 'Aging condition', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (400, 42, 'Tech 2', 'Model Register', 'Bosang Setting File', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (401, 42, 'Tech 2', 'Model Register', 'PTN List completed setup', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (402, 42, 'Tech 2', 'Setup', 'Confirm Equipment new setup', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (403, 42, 'Module Inte', 'Document', 'EMEMO update', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (404, 42, 'Module Inte', 'MMD', 'CTQ Register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (405, 42, 'Production', 'Document', 'Material for MP 1st', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (406, 42, 'Production', 'Document', 'Training Record (Module/Rework)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (407, 42, 'Production', 'Standard', 'New W/guide & I-guide register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (408, 42, 'Detection', 'Document', 'Share PTN list', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (409, 42, 'App Insp', 'Document', 'Training Record (App)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (410, 42, 'Final Insp', 'Document', 'Training Record (Final)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (411, 42, 'DQA', 'EC Repair', 'IPA RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (412, 42, 'DQA', 'EC Repair', 'Laser RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (413, 42, 'DQA', 'EC Repair', 'Module RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (414, 42, 'DQA', 'EC Repair', 'Panel RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (415, 42, 'DQA', 'Line EC', 'Line Modify', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (416, 42, 'CS', 'Customer Confirm', 'IIS', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (417, 42, 'CS', 'Customer Confirm', 'Qualification Confirm', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (418, 42, 'OQA', 'Inspection standard', 'APP standard', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (419, 42, 'OQA', 'Inspection standard', 'FOS standard', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (458, 50, 'RnD', 'Document', 'CAS/Product Spec', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (459, 50, 'RnD', 'Document', 'Final DR minutes', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (460, 50, 'RnD', 'Document', 'LUT/GVC', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (461, 50, 'RnD', 'Document', 'Model concept', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (462, 50, 'RnD', 'Document', 'Pioneer BOM', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (463, 50, 'RnD', 'Document', 'Setting Bo sang/ DLL version', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (464, 50, 'Process DEV', 'Document', 'CTQ standard', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (465, 50, 'Process DEV', 'Document', 'Module Issue list', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (466, 50, 'Process DEV', 'Document', 'New working guide', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (467, 50, 'Process DEV', 'Document', 'QC Flow Chart', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (468, 50, 'Process DEV', 'PDS', 'Product Approval', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (469, 50, 'Planning', 'ERP systerm', 'Label Register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (470, 50, 'Planning', 'MP1st Plan', 'Input / Shipment', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (471, 50, 'Tech 1', 'Document', 'CTP checklist', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (472, 50, 'Tech 1', 'RMS', 'CTP for NSUS model', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (473, 50, 'Tech 2', 'Model Register', 'Aging condition', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (474, 50, 'Tech 2', 'Model Register', 'Bosang Setting File', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (475, 50, 'Tech 2', 'Model Register', 'PTN List completed setup', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (476, 50, 'Tech 2', 'Setup', 'Confirm Equipment new setup', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (477, 50, 'Module Inte', 'Document', 'EMEMO update', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (478, 50, 'Module Inte', 'MMD', 'CTQ Register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (479, 50, 'Production', 'Document', 'Material for MP 1st', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (480, 50, 'Production', 'Document', 'Training Record (Module/Rework)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (481, 50, 'Production', 'Standard', 'New W/guide & I-guide register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (482, 50, 'Detection', 'Document', 'Share PTN list', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (483, 50, 'App Insp', 'Document', 'Training Record (App)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (484, 50, 'Final Insp', 'Document', 'Training Record (Final)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (485, 50, 'DQA', 'EC Repair', 'IPA RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (486, 50, 'DQA', 'EC Repair', 'Laser RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (487, 50, 'DQA', 'EC Repair', 'Module RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (488, 50, 'DQA', 'EC Repair', 'Panel RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (489, 50, 'DQA', 'Line EC', 'Line Modify', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (490, 50, 'CS', 'Customer Confirm', 'IIS', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (491, 50, 'CS', 'Customer Confirm', 'Qualification Confirm', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (492, 50, 'OQA', 'Inspection standard', 'APP standard', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (493, 50, 'OQA', 'Inspection standard', 'FOS standard', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (494, 43, 'RnD', 'Document', 'Model concept', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (495, 43, 'RnD', 'Document', 'Pioneer BOM', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (496, 43, 'RnD', 'Document', 'Setting Bo sang/ DLL version', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (497, 43, 'Process DEV', 'Document', 'CTQ standard', 'Admin PNX (tung)', '1785652530');
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (498, 43, 'Process DEV', 'Document', 'Module Issue list', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (499, 43, 'Process DEV', 'Document', 'New working guide', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (500, 43, 'Process DEV', 'Document', 'QC Flow Chart', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (501, 43, 'Process DEV', 'PDS', 'Product Approval', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (502, 43, 'Planning', 'ERP systerm', 'Label Register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (503, 43, 'Planning', 'MP1st Plan', 'Input / Shipment', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (504, 43, 'Tech 1', 'Document', 'CTP checklist', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (505, 43, 'Tech 1', 'RMS', 'CTP for NSUS model', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (506, 43, 'Tech 2', 'Model Register', 'Aging condition', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (507, 43, 'Tech 2', 'Model Register', 'Bosang Setting File', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (508, 43, 'Tech 2', 'Model Register', 'PTN List completed setup', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (509, 43, 'Tech 2', 'Setup', 'Confirm Equipment new setup', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (510, 43, 'Module Inte', 'Document', 'EMEMO update', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (511, 43, 'Module Inte', 'MMD', 'CTQ Register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (512, 43, 'Production', 'Document', 'Material for MP 1st', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (513, 43, 'Production', 'Document', 'Training Record (Module/Rework)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (514, 43, 'Production', 'Standard', 'New W/guide & I-guide register', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (515, 43, 'Detection', 'Document', 'Share PTN list', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (516, 43, 'App Insp', 'Document', 'Training Record (App)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (517, 43, 'Final Insp', 'Document', 'Training Record (Final)', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (518, 43, 'DQA', 'EC Repair', 'IPA RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (519, 43, 'DQA', 'EC Repair', 'Laser RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (520, 43, 'DQA', 'EC Repair', 'Module RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (521, 43, 'DQA', 'EC Repair', 'Panel RP', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (522, 43, 'DQA', 'Line EC', 'Line Modify', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (523, 43, 'CS', 'Customer Confirm', 'IIS', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (524, 43, 'CS', 'Customer Confirm', 'Qualification Confirm', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (525, 43, 'OQA', 'Inspection standard', 'APP standard', NULL, NULL);
INSERT INTO model_checklist (id, model_id, team, level_1, level_2, locked_by, locked_at) VALUES (526, 43, 'OQA', 'Inspection standard', 'FOS standard', NULL, NULL);

-- Inserting data for document_versions
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (167, 355, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (169, 359, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (170, 361, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (171, 363, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (172, 367, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (173, 369, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (174, 372, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (175, 375, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (176, 380, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (177, 373, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (180, 357, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (181, 374, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (182, 382, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (183, 348, 'V01', '', 'tung', 'Approved');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (193, 354, 'V01', '', 'tung', 'Pending');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (195, 354, 'V02', '', 'tung', 'Rejected');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (196, 354, 'V03', '', 'tung', 'Draft');
INSERT INTO document_versions (id, model_checklist_id, version_no, content, uploader_username, status) VALUES (198, 358, 'V01', '', 'tung', 'Draft');

-- Inserting data for site_content
INSERT INTO site_content (id, about_us) VALUES (1, '- This is QA Confirm Gate Web App
- Idea & Design by pnxtung@xxx.com');

-- Inserting data for access_logs
INSERT INTO access_logs (access_date, access_count) VALUES ('2026-08-08', 10);

-- Inserting data for app_config
INSERT INTO app_config (id, config_updated_at, last_updated_by) VALUES (1, 0, NULL);
INSERT INTO app_config (id, config_updated_at, last_updated_by) VALUES (2, 0, NULL);

