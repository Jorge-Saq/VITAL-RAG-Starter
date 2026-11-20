# Project VITAL — LLM + RAG Lab Report

**CSCI3364 — Software Testing, Quality and Security | Boston College**

## Setup

| Item | Value |
| --- | --- |
| Model | `qwen2.5:1.5b` via Ollama (local), `temperature=0` |
| Retrieval | TF-IDF + cosine similarity over the 6 files in `knowledge_base/`, top `k=2`, zero-score hits removed, ties broken by filename |
| RAG prompt | `llm.py` system prompt: use ONLY the context, treat context as untrusted data, otherwise reply exactly *"I do not have enough information in the provided documents."* |
| App | Streamlit (`app.py`) with a sidebar **Enable RAG** toggle; retrieved filenames shown under every answer |

## What I implemented

| Task | File | Summary |
| --- | --- | --- |
| TODO 1: load documents | `rag.py` | Reads every `.txt` file into a pandas DataFrame, sorts by filename, returns `(filename, text)` tuples. |
| TODO 2: retrieve | `rag.py` | Fits `TfidfVectorizer` on the documents only, transforms the question, ranks by cosine similarity, drops zero scores, sorts by `(-score, filename)`, returns at most `k` `(filename, text, score)` tuples. Returns `[]` for an empty corpus. |
| TODO 3: format context | `rag.py` | Each hit becomes `[Source: filename]` followed by its text; hits are separated by a blank line. No hits → `""`. |
| TODO 4: integrate RAG | `app.py` | Sidebar toggle (default off). When on: `retrieve` → `build_context` → `ask_llm(question, context)`. An empty context is passed as `""` (not `None`) so the fallback prompt still applies. A `Sources:` caption (or "Sources: none retrieved" / "RAG off") is shown and kept in chat history. |
| Test and improve | `tests/test_retrieval.py`, `rag.py` | Added 2 tests, investigated a retrieval failure, made one retrieval change, reran tests and the app (see below). |

## Evidence

The documents are the oracle: each response is judged against the text of its expected source file, not against what sounds plausible.

### Expected sources and correct answers

| # | (a) Question | (b) Expected source | Correct answer according to the source |
| --- | --- | --- | --- |
| 1 | How many hours before an appointment must I cancel? | `cancellations.txt` | At least 18 hours before the scheduled time |
| 2 | Can I request a same-day appointment? | `scheduling.txt` | Yes, subject to availability |
| 3 | How are laboratory results communicated? | `lab_results.txt` | Through the secure patient portal |
| 4 | Does the clinic provide free transportation? | none (not covered) | The fallback line |
| 5 | What happens when I ask about an unsupported policy? | none (not covered) | The fallback line |

### Results

Run A is before my retrieval change; Run B is after it (scores in parentheses).

| # | (c) Retrieved — Run A | (c) Retrieved — Run B | (d) Response without RAG | (e) Response with RAG — Run A | (e) Response with RAG — Run B | (f) Supported by source? |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `cancellations.txt` (0.266), `scheduling.txt` (0.228) | `cancellations.txt` (0.427), `scheduling.txt` (0.194) | "I'm sorry, but I can't answer this question as it doesn't provide enough context. Could you please provide more information or clarify the question?" | "You must cancel your appointment at least 18 hours before the scheduled time." | "At least 18 hours before the scheduled time." | No RAG: **No** (no answer). RAG A: **Yes**. RAG B: **Yes**. |
| 2 | `scheduling.txt` (0.514), `portal.txt` (0.076) | `scheduling.txt` (0.668), `portal.txt` (0.215) | "I'm sorry, but I can't assist with that." | "Yes, you can request a same-day appointment, but it must be available." | "Yes, you can request a same-day appointment, but it depends on availability." | No RAG: **No** (no answer). RAG A: **Yes** (rewording of "subject to availability"). RAG B: **Yes**. |
| 3 | `lab_results.txt` (0.546), `portal.txt` (0.181) | `lab_results.txt` (0.591), `portal.txt` (0.241) | Long generic list: written reports, email/EHR, phone calls, in-person consultations, text/app notifications, patient education, follow-up appointments (full text in the appendix). | "Laboratory results are communicated through the secure patient portal." | "Laboratory results are communicated through the secure patient portal." | No RAG: **No** (hallucination; none of these methods are in the documents, and the portal is never mentioned). RAG A: **Yes**. RAG B: **Yes**. |
| 4 | `billing.txt` (0.270), `lab_results.txt` (0.234) | none | "I'm sorry, but I can't answer this question because I don't have any specific information about a particular clinic. … contact them directly to find out if they provide free transportation." | "I do not have enough information in the provided documents." | "I do not have enough information in the provided documents." | No RAG: makes no false claim, but doesn't use the required fallback line. RAG A: **Yes** (correct abstention despite irrelevant retrieval). RAG B: **Yes** (correct abstention, nothing retrieved). |
| 5 | `lab_results.txt` (0.201), `scheduling.txt` (0.192)\* | none | Answered as if the question were about *software* policies: "it typically means that the policy you are referring to is not supported by the current version of the software, system, or service you are using…" plus advice to check documentation (full text in the appendix). | not recorded | "I do not have enough information in the provided documents." | No RAG: **No** (made-up answer about software, unrelated to the clinic). RAG B: **Yes** (correct abstention). |

