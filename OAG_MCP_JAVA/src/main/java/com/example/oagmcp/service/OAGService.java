package com.example.oagmcp.service;

import com.example.oagmcp.logic.OAGLogic;
import com.example.oagmcp.vo.OAGVO;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/oag")
public class OAGService {

    private final OAGLogic logic;

    public OAGService(OAGLogic logic) {
        this.logic = logic;
    }

    @RequestMapping(value = "/retrieve-context", method = RequestMethod.POST)
    public OAGVO.RetrieveResponse retrieveContext(@RequestBody OAGVO.RetrieveRequest request) {
        return logic.retrieveContext(request);
    }
}
