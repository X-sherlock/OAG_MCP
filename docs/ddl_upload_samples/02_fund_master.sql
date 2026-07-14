-- 测试目标：与 03_fund_business.sql 一起上传，验证跨文件外键解析。
CREATE TABLE fund_manager (
    manager_id BIGINT PRIMARY KEY,
    manager_code VARCHAR(32) NOT NULL UNIQUE,
    manager_name VARCHAR(120) NOT NULL,
    established_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE fund_product (
    fund_id BIGINT PRIMARY KEY,
    fund_code VARCHAR(16) NOT NULL UNIQUE,
    fund_name VARCHAR(160) NOT NULL,
    manager_id BIGINT NOT NULL,
    fund_type VARCHAR(40) NOT NULL,
    inception_date DATE,
    risk_level VARCHAR(16),
    CONSTRAINT fk_fund_manager
        FOREIGN KEY (manager_id) REFERENCES fund_manager(manager_id)
);