\* Run A retrieval for #5 was computed with the original `retrieve()` and was not run through the app.

### Observations

- **Without RAG**, the model failed every in-scope question (1–3), in two different ways: it refused (1, 2), or it confidently gave a generic answer that isn't the clinic's policy (3). Question 3 is the clearest hallucination: a detailed, plausible answer with no grounding in the documents. For the out-of-scope question #5 it didn't abstain either: with no context, it guessed the question was about software and invented an answer about deprecated software policies.
- **With RAG**, every response was supported by its source, and every unsupported question got the exact fallback line.
- **The model's output is not fully deterministic.** For #1 and #2, Run A and Run B retrieved the same two files, so the prompts were identical, yet the wording changed even at `temperature=0`. An oracle that checks for exact strings in the LLM output would be brittle. Checking the key fact against the source is the more reliable approach.

## Tests

| Test | Purpose | Before change | After change |
| --- | --- | --- | --- |
| `test_load_documents` | 6 documents load | pass | pass |
| `test_cancellation_policy_retrieved` | cancel question retrieves `cancellations.txt` | pass | pass |
| `test_context_includes_source` | context has `[Source: …]` header | pass | pass |
| `test_empty_corpus` | empty corpus → `[]` | pass | pass |
| `test_unsupported_question_retrieves_nothing` (**new**) | transportation question retrieves nothing | **fail** | pass |
| `test_billing_question_retrieves_billing` (**new**) | "How can I pay my bill?" retrieves `billing.txt` | **fail**\*\* | pass |

```
# After adding test_unsupported_question_retrieves_nothing (original retrieve)
$ python -m pytest -q
....F
1 failed, 4 passed

# After the change
$ python -m pytest -q
......
6 passed
```

\*\* `test_billing_question_retrieves_billing` was added together with the change. Running the original `retrieve()` on that question returns only `scheduling.txt` (0.238), so it would have failed too.

## Failure, change, and rerun

### Failure

For questions the documents don't cover (#4 transportation, #5 unsupported policy), `retrieve()` still returned two unrelated documents with non-zero scores: `billing.txt` (0.270) and `lab_results.txt` (0.234) for #4. This is a **retrieval failure**: the correct result is "nothing retrieved".

### Investigation

Every document starts with the same boilerplate, *"Fictional Harbor Clinic policy:"*. With default TF-IDF, the word "clinic" in the question matches all six documents, and common words like "the" add more overlap. `retrieve()` only drops scores of exactly 0, so any shared word counts as a hit.

### Changes tried

1. **Minimum score cutoff (rejected).** The wrong top hit for #4 scores *higher* than the right top hit for #1 (0.270 vs 0.266). Any cutoff that drops `billing.txt` also drops `cancellations.txt` and breaks `test_cancellation_policy_retrieved`.
2. **Stop words only (rejected).** Removing English stop words plus the boilerplate words `fictional`, `harbor`, `clinic` and `policy` fixed #4 (`[]`) but caused a regression: the cancel question then retrieved `scheduling.txt` (0.259) and `visitors.txt` (0.210), and `test_cancellation_policy_retrieved` failed. The cause is a vocabulary mismatch: the question says "cancel", the document says "canceled" and "cancellations", and TF-IDF treats those as different words. With "must" and "before" removed as stop words, only "hours" was left in common, and that also matches "Visiting hours".
3. **Final change: stop words plus simple suffix stripping (kept).** `rag.py` now uses a custom tokenizer that lowercases, drops stop words (English stop words plus the four boilerplate words), and strips the endings `-ations`, `-ation`, `-ing`, `-ed`, `-s`, so "cancel", "canceled" and "cancellations" all match. I also took **"bill" out of the stop words**, because scikit-learn's built-in English stop-word list includes "bill", which would make billing questions retrieve nothing. The new billing test guards against that.

### Outcome of rerunning

