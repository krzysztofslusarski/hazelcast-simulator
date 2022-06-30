package com.hazelcast.simulator.tests.map.sql.realprod.client2;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.hazelcast.nio.serialization.Portable;
import com.hazelcast.nio.serialization.PortableReader;
import com.hazelcast.nio.serialization.PortableWriter;

import java.io.IOException;
import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

public class Client2JavaSerAccountValue implements Serializable {
    public String LOG_ACCT_APP_CD;
    public String LOG_ACCT_BRANCH_CD;
    public BigDecimal LOG_ACCT_OPEN_BAL;
    public BigDecimal LOG_ACCT_CURR_BAL;
    public LocalDateTime LOG_TIMESTAMP;
    public LocalDateTime CACHE_TIMESTAMP;
}