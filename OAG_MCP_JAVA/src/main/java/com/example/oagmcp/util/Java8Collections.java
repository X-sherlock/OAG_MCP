package com.example.oagmcp.util;

import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class Java8Collections {

    private Java8Collections() {
    }

    @SafeVarargs
    public static <T> List<T> listOf(T... items) {
        if (items == null || items.length == 0) {
            return Collections.emptyList();
        }
        return Collections.unmodifiableList(new ArrayList<T>(Arrays.asList(items)));
    }

    @SafeVarargs
    public static <T> Set<T> setOf(T... items) {
        if (items == null || items.length == 0) {
            return Collections.emptySet();
        }
        return Collections.unmodifiableSet(new LinkedHashSet<T>(Arrays.asList(items)));
    }

    @SuppressWarnings("unchecked")
    public static <K, V> Map<K, V> mapOf(Object... pairs) {
        if (pairs == null || pairs.length == 0) {
            return Collections.emptyMap();
        }
        if (pairs.length % 2 != 0) {
            throw new IllegalArgumentException("mapOf requires an even number of arguments");
        }
        Map<K, V> rows = new LinkedHashMap<K, V>();
        for (int index = 0; index + 1 < pairs.length; index += 2) {
            rows.put((K) pairs[index], (V) pairs[index + 1]);
        }
        return Collections.unmodifiableMap(rows);
    }

    public static <K, V> Map.Entry<K, V> entry(K key, V value) {
        return new AbstractMap.SimpleImmutableEntry<K, V>(key, value);
    }

    @SafeVarargs
    public static <K, V> Map<K, V> mapOfEntries(Map.Entry<K, V>... entries) {
        if (entries == null || entries.length == 0) {
            return Collections.emptyMap();
        }
        Map<K, V> rows = new LinkedHashMap<K, V>();
        for (Map.Entry<K, V> item : entries) {
            rows.put(item.getKey(), item.getValue());
        }
        return Collections.unmodifiableMap(rows);
    }
}