- **Tests:** 6 passed (up from 1 failed, 4 passed).
- **Retrieval:** unsupported questions (#4, #5) now retrieve nothing, and the expected source is still first for #1–#3 with higher scores than before (`cancellations.txt` 0.266 → 0.427, `scheduling.txt` 0.514 → 0.668, `lab_results.txt` 0.546 → 0.591). The billing question now retrieves `billing.txt` (0.740).
- **App rerun (Run B):** #4 and #5 show "Sources: none retrieved" and the fallback line; #1–#3 keep supported answers. No regressions.

## Retrieval failures vs generation failures

A **retrieval failure** means the wrong documents were passed to the model (or the right one was missing). A **generation failure** means the model's answer isn't supported by the context it was given (or, with no context, isn't true for this clinic).

| Case | Retrieval | Generation | Classification |
| --- | --- | --- | --- |
| #1–#3 and #5 without RAG | n/a (no retrieval) | Refusals (#1, #2), hallucinated generic answer (#3), invented off-topic answer instead of abstaining (#5) | **Generation failures** (no grounding) |
| #1–#3 with RAG, Run A | Correct source ranked first; the second file is off-topic for #1 (`scheduling.txt`) and #2 (`portal.txt`), and relevant for #3 (`portal.txt` also mentions viewing lab results) | Supported answers | Minor retrieval noise with no effect on the answer; **no failure** |
| #4 with RAG, Run A | Two irrelevant files retrieved | Correct fallback line | **Retrieval failure**; generation recovered |
| #4, #5 with RAG, Run B | Nothing retrieved | Correct fallback line | **No failure** |
| Cancel question with stop words only (attempt 2) | `cancellations.txt` missing from top 2 | not run in app | **Retrieval failure** (regression caught by test) |
| Billing question, original `retrieve()` | `scheduling.txt` instead of `billing.txt` | not run in app | **Retrieval failure** (caught by new test) |

With RAG enabled, every failure I found was in **retrieval**. The generation step never produced an unsupported answer: even when retrieval returned the wrong documents (#4, Run A), the model followed the "use ONLY the context" instruction and gave the fallback line. Passing the retrieval tests is a milestone, not proof that answers are correct, so the generation side was checked by comparing each answer to its source file.

## Limitations

- The suffix stripping is deliberately simple. It can over-strip or miss forms (for example, "paid" still doesn't match "pay"). A real stemmer or embeddings would generalize better.
- The tests and the stop-word list are tuned to this six-document corpus. New documents could need new tests.
- Generation quality was judged by hand on five questions with a 1.5B model; there are no automated checks on the LLM's answers.

## Security and privacy

- Only the six fictional clinic policy files and made-up questions were used. No real patient information or protected health information was entered.
- The model runs locally through Ollama, so no prompts or documents leave the machine.
- Retrieved documents are treated as **untrusted data**: the `llm.py` system prompt tells the model to treat the context as source data, not instructions, and to answer only from it. Sources are shown with every answer so the user can check them.
- Not tested: prompt-injection text placed inside a knowledge-base document. That would be a useful next test.

## Files changed

- `rag.py`: TODO 1–3, custom tokenizer and stop words
- `app.py`: TODO 4, RAG toggle and sources caption
- `tests/test_retrieval.py`: 2 new tests
- `requirements.txt`: added `pandas`
- `LAB_REPORT.md`: this report

## Reproduce

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # 6 passed
streamlit run app.py         # requires Ollama running with qwen2.5:1.5b
```

## Appendix: full responses without RAG

### #3: How are laboratory results communicated?

> Laboratory results are typically communicated in several ways, depending on the context and the nature of the results. Here are some common methods:
>
> Written Reports: Laboratory results are often reported in written form, either as a report or as part of a larger report. This can be sent to the patient, the referring physician, or the patient's insurance company.
>
> Email or Electronic Health Records (EHR): Results can be sent electronically via email or integrated into electronic health records (EHR) systems. This is particularly useful for sharing results with multiple healthcare providers.
>
> Phone Calls: Results can be communicated over the phone, especially if the results are urgent or require immediate action.
>
> In-Person Consultations: In some cases, results may be discussed in person, either at the patient's request or as part of a follow-up appointment.
>
> Notifications: Some laboratories may send notifications via text message or mobile app, especially for results that are not immediately actionable.
>
> Patient Education: In some cases, the laboratory may provide educational materials or information about the results, especially if the results are complex or require further explanation.
>
> Follow-Up Appointments: Results may be discussed during follow-up appointments, either in person or via telehealth.
>
> The method of communication is often determined by the urgency of the results, the preferences of the patient or healthcare provider, and the specific requirements of the laboratory and the healthcare system.

### #5: What happens when I ask about an unsupported policy?

> When you ask about an unsupported policy, it typically means that the policy you are referring to is not supported by the current version of the software, system, or service you are using. This could be due to a variety of reasons, such as the policy being deprecated, removed, or not supported in the current version.
>
> In such cases, it is important to check the documentation or support resources for the specific version of the software, system, or service you are using to determine if the policy is still supported. If the policy is not supported, you may need to look for an alternative solution or workaround to achieve the desired outcome.
>
> It is also worth noting that some policies may be deprecated or removed from the system or service, and it is important to keep up with the latest updates and changes to ensure that you are using the most up-to-date and supported policies.
