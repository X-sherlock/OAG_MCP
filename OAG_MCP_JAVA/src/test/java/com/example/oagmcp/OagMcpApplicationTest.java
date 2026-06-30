package com.example.oagmcp;

import com.example.oagmcp.logic.OAGLogic;
import com.example.oagmcp.dao.FundSkillDAO;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(properties = {
        "spring.autoconfigure.exclude=org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration,org.mybatis.spring.boot.autoconfigure.MybatisAutoConfiguration"
})
class OagMcpApplicationTest {

    @Autowired
    private OAGLogic logic;

    @MockBean
    private FundSkillDAO fundSkillDAO;

    @Test
    void springContextStartsWithYamlDaoAndNoDatabase() {
        assertThat(logic).isNotNull();
    }
}
