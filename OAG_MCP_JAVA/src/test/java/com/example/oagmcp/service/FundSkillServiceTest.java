package com.example.oagmcp.service;

import com.example.oagmcp.logic.FundSkillLogic;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class FundSkillServiceTest {

    @Test
    void executeReadsBusinessPayloadFromDataWrapper() {
        FundSkillLogic logic = mock(FundSkillLogic.class);
        FundSkillService service = new FundSkillService(logic);
        Map<String, Object> businessInput = map("fund_code", "000001");
        Map<String, Object> businessOutput = map("success", true, "skill_id", "get_fund_profile_facts");
        Map<String, Object> request = map("data", businessInput);
        when(logic.execute(eq("get_fund_profile_facts"), anyMap())).thenReturn(businessOutput);

        Map<String, Object> response = service.execute("get_fund_profile_facts", request);

        assertEquals(businessOutput, response.get("data"));
        verify(logic).execute("get_fund_profile_facts", businessInput);
    }

    @Test
    void httpPostBindsDataWrapper() throws Exception {
        FundSkillLogic logic = mock(FundSkillLogic.class);
        FundSkillService service = new FundSkillService(logic);
        MockMvc mvc = MockMvcBuilders.standaloneSetup(service).build();
        when(logic.execute(eq("get_fund_profile_facts"), anyMap()))
                .thenReturn(map("success", true, "skill_id", "get_fund_profile_facts"));

        mvc.perform(post("/skills/get_fund_profile_facts")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"data\":{\"fund_code\":\"000001\"}}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.success").value(true));

        verify(logic).execute("get_fund_profile_facts", map("fund_code", "000001"));
    }

    @Test
    void httpPostAlsoAcceptsDirectBusinessJson() throws Exception {
        FundSkillLogic logic = mock(FundSkillLogic.class);
        FundSkillService service = new FundSkillService(logic);
        MockMvc mvc = MockMvcBuilders.standaloneSetup(service).build();
        when(logic.execute(eq("get_fund_profile_facts"), anyMap()))
                .thenReturn(map("success", true, "skill_id", "get_fund_profile_facts"));

        mvc.perform(post("/skills/get_fund_profile_facts")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"fund_code\":\"000001\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.success").value(true));

        verify(logic).execute("get_fund_profile_facts", map("fund_code", "000001"));
    }

    @Test
    void httpPostAlsoAcceptsInputWrapperAlias() throws Exception {
        FundSkillLogic logic = mock(FundSkillLogic.class);
        FundSkillService service = new FundSkillService(logic);
        MockMvc mvc = MockMvcBuilders.standaloneSetup(service).build();
        when(logic.execute(eq("get_fund_profile_facts"), anyMap()))
                .thenReturn(map("success", true, "skill_id", "get_fund_profile_facts"));

        mvc.perform(post("/skills/get_fund_profile_facts")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"input\":{\"fund_code\":\"000001\"}}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.success").value(true));

        verify(logic).execute("get_fund_profile_facts", map("fund_code", "000001"));
    }

    private static Map<String, Object> map(Object... values) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int index = 0; index < values.length; index += 2) {
            result.put(String.valueOf(values[index]), values[index + 1]);
        }
        return result;
    }
}
