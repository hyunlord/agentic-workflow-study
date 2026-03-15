---
source_url: https://www.sbert.net/docs/sentence_transformer/usage/usage.html
title: Usage
domain: sentence_transformers
fetched_at: 2026-03-15T09:28:31+00:00
---

# Usage

- Usage
- [Edit on GitHub](https://github.com/huggingface/sentence-transformers/blob/main/docs/sentence_transformer/usage/usage.rst)

---

# Usage[ï](https://www.sbert.net/docs/sentence_transformer/usage/usage.html#usage "Link to this heading")

Characteristics of Sentence Transformer (a.k.a bi-encoder) models:

1. Calculates a **fixed-size vector representation (embedding)** given **texts or images**.
2. Embedding calculation is often **efficient**, embedding similarity calculation is **very fast**.
3. Applicable for a **wide range of tasks**, such as semantic textual similarity, semantic search, clustering, classification, paraphrase mining, and more.
4. Often used as a **first step in a two-step retrieval process**, where a Cross-Encoder (a.k.a. reranker) model is used to re-rank the top-k results from the bi-encoder.

Once you have [installed](https://www.sbert.net/docs/installation.html) Sentence Transformers, you can easily use Sentence Transformer models:

```
from sentence_transformers import SentenceTransformer

# 1. Load a pretrained Sentence Transformer model
model = SentenceTransformer("all-MiniLM-L6-v2")

# The sentences to encode
sentences = [
    "The weather is lovely today.",
    "It's so sunny outside!",
    "He drove to the stadium.",
]

# 2. Calculate embeddings by calling model.encode()
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

# 3. Calculate the embedding similarities
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.6660, 0.1046],
#         [0.6660, 1.0000, 0.1411],
#         [0.1046, 0.1411, 1.0000]])
```

Tasks and Advanced Usage

- [Computing Embeddings](https://www.sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html)
- [Semantic Textual Similarity](https://www.sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html)
- [Semantic Search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html)
- [Clustering](https://www.sbert.net/examples/sentence_transformer/applications/clustering/README.html)
- [Paraphrase Mining](https://www.sbert.net/examples/sentence_transformer/applications/paraphrase-mining/README.html)
- [Translated Sentence Mining](https://www.sbert.net/examples/sentence_transformer/applications/parallel-sentence-mining/README.html)
- [Image Search](https://www.sbert.net/examples/sentence_transformer/applications/image-search/README.html)
- [Embedding Quantization](https://www.sbert.net/examples/sentence_transformer/applications/embedding-quantization/README.html)
- [Creating Custom Models](https://www.sbert.net/docs/sentence_transformer/usage/custom_models.html)
- [Evaluation with MTEB](https://www.sbert.net/docs/sentence_transformer/usage/mteb_evaluation.html)
- [Speeding up Inference](https://www.sbert.net/docs/sentence_transformer/usage/efficiency.html)
