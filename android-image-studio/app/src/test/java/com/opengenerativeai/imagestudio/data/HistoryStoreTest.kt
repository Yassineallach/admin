package com.opengenerativeai.imagestudio.data

import org.junit.Assert.assertEquals
import org.junit.Test

class HistoryStoreTest {
    @Test
    fun roundTrips() {
        val items = listOf(
            Generation("1", 10L, "m", "M", "a cat", JobStatus.SUCCEEDED, outputs = listOf("u1", "u2")),
            Generation("2", 20L, "m", "M", "", JobStatus.PENDING, requestId = "r"),
            Generation("3", 30L, "m", "M", "x", JobStatus.FAILED, error = "boom"),
        )
        assertEquals(items, HistoryStore.decode(HistoryStore.encode(items)))
    }
}
