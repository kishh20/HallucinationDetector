from sentence_transformers import CrossEncoder
import numpy as np
import re


# =======================================
# Load NLI model
# =======================================

print("Loading NLI verifier...")

verifier = CrossEncoder(
    "cross-encoder/nli-deberta-v3-base",
    max_length=512
)

print("NLI verifier loaded!")


# =======================================
# Split context into sentences
# =======================================

def split_into_sentences(text):
    if not text:
        return []
    # Strip markdown headers, lists, numbers, and bullet points
    cleaned = re.sub(r"^[#*\-\d.]+\s*", "", str(text), flags=re.M)
    # Strip bold labels like '**Serve**:' or '**Nutritional Value**:'
    cleaned = re.sub(r"\*\*[^*]+?\*\*:\s*", "", cleaned)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", cleaned.strip())
    # Keep meaningful sentences
    sentences = [
        s.strip().strip("*#-_ ")
        for s in sentences
        if len(s.strip()) > 15
    ]
    return sentences


# =======================================
# Verify answer against evidence
# =======================================

def verify_answer(answer, contexts):
    if not contexts or not answer or not str(answer).strip():
        return {
            "supported": False,
            "entailment": 0.0,
            "contradiction": 0.0,
            "neutral": 100.0,
            "claims_total": 0,
            "claims_supported": 0,
            "claims_unsupported": 0,
            "unsupported_claims": [],
            "best_evidence": "",
        }

    # -----------------------------------
    # 1. Create evidence chunks (both sentences & paragraphs)
    # -----------------------------------
    evidence_chunks = []
    for context in contexts:
        if not context:
            continue
        c_clean = str(context).strip()
        sents = split_into_sentences(c_clean)
        evidence_chunks.extend(sents)
        if len(c_clean) > 35:
            evidence_chunks.append(c_clean[:550])

    if not evidence_chunks:
        return {
            "supported": False,
            "entailment": 0.0,
            "contradiction": 0.0,
            "neutral": 100.0,
            "claims_total": 0,
            "claims_supported": 0,
            "claims_unsupported": 0,
            "unsupported_claims": [],
            "best_evidence": "",
        }

    # Deduplicate while preserving order
    seen_chunks = set()
    unique_evidence = []
    for c in evidence_chunks:
        c_str = c.strip()
        if c_str and c_str not in seen_chunks:
            seen_chunks.add(c_str)
            unique_evidence.append(c_str)

    # -----------------------------------
    # 2. Extract claim sentences from answer
    # -----------------------------------
    ans_sentences = split_into_sentences(answer)
    if not ans_sentences:
        ans_sentences = [str(answer).strip()[:400]]

    # -----------------------------------
    # 3. Sentence-level NLI cross-examination
    # -----------------------------------
    sentence_evals = []
    best_overall_evidence = unique_evidence[0]
    highest_overall_entail = 0.0

    for sent in ans_sentences:
        pairs = [(chunk, sent) for chunk in unique_evidence]
        scores = verifier.predict(pairs, apply_softmax=True)
        scores = np.asarray(scores)
        # NLI Label indices: 0: contradiction, 1: entailment, 2: neutral
        best_chunk_idx = int(np.argmax(scores[:, 1]))
        max_entail = float(scores[best_chunk_idx, 1]) * 100.0
        contra_for_best = float(scores[best_chunk_idx, 0]) * 100.0
        neutral_for_best = float(scores[best_chunk_idx, 2]) * 100.0

        if max_entail > highest_overall_entail:
            highest_overall_entail = max_entail
            best_overall_evidence = unique_evidence[best_chunk_idx]

        # Contradiction check against the best matching chunk
        is_sent_supported = (max_entail >= 40.0 and max_entail > contra_for_best)
        is_sent_contradicted = (contra_for_best >= 60.0 and contra_for_best > max_entail)

        sentence_evals.append({
            "sentence": sent,
            "entailment": max_entail,
            "contradiction": contra_for_best,
            "neutral": neutral_for_best,
            "supported": is_sent_supported and not is_sent_contradicted,
            "contradicted": is_sent_contradicted,
            "best_chunk": unique_evidence[best_chunk_idx],
        })

    # -----------------------------------
    # 4. Aggregate metrics across all claims
    # -----------------------------------
    total_claims = len(sentence_evals)
    supported_claims = sum(1 for e in sentence_evals if e["supported"])
    unsupported_claims = [e["sentence"] for e in sentence_evals if not e["supported"]]
    unsupported_count = len(unsupported_claims)

    mean_entailment = float(np.mean([e["entailment"] for e in sentence_evals]))
    mean_contradiction = float(np.mean([e["contradiction"] for e in sentence_evals]))
    mean_neutral = float(np.mean([e["neutral"] for e in sentence_evals]))

    has_contradiction = any(e["contradicted"] for e in sentence_evals)
    support_ratio = (supported_claims / total_claims) if total_claims > 0 else 0.0

    # Verdict: supported if at least 70% of claims are verified and zero direct contradictions
    supported = bool(support_ratio >= 0.70 and not has_contradiction and mean_entailment >= 40.0)

    print("\nBest NLI Evidence:")
    print(best_overall_evidence)

    return {
        "supported": supported,
        "entailment": mean_entailment,
        "contradiction": mean_contradiction,
        "neutral": mean_neutral,
        "claims_total": total_claims,
        "claims_supported": supported_claims,
        "claims_unsupported": unsupported_count,
        "unsupported_claims": unsupported_claims,
        "best_evidence": best_overall_evidence,
    }