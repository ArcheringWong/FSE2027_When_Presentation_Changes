# Data sources and distribution

## RCA100

RCA-100 version 1.1 is the cloud-native root-cause benchmark by Xidao Wen, Haibin Liu, Guiyang Liu, Cheng Zhang, Fang Situ, and Qi Zhou (2026), as credited in its supplied README. Source: [AgenticOpsEval RCA100](https://www.aiops.cn/gitlab/aiops-live-benchmark/agenticopseval/-/tree/master/RCA100).

The supplied data license is [Creative Commons Attribution-NonCommercial-ShareAlike 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). RCA100-derived metadata and records in this package remain subject to those terms, including attribution, noncommercial use, and ShareAlike. No additional restrictions on that licensed material are intended. The source README citation title is “RCA-100: A Chain-Reasoning Benchmark for Root Cause Analysis on Cloud-Native Microservices”.

## AIOps2025

The AIOps Challenge 2025 Dataset is credited as © 2025 Dan Pei in its supplied README and licensed under [Creative Commons Attribution-NonCommercial 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Source: [AgenticOpsEval AIOps2025](https://www.aiops.cn/gitlab/aiops-live-benchmark/agenticopseval/-/tree/master/AIOps2025). The two case illustrations are excerpts derived from this dataset. Attribution and noncommercial terms continue to apply.

## Modifications and boundaries

Study processing includes cohort selection, telemetry aggregation, entity normalization, bounded evidence selection, neutral permutation, model-response parsing, and statistical summarization. This review export selects the fields needed for those analyses and removes local paths, account information, provider-assigned request identifiers, and complete gold sets. It preserves recorded verdicts, scores, entity types, explicit mapping evidence, and cited evidence content. Original telemetry paths appearing inside a dataset log template are scientific input content, not author-machine paths.

The package contains study code and derived observations, not a redistribution of the complete source datasets. Dataset names in individual rows identify which source terms apply. The source datasets and their complete labels should be obtained through the linked maintainers under the applicable access terms. The study code does not grant new rights over third-party datasets. This review copy does not assign a new blanket license to the entire repository.
