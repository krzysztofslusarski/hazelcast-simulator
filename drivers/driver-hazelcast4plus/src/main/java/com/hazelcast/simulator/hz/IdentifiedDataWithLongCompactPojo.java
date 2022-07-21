/*
 * Copyright (c) 2008-2016, Hazelcast, Inc. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.hazelcast.simulator.hz;

/**
 * A sample IdentifiedDataSerializable object implementation.
 * With 20 integers in 'numbers' and a long in 'value'.
 */
public class IdentifiedDataWithLongCompactPojo {
    public Integer[] numbers;
    public Long value;

    public IdentifiedDataWithLongCompactPojo() {
    }

    public IdentifiedDataWithLongCompactPojo(Integer[] numbers, Long value) {
        this.numbers = numbers;
        this.value = value;
    }
}
