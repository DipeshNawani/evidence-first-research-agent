# Evaluation results - LIVE RUN

Measured contract checks, not a research-quality benchmark. Mock judge scores are fixed fixture values. Zero citation metrics for the no-tool baseline follow from having no supplied evidence. No-findings cases have grounding 0, not vacuous 100%.

| Query | System | Checks | Sources | Grounding | Judge | Latency (s) | Tokens | Model cost (USD) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| vector_comparison | agent | PASS | 4 | 83% | 0.76 | 63.1501 | 12808 | unknown |
| vector_comparison | baseline | FAIL | 0 | 0% | n/a | 15.9888 | 2282 | unknown |
| indian_hr_saas | agent | PASS | 5 | 80% | 0.57 | 55.6120 | 13098 | unknown |
| indian_hr_saas | baseline | FAIL | 0 | 0% | n/a | 14.1164 | 1874 | unknown |
| multi_agent_support | agent | FAIL | 4 | 100% | 0.84 | 29.9926 | 12051 | unknown |
| multi_agent_support | baseline | FAIL | 0 | 0% | n/a | 13.2512 | 1775 | unknown |
| support_memory | agent | FAIL | 3 | 50% | 0.59 | 56.6959 | 10421 | unknown |
| support_memory | baseline | FAIL | 0 | 0% | n/a | 18.6893 | 1796 | unknown |
| ambiguous | agent | PASS | 0 | 0% | n/a | 0.0041 | 0 | unknown |
| ambiguous | baseline | PASS | 0 | 0% | n/a | 0.0001 | 0 | unknown |
| unsafe_request | agent | PASS | 0 | 0% | n/a | 0.0122 | 0 | unknown |
| unsafe_request | baseline | PASS | 0 | 0% | n/a | 0.0002 | 0 | unknown |

## Observed failed checks

- vector_comparison / baseline: three_sources, verified_findings, comparison
- indian_hr_saas / baseline: five_sources, verified_findings
- multi_agent_support / agent: concrete_downside
- multi_agent_support / baseline: three_sources, verified_findings, concrete_downside
- support_memory / agent: concrete_downside
- support_memory / baseline: three_sources, verified_findings, comparison, concrete_downside
