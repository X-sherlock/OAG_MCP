package com.example.oagmcp.dao;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

@Mapper
public interface FundSkillDAO {

    Map<String, Object> selectFund(@Param("fundCode") String fundCode,
                                   @Param("columns") List<String> columns);

    List<Map<String, Object>> selectFundsByName(@Param("fundName") String fundName,
                                                @Param("columns") List<String> columns);

    List<Map<String, Object>> selectFunds(@Param("fundCodes") List<String> fundCodes,
                                          @Param("columns") List<String> columns);
}
