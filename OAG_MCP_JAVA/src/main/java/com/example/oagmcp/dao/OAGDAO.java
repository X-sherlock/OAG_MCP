package com.example.oagmcp.dao;

import com.example.oagmcp.dao.entity.OAGEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface OAGDAO {

    int countEnabledDomain(@Param("domain") String domain);

    List<OAGEntity.OAGObject> searchObjects(@Param("domain") String domain,
                                            @Param("question") String question,
                                            @Param("normalized") String normalized,
                                            @Param("topK") int topK);

    List<OAGEntity.OAGAttribute> searchAttributes(@Param("domain") String domain,
                                                  @Param("question") String question,
                                                  @Param("normalized") String normalized,
                                                  @Param("topK") int topK);

    List<OAGEntity.OAGAttribute> listAttributesByNames(@Param("domain") String domain,
                                                       @Param("names") List<String> names);

    List<OAGEntity.OAGObject> listObjectsByIds(@Param("domain") String domain,
                                               @Param("objectIds") List<String> objectIds);

    List<OAGEntity.IntentProfile> listIntentProfiles(@Param("domain") String domain);

    List<OAGEntity.SkillCapability> listSkillCapabilities(@Param("domain") String domain);

    List<OAGEntity.GraphEdge> listGraphEdgesByNodeIds(@Param("domain") String domain,
                                                      @Param("nodeIds") List<String> nodeIds,
                                                      @Param("topK") int topK);
}
