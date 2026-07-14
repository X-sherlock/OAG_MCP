-- 测试目标：PostgreSQL 方言、schema 限定名、COMMENT ON 和 ALTER TABLE 外键。
CREATE TABLE support.app_user (
    user_id BIGSERIAL PRIMARY KEY,
    login_name VARCHAR(64) NOT NULL UNIQUE,
    display_name VARCHAR(120) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE support.ticket (
    ticket_id BIGSERIAL PRIMARY KEY,
    requester_id BIGINT NOT NULL,
    subject VARCHAR(200) NOT NULL,
    priority VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE support.ticket_message (
    message_id BIGSERIAL PRIMARY KEY,
    ticket_id BIGINT NOT NULL,
    sender_id BIGINT NOT NULL,
    message_body TEXT NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE support.ticket
    ADD CONSTRAINT fk_ticket_requester
    FOREIGN KEY (requester_id) REFERENCES support.app_user(user_id);

ALTER TABLE support.ticket_message
    ADD CONSTRAINT fk_message_ticket
    FOREIGN KEY (ticket_id) REFERENCES support.ticket(ticket_id);

ALTER TABLE support.ticket_message
    ADD CONSTRAINT fk_message_sender
    FOREIGN KEY (sender_id) REFERENCES support.app_user(user_id);

COMMENT ON TABLE support.ticket IS '客服工单';
COMMENT ON COLUMN support.ticket.subject IS '工单主题';
COMMENT ON COLUMN support.ticket.priority IS '优先级';
COMMENT ON TABLE support.ticket_message IS '工单沟通记录';
