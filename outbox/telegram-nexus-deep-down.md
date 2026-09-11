Hi, a heads-up on ask_nexus_deep. Since 14:22 UTC today every deep investigation our agent starts ends "failed" after 78-101 s, six in a row, no answer. Job ids from get_deep_answer: bd0a3f97 (14:22), 9f21f27e (14:25), 777ff973 (15:10), 88f038c5 (15:12), 1e30ce1a (15:48), 2f4fef39 (15:50).

Each time the error is "The deep-answer run could not be completed. Retry ask_nexus_deep after retry_after_s seconds...", retryable true, retry_after_s 30. Retrying did not help, including a short, plain question. This morning the same channel answered in 2-3 minutes (8af1ab8c, ca20b16f).

As your CEO suggested, our agent takes its trading guidance from Nexus, so right now it gets none. Is the deep channel down on your side, and when do you expect it back? Until then, should agents ask trading questions through POST /api/v1/bounty/qa-agent/ask, as the error suggests? The details also went to you as a verification on #86.
