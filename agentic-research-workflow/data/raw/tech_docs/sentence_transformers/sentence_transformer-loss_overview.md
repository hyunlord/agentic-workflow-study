---
source_url: https://www.sbert.net/docs/sentence_transformer/loss_overview.html
title: Loss Overview
domain: sentence_transformers
fetched_at: 2026-03-15T09:28:39+00:00
---

# Loss Overview

- Loss Overview
- [Edit on GitHub](https://github.com/huggingface/sentence-transformers/blob/main/docs/sentence_transformer/loss_overview.md)

---

# Loss Overview[ï](https://www.sbert.net/docs/sentence_transformer/loss_overview.html#loss-overview "Link to this heading")

## Loss Table[ï](https://www.sbert.net/docs/sentence_transformer/loss_overview.html#loss-table "Link to this heading")

Loss functions play a critical role in the performance of your fine-tuned model. Sadly, there is no âone size fits allâ loss function. Ideally, this table should help narrow down your choice of loss function(s) by matching them to your data formats.

Note

You can often convert one training data format into another, allowing more loss functions to be viable for your scenario. For example, `(sentence_A, sentence_B) pairs` with `class` labels can be converted into `(anchor, positive, negative) triplets` by sampling sentences with the same or different classes.

**Legend:** Loss functions marked with `â` are commonly recommended default choices.

| Inputs | Labels | Appropriate Loss Functions |
| --- | --- | --- |
| `single sentences` | `class` | [`BatchAllTripletLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#batchalltripletloss) [`BatchHardSoftMarginTripletLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#batchhardsoftmargintripletloss) [`BatchHardTripletLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#batchhardtripletloss) [`BatchSemiHardTripletLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#batchsemihardtripletloss) |
| `single sentences` | `none` | [`ContrastiveTensionLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#contrastivetensionloss) [`DenoisingAutoEncoderLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#denoisingautoencoderloss) |
| `(anchor, anchor) pairs` | `none` | [`ContrastiveTensionLossInBatchNegatives`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#contrastivetensionlossinbatchnegatives) |
| `(damaged_sentence, original_sentence) pairs` | `none` | [`DenoisingAutoEncoderLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#denoisingautoencoderloss) |
| `(sentence_A, sentence_B) pairs` | `class` | [`SoftmaxLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#softmaxloss) |
| `(anchor, positive) pairs` | `none` | [`MultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#multiplenegativesrankingloss) â [`CachedMultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cachedmultiplenegativesrankingloss) â [`MegaBatchMarginLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#megabatchmarginloss) [`GISTEmbedLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#gistembedloss) [`CachedGISTEmbedLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cachedgistembedloss) |
| `(anchor, positive/negative) pairs` | `1 if positive, 0 if negative` | [`ContrastiveLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#contrastiveloss) [`OnlineContrastiveLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#onlinecontrastiveloss) |
| `(sentence_A, sentence_B) pairs` | `float similarity score between 0 and 1` | [`CoSENTLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cosentloss) [`AnglELoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#angleloss) [`CosineSimilarityLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cosinesimilarityloss) |
| `(anchor, positive, negative) triplets` | `none` | [`MultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#multiplenegativesrankingloss) â [`CachedMultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cachedmultiplenegativesrankingloss) â [`TripletLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#tripletloss) [`CachedGISTEmbedLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cachedgistembedloss) [`GISTEmbedLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#gistembedloss) |
| `(anchor, positive, negative_1, ..., negative_n)` | `none` | [`MultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#multiplenegativesrankingloss) â [`CachedMultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cachedmultiplenegativesrankingloss) â [`CachedGISTEmbedLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cachedgistembedloss) |

## Loss modifiers[ï](https://www.sbert.net/docs/sentence_transformer/loss_overview.html#loss-modifiers "Link to this heading")

These loss functions can be seen as *loss modifiers*: they work on top of standard loss functions, but apply those loss functions in different ways to try and instil useful properties into the trained embedding model.

For example, models trained with [`MatryoshkaLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#matryoshkaloss) produce embeddings whose size can be truncated without notable losses in performance, and models trained with [`AdaptiveLayerLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#adaptivelayerloss) still perform well when you remove model layers for faster inference.

| Texts | Labels | Appropriate Loss Functions |
| --- | --- | --- |
| `any` | `any` | [`MatryoshkaLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#matryoshkaloss) [`AdaptiveLayerLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#adaptivelayerloss) [`Matryoshka2dLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#matryoshka2dloss) |

## Regularization[ï](https://www.sbert.net/docs/sentence_transformer/loss_overview.html#regularization "Link to this heading")

These losses are designed to regularize the embedding space during training, encouraging certain properties in the learned embeddings. They can often be applied to any dataset configuration.

| Texts | Labels | Appropriate Loss Functions |
| --- | --- | --- |
| `any` | `none` | [`GlobalOrthogonalRegularizationLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#globalorthogonalregularizationloss) |

## Distillation[ï](https://www.sbert.net/docs/sentence_transformer/loss_overview.html#distillation "Link to this heading")

These loss functions are specifically designed to be used when distilling the knowledge from one model into another.
For example, when finetuning a small model to behave more like a larger & stronger one, or when finetuning a model to become multi-lingual.

| Texts | Labels | Appropriate Loss Functions |
| --- | --- | --- |
| `sentence` | `model sentence embeddings` | [`MSELoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#mseloss) |
| `(sentence_1, sentence_2, ..., sentence_N)` | `model sentence embeddings` | [`MSELoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#mseloss) |
| `(query, passage_one, passage_two)` | `gold_sim(query, passage_one) - gold_sim(query, passage_two)` | [`MarginMSELoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#marginmseloss) |
| `(query, positive, negative_1, ..., negative_n)` | `[gold_sim(query, positive) - gold_sim(query, negative_i) for i in 1..n]` | [`MarginMSELoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#marginmseloss) |
| `(query, positive, negative)` | `[gold_sim(query, positive), gold_sim(query, negative)]` | [`DistillKLDivLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#distillkldivloss) [`MarginMSELoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#marginmseloss) |
| `(query, positive, negative_1, ..., negative_n)` | `[gold_sim(query, positive), gold_sim(query, negative_i)...]` | [`DistillKLDivLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#distillkldivloss) [`MarginMSELoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#marginmseloss) |

## Commonly used Loss Functions[ï](https://www.sbert.net/docs/sentence_transformer/loss_overview.html#commonly-used-loss-functions "Link to this heading")

In practice, not all loss functions get used equally often. The most common scenarios are:

- `(anchor, positive) pairs` without any labels: [`MultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#multiplenegativesrankingloss) (a.k.a. InfoNCE or in-batch negatives loss) is commonly used to train the top performing embedding models. This data is often relatively cheap to obtain, and the models are generally very performant. [`CachedMultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cachedmultiplenegativesrankingloss) is often used to increase the batch size, resulting in superior performance.
- `(sentence_A, sentence_B) pairs` with a `float similarity score`: [`CosineSimilarityLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cosinesimilarityloss) is traditionally used a lot, though more recently [`CoSENTLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#cosentloss) and [`AnglELoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#angleloss) are used as drop-in replacements with superior performance.

## Custom Loss Functions[ï](https://www.sbert.net/docs/sentence_transformer/loss_overview.html#custom-loss-functions "Link to this heading")

Advanced users can create and train with their own loss functions. Custom loss functions only have a few requirements:

- They must be a subclass of [`torch.nn.Module`](https://docs.pytorch.org/docs/stable/generated/torch.nn.Module.html#torch.nn.Module "(in PyTorch v2.10)").
- They must have `model` as the first argument in the constructor.
- They must implement a `forward` method that accepts `sentence_features` and `labels`. The former is a list of tokenized batches, one element for each column. These tokenized batches can be fed directly to the `model` being trained to produce embeddings. The latter is an optional tensor of labels. The method must return a single loss value or a dictionary of loss components (component names to loss values) that will be summed to produce the final loss value. When returning a dictionary, the individual components will be logged separately in addition to the summed loss, allowing you to monitor the individual components of the loss.

To get full support with the automatic model card generation, you may also wish to implement:

- a `get_config_dict` method that returns a dictionary of loss parameters.
- a `citation` property so your work gets cited in all models that train with the loss.

Consider inspecting existing loss functions to get a feel for how loss functions are commonly implemented.
