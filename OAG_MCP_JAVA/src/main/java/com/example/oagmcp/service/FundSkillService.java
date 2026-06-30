package com.example.oagmcp.service;

import com.example.oagmcp.logic.FundSkillLogic;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
public class FundSkillService {

    private final FundSkillLogic logic;

    public FundSkillService(FundSkillLogic logic) {
        this.logic = logic;
    }

    @RequestMapping(
            value = {"/skills/{skillId}"}
    )
    @ResponseBody
    public Map<String, Object> execute(
            @PathVariable String skillId,
            @RequestBody(required = false) Map<String, Object> input) {
        Map<String, Object> output = new LinkedHashMap<>();
        Map<String, Object> data = unwrapInput(input);
        try {
            output.put("data", logic.execute(skillId, data));
        } catch (IllegalArgumentException ex) {
            output.put("data", logic.error(skillId, data, ex.getMessage()));
        } catch (Exception ex) {
            output.put("data", logic.error(skillId, data, "Skill execution failed: " + ex.getMessage()));
        }
        return output;
    }

    private Map<String, Object> unwrapInput(Map<String, Object> input) {
        if (input == null || input.isEmpty()) {
            return new LinkedHashMap<>();
        }
        for (String wrapperKey : new String[]{"data", "input", "requestData", "payload"}) {
            Object value = input.get(wrapperKey);
            if (value instanceof Map) {
                return copyMap((Map<?, ?>) value);
            }
        }
        return new LinkedHashMap<>(input);
    }

    private Map<String, Object> copyMap(Map<?, ?> source) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : source.entrySet()) {
            result.put(String.valueOf(entry.getKey()), entry.getValue());
        }
        return result;
    }
}
