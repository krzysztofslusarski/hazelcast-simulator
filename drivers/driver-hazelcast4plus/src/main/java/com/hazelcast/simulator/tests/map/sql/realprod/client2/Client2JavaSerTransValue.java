package com.hazelcast.simulator.tests.map.sql.realprod.client2;

import com.hazelcast.nio.serialization.Portable;
import com.hazelcast.nio.serialization.PortableReader;
import com.hazelcast.nio.serialization.PortableWriter;

import java.io.IOException;
import java.io.Serializable;
import java.math.BigDecimal;

public class Client2JavaSerTransValue implements Serializable {
    public BigDecimal LogTranAmount;
    public BigDecimal LogTranStmtBal;
    public Integer LogTranRecNum;
    public Integer LogTranBatch;
    public String LogRecordType;
}
