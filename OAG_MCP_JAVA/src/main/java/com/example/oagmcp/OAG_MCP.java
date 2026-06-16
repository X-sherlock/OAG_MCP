package com.example.oagmcp;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.example.oagmcp.dao")
public class OAG_MCP {

    public static void main(String[] args) {
        SpringApplication.run(OAG_MCP.class, args);
    }
}
