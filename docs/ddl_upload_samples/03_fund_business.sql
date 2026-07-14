-- 测试目标：跨文件引用、复合唯一键、数值/日期字段和多张业务表。
CREATE TABLE fund_nav (
    nav_id BIGINT PRIMARY KEY,
    fund_id BIGINT NOT NULL,
    nav_date DATE NOT NULL,
    unit_nav DECIMAL(18,6) NOT NULL,
    accumulated_nav DECIMAL(18,6),
    daily_return DECIMAL(12,8),
    CONSTRAINT uk_fund_nav UNIQUE (fund_id, nav_date),
    CONSTRAINT fk_nav_fund
        FOREIGN KEY (fund_id) REFERENCES fund_product(fund_id)
);

CREATE TABLE fund_holding (
    holding_id BIGINT PRIMARY KEY,
    fund_id BIGINT NOT NULL,
    report_date DATE NOT NULL,
    security_code VARCHAR(32) NOT NULL,
    security_name VARCHAR(160) NOT NULL,
    market_value DECIMAL(20,2) NOT NULL,
    nav_ratio DECIMAL(10,6),
    CONSTRAINT uk_fund_holding UNIQUE (fund_id, report_date, security_code),
    CONSTRAINT fk_holding_fund
        FOREIGN KEY (fund_id) REFERENCES fund_product(fund_id)
);

CREATE TABLE fund_transaction (
    transaction_id BIGINT PRIMARY KEY,
    fund_id BIGINT NOT NULL,
    trade_date DATE NOT NULL,
    security_code VARCHAR(32) NOT NULL,
    trade_side VARCHAR(8) NOT NULL,
    quantity DECIMAL(20,4) NOT NULL,
    trade_amount DECIMAL(20,2) NOT NULL,
    CONSTRAINT fk_transaction_fund
        FOREIGN KEY (fund_id) REFERENCES fund_product(fund_id)
);
