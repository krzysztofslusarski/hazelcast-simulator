package com.hazelcast.simulator.hz;

import com.hazelcast.nio.serialization.compact.CompactReader;
import com.hazelcast.nio.serialization.compact.CompactSerializer;
import com.hazelcast.nio.serialization.compact.CompactWriter;
import org.jetbrains.annotations.NotNull;

public class IdentifiedDataWithLongCompactSerializer implements CompactSerializer<IdentifiedDataWithLongCompactPojo> {
    @NotNull
    @Override
    public IdentifiedDataWithLongCompactPojo read(@NotNull CompactReader compactReader) {
        IdentifiedDataWithLongCompactPojo pojo = new IdentifiedDataWithLongCompactPojo();
        pojo.value = compactReader.readInt64("value");
        pojo.numbers = new Integer[compactReader.readInt32("numbers-size")];
        for (int i = 0; i < pojo.numbers.length; i++) {
            if (compactReader.readBoolean("numbers-present-" + i)) {
                pojo.numbers[i] = compactReader.readInt32("numbers-" + i);
            }
        }
        return pojo;
    }

    @Override
    public void write(@NotNull CompactWriter compactWriter, @NotNull IdentifiedDataWithLongCompactPojo pojo) {
        compactWriter.writeInt64("value", pojo.value);
        compactWriter.writeInt32("numbers-size", pojo.numbers.length);
        for (int i = 0; i < pojo.numbers.length; i++) {
            Integer number = pojo.numbers[i];
            if (number != null) {
                compactWriter.writeBoolean("numbers-present-" + i, true);
                compactWriter.writeInt32("numbers-" + i, number);
            } else {
                compactWriter.writeBoolean("numbers-present-" + i, false);
            }
        }
    }
}
