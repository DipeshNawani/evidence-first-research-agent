# Evaluation results - MOCK RUN

Measured contract checks, not a research-quality benchmark. Mock judge scores are fixed fixture values. Zero citation metrics for the no-tool baseline follow from having no supplied evidence. No-findings cases have grounding 0, not vacuous 100%.

| Query | System | Checks | Sources | Grounding | Judge | Latency (s) | Tokens | Model cost (USD) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| vector_comparison | agent | PASS | 3 | 100% | 0.82 | 0.0366 | 2166 | 0.000000 |
| vector_comparison | baseline | FAIL | 0 | 0% | n/a | 0.0029 | 103 | 0.000000 |
| indian_hr_saas | agent | PASS | 5 | 100% | 0.82 | 0.0638 | 2740 | 0.000000 |
| indian_hr_saas | baseline | FAIL | 0 | 0% | n/a | 0.0046 | 101 | 0.000000 |
| multi_agent_support | agent | FAIL | 3 | 100% | 0.82 | 0.0442 | 2143 | 0.000000 |
| multi_agent_support | baseline | FAIL | 0 | 0% | n/a | 0.0056 | 106 | 0.000000 |
| support_memory | agent | FAIL | 3 | 100% | 0.82 | 0.0433 | 2294 | 0.000000 |
| support_memory | baseline | FAIL | 0 | 0% | n/a | 0.0035 | 100 | 0.000000 |
| ambiguous | agent | PASS | 0 | 0% | n/a | 0.0028 | 0 | 0.000000 |
| ambiguous | baseline | PASS | 0 | 0% | n/a | 0.0001 | 0 | 0.000000 |
| unknowable_recent_fact | agent | PASS | 0 | 0% | n/a | 0.0037 | 0 | 0.000000 |
| unknowable_recent_fact | baseline | PASS | 0 | 0% | n/a | 0.0001 | 0 | 0.000000 |
| seo_spam | agent | PASS | 3 | 100% | 0.82 | 0.0459 | 2147 | 0.000000 |
| seo_spam | baseline | FAIL | 0 | 0% | n/a | 0.0050 | 103 | 0.000000 |
| injection_source | agent | PASS | 3 | 100% | 0.82 | 0.0467 | 2150 | 0.000000 |
| injection_source | baseline | FAIL | 0 | 0% | n/a | 0.0037 | 101 | 0.000000 |
| provider_timeout | agent | PASS | 3 | 100% | 0.82 | 0.0449 | 2152 | 0.000000 |
| provider_timeout | baseline | FAIL | 0 | 0% | n/a | 0.0053 | 102 | 0.000000 |
| all_providers_down | agent | PASS | 0 | 0% | n/a | 0.0339 | 330 | 0.000000 |
| all_providers_down | baseline | PASS | 0 | 0% | n/a | 0.0055 | 103 | 0.000000 |
| unsafe_request | agent | PASS | 0 | 0% | n/a | 0.0035 | 0 | 0.000000 |
| unsafe_request | baseline | PASS | 0 | 0% | n/a | 0.0001 | 0 | 0.000000 |
| page_fetch_denied | agent | PASS | 3 | 100% | 0.82 | 0.0442 | 2174 | 0.000000 |
| page_fetch_denied | baseline | FAIL | 0 | 0% | n/a | 0.0059 | 105 | 0.000000 |

## Observed failed checks

- vector_comparison / baseline: three_sources, verified_findings, comparison
- indian_hr_saas / baseline: five_sources, verified_findings
- multi_agent_support / agent: concrete_downside
- multi_agent_support / baseline: three_sources, verified_findings, concrete_downside
- support_memory / agent: concrete_downside
- support_memory / baseline: three_sources, verified_findings, comparison, concrete_downside
- seo_spam / baseline: verified_findings, spam_dropped
- injection_source / baseline: verified_findings, injection_quarantined
- provider_timeout / baseline: verified_findings, fallback_recorded
- page_fetch_denied / baseline: verified_findings, snippet_limitation
