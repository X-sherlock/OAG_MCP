-- 测试目标：单文件解析、中文注释、主键、唯一键、默认值和表级外键。
CREATE EXTERNALTABLE IF NOT EXISTS bigdata_ifund.customer (
    customer_id BIGINT PRIMARY KEY COMMENT '客户唯一标识',
    customer_code VARCHAR(32) NOT NULL UNIQUE COMMENT '客户编码',
    customer_name VARCHAR(120) NOT NULL COMMENT '客户名称',
    customer_level VARCHAR(20) NOT NULL DEFAULT 'NORMAL' COMMENT '客户等级',
    registered_at DATETIME NOT NULL COMMENT '注册时间'
) 
USING hudi
TBLPROPERTIES (
    'hoodie.table.name=xxx',
...
)
Location 'hdfs://xxx'
COMMENT='客户主数据';

drop table if EXISTS bigdata_ifund. customer_contact;
CREATE EXTERNALTABLE IF NOT EXISTS bigdata_ifund. customer_contact (
    contact_id BIGINT PRIMARY KEY COMMENT '联系方式唯一标识',
    customer_id BIGINT NOT NULL COMMENT '所属客户',
    contact_type VARCHAR(20) NOT NULL COMMENT '联系方式类型',
    contact_value VARCHAR(160) NOT NULL COMMENT '联系方式内容',
    is_primary BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否主要联系方式',
    CONSTRAINT uk_customer_contact UNIQUE (customer_id, contact_type, contact_value),
    CONSTRAINT fk_contact_customer
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户联系方式';
