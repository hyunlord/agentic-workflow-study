---
source_url: https://www.sbert.net/docs/sentence_transformer/training_overview.html
title: Training Overview
domain: sentence_transformers
fetched_at: 2026-03-15T09:28:37+00:00
---

# Training Overview

- Training Overview
- [Edit on GitHub](https://github.com/huggingface/sentence-transformers/blob/main/docs/sentence_transformer/training_overview.md)

---

# Training Overview[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#training-overview "Link to this heading")

## Why Finetune?[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#why-finetune "Link to this heading")

Finetuning Sentence Transformer models often heavily improves the performance of the model on your use case, because each task requires a different notion of similarity. For example, given news articles:

- âApple launches the new iPadâ
- âNVIDIA is gearing up for the next GPU generationâ

Then the following use cases, we may have different notions of similarity:

- a model for **classification** of news articles as Economy, Sports, Technology, Politics, etc., should produce **similar embeddings** for these texts.
- a model for **semantic textual similarity** should produce **dissimilar embeddings** for these texts, as they have different meanings.
- a model for **semantic search** would **not need a notion for similarity** between two documents, as it should only compare queries and documents.

Also see [**Training Examples**](https://www.sbert.net/docs/sentence_transformer/training/examples.html) for numerous training scripts for common real-world applications that you can adopt.

## Training Components[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#training-components "Link to this heading")

Training Sentence Transformer models involves between 4 to 6 components:

[Model

Learn how to initialize the **model** for training.](https://www.sbert.net/docs/sentence_transformer/training_overview.html#model)
[Dataset

Learn how to prepare the **data** for training.](https://www.sbert.net/docs/sentence_transformer/training_overview.html#dataset)
[Loss Function

Learn how to prepare and choose a **loss** function.](https://www.sbert.net/docs/sentence_transformer/training_overview.html#loss-function)
[Training Arguments

Learn which **training arguments** are useful.](https://www.sbert.net/docs/sentence_transformer/training_overview.html#training-arguments)
[Evaluator

Learn how to **evaluate** during and after training.](https://www.sbert.net/docs/sentence_transformer/training_overview.html#evaluator)
[Trainer

Learn how to start the **training** process.](https://www.sbert.net/docs/sentence_transformer/training_overview.html#trainer)

## Model[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#model "Link to this heading")

Sentence Transformer models consist of a sequence of [Modules](https://www.sbert.net/docs/package_reference/sentence_transformer/models.html) or [Custom Modules](https://www.sbert.net/docs/sentence_transformer/usage/custom_models.html#advanced-custom-modules), allowing for a lot of flexibility. If you want to further finetune a SentenceTransformer model (e.g. it has a [modules.json file](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/main/modules.json)), then you donât have to worry about which modules are used:

```
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
```

But if instead you want to train from another checkpoint, or from scratch, then these are the most common architectures you can use:

Transformers

Most Sentence Transformer models use the [`Transformer`](https://www.sbert.net/docs/package_reference/sentence_transformer/models.html#sentence_transformers.models.Transformer "sentence_transformers.models.Transformer") and [`Pooling`](https://www.sbert.net/docs/package_reference/sentence_transformer/models.html#sentence_transformers.models.Pooling "sentence_transformers.models.Pooling") modules. The former loads a pretrained transformer model (e.g. [BERT](https://huggingface.co/google-bert/bert-base-uncased), [RoBERTa](https://huggingface.co/FacebookAI/roberta-base), [DistilBERT](https://huggingface.co/distilbert/distilbert-base-uncased), [ModernBERT](https://huggingface.co/answerdotai/ModernBERT-base), etc.) and the latter pools the output of the transformer to produce a single vector representation for each input sentence.

```
from sentence_transformers import models, SentenceTransformer

transformer = models.Transformer("google-bert/bert-base-uncased")
pooling = models.Pooling(transformer.get_word_embedding_dimension(), pooling_mode="mean")

model = SentenceTransformer(modules=[transformer, pooling])
```

This is the default option in Sentence Transformers, so itâs easier to use the shortcut:

```
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("google-bert/bert-base-uncased")
```

Tip

The strongest base models are often âencoder modelsâ, i.e. models that are trained to produce a meaningful token embedding for inputs. You can find strong candidates here:

- [fill-mask models](https://huggingface.co/models?pipeline_tag=fill-mask) - trained for token embeddings
- [sentence similarity models](https://huggingface.co/models?pipeline_tag=sentence-similarity) - trained for text embeddings
- [feature-extraction models](https://huggingface.co/models?pipeline_tag=feature-extraction) - trained for text embeddings

Consider looking for base models that are designed on your language and/or domain of interest. For example, [FacebookAI/xlm-roberta-base](https://huggingface.co/FacebookAI/xlm-roberta-base) will work better than [google-bert/bert-base-uncased](https://huggingface.co/google-bert/bert-base-uncased) for Turkish.

Static

Static Embedding models ([blogpost](https://huggingface.co/blog/static-embeddings)) use the [`StaticEmbedding`](https://www.sbert.net/docs/package_reference/sentence_transformer/models.html#sentence_transformers.models.StaticEmbedding "sentence_transformers.models.StaticEmbedding") module, and are encoder models that donât use slow transformers or attention mechanisms. For these models, computing embeddings is simply: given the input token, return the pre-computed token embedding. These models are orders of magnitude faster, but cannot capture complex semantics as token embeddings are computed separate from the context.

```
from sentence_transformers import models, SentenceTransformer
from tokenizers import Tokenizer

# Load any Tokenizer from Hugging Face
tokenizer = Tokenizer.from_pretrained("google-bert/bert-base-uncased")
# The `embedding_dim` is the dimensionality (size) of the token embeddings
static_embedding = StaticEmbedding(tokenizer, embedding_dim=512)

model = SentenceTransformer(modules=[static_embedding])
```

## Dataset[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#dataset "Link to this heading")

The `SentenceTransformerTrainer` trains and evaluates using [`datasets.Dataset`](https://huggingface.co/docs/datasets/main/en/package_reference/main_classes#datasets.Dataset "(in datasets vmain)") (one dataset) or [`datasets.DatasetDict`](https://huggingface.co/docs/datasets/main/en/package_reference/main_classes#datasets.DatasetDict "(in datasets vmain)") instances (multiple datasets, see also [Multi-dataset training](https://www.sbert.net/docs/sentence_transformer/training_overview.html#multi-dataset-training)).

Data on ð¤ Hugging Face Hub

If you want to load data from the [Hugging Face Datasets](https://huggingface.co/datasets), then you should use [`datasets.load_dataset()`](https://huggingface.co/docs/datasets/main/en/package_reference/loading_methods#datasets.load_dataset "(in datasets vmain)"):

```
from datasets import load_dataset

train_dataset = load_dataset("sentence-transformers/all-nli", "pair-class", split="train")
eval_dataset = load_dataset("sentence-transformers/all-nli", "pair-class", split="dev")

print(train_dataset)
"""
Dataset({
    features: ['premise', 'hypothesis', 'label'],
    num_rows: 942069
})
"""
```

Some datasets (including [sentence-transformers/all-nli](https://huggingface.co/datasets/sentence-transformers/all-nli)) require you to provide a âsubsetâ alongside the dataset name. `sentence-transformers/all-nli` has 4 subsets, each with different data formats: [pair](https://huggingface.co/datasets/sentence-transformers/all-nli/viewer/pair), [pair-class](https://huggingface.co/datasets/sentence-transformers/all-nli/viewer/pair-class), [pair-score](https://huggingface.co/datasets/sentence-transformers/all-nli/viewer/pair-score), [triplet](https://huggingface.co/datasets/sentence-transformers/all-nli/viewer/triplet).

Note

Many Hugging Face datasets that work out of the box with Sentence Transformers have been tagged with `sentence-transformers`, allowing you to easily find them by browsing to <https://huggingface.co/datasets?other=sentence-transformers>. We strongly recommend that you browse these datasets to find training datasets that might be useful for your tasks.

Local Data (CSV, JSON, Parquet, Arrow, SQL)

If you have local data in common file-formats, then you can load this data easily using [`datasets.load_dataset()`](https://huggingface.co/docs/datasets/main/en/package_reference/loading_methods#datasets.load_dataset "(in datasets vmain)"):

```
from datasets import load_dataset

dataset = load_dataset("csv", data_files="my_file.csv")
```

or:

```
from datasets import load_dataset

dataset = load_dataset("json", data_files="my_file.json")
```

Local Data that requires pre-processing

If you have local data that requires some extra pre-processing, my recommendation is to initialize your dataset using [`datasets.Dataset.from_dict()`](https://huggingface.co/docs/datasets/main/en/package_reference/main_classes#datasets.Dataset.from_dict "(in datasets vmain)") and a dictionary of lists, like so:

```
from datasets import Dataset

anchors = []
positives = []
# Open a file, do preprocessing, filtering, cleaning, etc.
# and append to the lists

dataset = Dataset.from_dict({
    "anchor": anchors,
    "positive": positives,
})
```

Each key from the dictionary will become a column in the resulting dataset.

### Dataset Format[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#dataset-format "Link to this heading")

It is important that your dataset format matches your loss function (or that you choose a loss function that matches your dataset format). Verifying whether a dataset format works with a loss function involves two steps:

1. If your loss function requires a *Label* according to the [Loss Overview](https://www.sbert.net/docs/sentence_transformer/loss_overview.html) table, then your dataset must have a **column named âlabelâ, âlabelsâ, âscoreâ or âscoresâ**. This column is automatically taken as the label.
2. All columns not named âlabelâ, âlabelsâ, âscoreâ or âscoresâ are considered *Inputs* according to the [Loss Overview](https://www.sbert.net/docs/sentence_transformer/loss_overview.html) table. The number of remaining columns must match the number of valid inputs for your chosen loss. The names of these columns are **irrelevant**, only the **order matters**.

For example, given a dataset with columns `["text1", "text2", "label"]` where the âlabelâ column has float similarity score between 0 and 1, we can use it with [`CoSENTLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#sentence_transformers.losses.CoSENTLoss "sentence_transformers.losses.CoSENTLoss"), [`AnglELoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#sentence_transformers.losses.AnglELoss "sentence_transformers.losses.AnglELoss"), and [`CosineSimilarityLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#sentence_transformers.losses.CosineSimilarityLoss "sentence_transformers.losses.CosineSimilarityLoss") because it:

1. has a âlabelâ column as is required for these loss functions.
2. has 2 non-label columns, exactly the amount required by these loss functions.

Be sure to re-order your dataset columns with [`Dataset.select_columns`](https://huggingface.co/docs/datasets/main/en/package_reference/main_classes#datasets.Dataset.select_columns "(in datasets vmain)") if your columns are not ordered correctly. For example, if your dataset has `["good_answer", "bad_answer", "question"]` as columns, then this dataset can technically be used with a loss that requires (anchor, positive, negative) triplets, but the `good_answer` column will be taken as the anchor, `bad_answer` as the positive, and `question` as the negative.

Additionally, if your dataset has extraneous columns (e.g. sample\_id, metadata, source, type), you should remove these with [`Dataset.remove_columns`](https://huggingface.co/docs/datasets/main/en/package_reference/main_classes#datasets.Dataset.remove_columns "(in datasets vmain)") as they will be used as inputs otherwise. You can also use [`Dataset.select_columns`](https://huggingface.co/docs/datasets/main/en/package_reference/main_classes#datasets.Dataset.select_columns "(in datasets vmain)") to keep only the desired columns.

## Loss Function[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#loss-function "Link to this heading")

Loss functions quantify how well a model performs for a given batch of data, allowing an optimizer to update the model weights to produce more favourable (i.e., lower) loss values. This is the core of the training process.

Sadly, there is no single loss function that works best for all use-cases. Instead, which loss function to use greatly depends on your available data and on your target task. See [Dataset Format](https://www.sbert.net/docs/sentence_transformer/training_overview.html#dataset-format) to learn what datasets are valid for which loss functions. Additionally, the [Loss Overview](https://www.sbert.net/docs/sentence_transformer/loss_overview.html) will be your best friend to learn about the options.

Most loss functions can be initialized with just the [`SentenceTransformer`](https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html#sentence_transformers.SentenceTransformer "sentence_transformers.SentenceTransformer") that youâre training, alongside some optional parameters, e.g.:

```
from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from sentence_transformers.losses import CoSENTLoss

# Load a model to train/finetune
model = SentenceTransformer("xlm-roberta-base")

# Initialize the CoSENTLoss
# This loss requires pairs of text and a float similarity score as a label
loss = CoSENTLoss(model)

# Load an example training dataset that works with our loss function:
train_dataset = load_dataset("sentence-transformers/all-nli", "pair-score", split="train")
"""
Dataset({
    features: ['sentence1', 'sentence2', 'label'],
    num_rows: 942069
})
"""
```

## Training Arguments[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#training-arguments "Link to this heading")

The [`SentenceTransformerTrainingArguments`](https://www.sbert.net/docs/package_reference/sentence_transformer/training_args.html#sentence_transformers.training_args.SentenceTransformerTrainingArguments "sentence_transformers.training_args.SentenceTransformerTrainingArguments") class can be used to specify parameters for influencing training performance as well as defining the tracking/debugging parameters. Although it is optional, it is heavily recommended to experiment with the various useful arguments.

Key Training Arguments for improving training performance

[`learning_rate`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.learning_rate)
[`lr_scheduler_type`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.lr_scheduler_type)
[`warmup_ratio`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.warmup_ratio)
[`num_train_epochs`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.num_train_epochs)
[`max_steps`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.max_steps)
[`per_device_train_batch_size`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.per_device_train_batch_size)
[`per_device_eval_batch_size`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.per_device_eval_batch_size)
[`auto_find_batch_size`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.auto_find_batch_size )
[`fp16`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.fp16)
[`bf16`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.bf16)
[`load_best_model_at_end`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.load_best_model_at_end)
[`metric_for_best_model`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.metric_for_best_model)
[`gradient_accumulation_steps`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.gradient_accumulation_steps)
[`gradient_checkpointing`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.gradient_checkpointing)
[`eval_accumulation_steps`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.eval_accumulation_steps)
[`optim`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.optim)
[`batch_sampler`](https://www.sbert.net/docs/package_reference/sentence_transformer/training_args.html#sentence_transformers.training_args.SentenceTransformerTrainingArguments)
[`multi_dataset_batch_sampler`](https://www.sbert.net/docs/package_reference/sentence_transformer/training_args.html#sentence_transformers.training_args.SentenceTransformerTrainingArguments)
[`prompts`](https://www.sbert.net/docs/package_reference/sentence_transformer/training_args.html#sentence_transformers.training_args.SentenceTransformerTrainingArguments)
[`router_mapping`](https://www.sbert.net/docs/package_reference/sentence_transformer/training_args.html#sentence_transformers.training_args.SentenceTransformerTrainingArguments)
[`learning_rate_mapping`](https://www.sbert.net/docs/package_reference/sentence_transformer/training_args.html#sentence_transformers.training_args.SentenceTransformerTrainingArguments)

  

Key Training Arguments for observing training performance

[`eval_strategy`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.eval_strategy)
[`eval_steps`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.eval_steps)
[`save_strategy`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.save_strategy)
[`save_steps`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.save_steps)
[`save_total_limit`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.save_total_limit)
[`report_to`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.report_to)
[`run_name`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.run_name)
[`log_level`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.log_level)
[`logging_steps`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.logging_steps)
[`push_to_hub`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.push_to_hub)
[`hub_model_id`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.hub_model_id)
[`hub_strategy`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.hub_strategy)
[`hub_private_repo`](https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments.hub_private_repo)

  

Here is an example of how [`SentenceTransformerTrainingArguments`](https://www.sbert.net/docs/package_reference/sentence_transformer/training_args.html#sentence_transformers.training_args.SentenceTransformerTrainingArguments "sentence_transformers.training_args.SentenceTransformerTrainingArguments") can be initialized:

```
args = SentenceTransformerTrainingArguments(
    # Required parameter:
    output_dir="models/mpnet-base-all-nli-triplet",
    # Optional training parameters:
    num_train_epochs=1,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    learning_rate=2e-5,
    warmup_ratio=0.1,
    fp16=True,  # Set to False if you get an error that your GPU can't run on FP16
    bf16=False,  # Set to True if you have a GPU that supports BF16
    batch_sampler=BatchSamplers.NO_DUPLICATES,  # losses that use "in-batch negatives" benefit from no duplicates
    # Optional tracking/debugging parameters:
    eval_strategy="steps",
    eval_steps=100,
    save_strategy="steps",
    save_steps=100,
    save_total_limit=2,
    logging_steps=100,
    run_name="mpnet-base-all-nli-triplet",  # Will be used in W&B if `wandb` is installed
)
```

## Evaluator[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#evaluator "Link to this heading")

You can provide the [`SentenceTransformerTrainer`](https://www.sbert.net/docs/package_reference/sentence_transformer/trainer.html#sentence_transformers.trainer.SentenceTransformerTrainer "sentence_transformers.trainer.SentenceTransformerTrainer") with an `eval_dataset` to get the evaluation loss during training, but it may be useful to get more concrete metrics during training, too. For this, you can use evaluators to assess the modelâs performance with useful metrics before, during, or after training. You can use both an `eval_dataset` and an evaluator, one or the other, or neither. They evaluate based on the `eval_strategy` and `eval_steps` [Training Arguments](https://www.sbert.net/docs/sentence_transformer/training_overview.html#training-arguments).

Here are the implemented Evaluators that come with Sentence Transformers:

| Evaluator | Required Data |
| --- | --- |
| [`BinaryClassificationEvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.BinaryClassificationEvaluator "sentence_transformers.evaluation.BinaryClassificationEvaluator") | Pairs with class labels. |
| [`EmbeddingSimilarityEvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.EmbeddingSimilarityEvaluator "sentence_transformers.evaluation.EmbeddingSimilarityEvaluator") | Pairs with similarity scores. |
| [`InformationRetrievalEvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.InformationRetrievalEvaluator "sentence_transformers.evaluation.InformationRetrievalEvaluator") | Queries (qid => question), Corpus (cid => document), and relevant documents (qid => set[cid]). |
| [`NanoBEIREvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.NanoBEIREvaluator "sentence_transformers.evaluation.NanoBEIREvaluator") | No data required. |
| [`MSEEvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.MSEEvaluator "sentence_transformers.evaluation.MSEEvaluator") | Source sentences to embed with a teacher model and target sentences to embed with the student model. Can be the same texts. |
| [`ParaphraseMiningEvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.ParaphraseMiningEvaluator "sentence_transformers.evaluation.ParaphraseMiningEvaluator") | Mapping of IDs to sentences & pairs with IDs of duplicate sentences. |
| [`RerankingEvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.RerankingEvaluator "sentence_transformers.evaluation.RerankingEvaluator") | List of `{'query': '...', 'positive': [...], 'negative': [...]}` dictionaries. |
| [`TranslationEvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.TranslationEvaluator "sentence_transformers.evaluation.TranslationEvaluator") | Pairs of sentences in two separate languages. |
| [`TripletEvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.TripletEvaluator "sentence_transformers.evaluation.TripletEvaluator") | (anchor, positive, negative) pairs. |

Additionally, [`SequentialEvaluator`](https://www.sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.evaluation.SequentialEvaluator "sentence_transformers.evaluation.SequentialEvaluator") should be used to combine multiple evaluators into one Evaluator that can be passed to the [`SentenceTransformerTrainer`](https://www.sbert.net/docs/package_reference/sentence_transformer/trainer.html#sentence_transformers.trainer.SentenceTransformerTrainer "sentence_transformers.trainer.SentenceTransformerTrainer").

Sometimes you donât have the required evaluation data to prepare one of these evaluators on your own, but you still want to track how well the model performs on some common benchmarks. In that case, you can use these evaluators with data from Hugging Face.

EmbeddingSimilarityEvaluator with STSb

```
from datasets import load_dataset
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator, SimilarityFunction

# Load the STSB dataset (https://huggingface.co/datasets/sentence-transformers/stsb)
eval_dataset = load_dataset("sentence-transformers/stsb", split="validation")

# Initialize the evaluator
dev_evaluator = EmbeddingSimilarityEvaluator(
    sentences1=eval_dataset["sentence1"],
    sentences2=eval_dataset["sentence2"],
    scores=eval_dataset["score"],
    main_similarity=SimilarityFunction.COSINE,
    name="sts-dev",
)
# You can run evaluation like so:
# results = dev_evaluator(model)
```

TripletEvaluator with AllNLI

```
from datasets import load_dataset
from sentence_transformers.evaluation import TripletEvaluator, SimilarityFunction

# Load triplets from the AllNLI dataset (https://huggingface.co/datasets/sentence-transformers/all-nli)
max_samples = 1000
eval_dataset = load_dataset("sentence-transformers/all-nli", "triplet", split=f"dev[:{max_samples}]")

# Initialize the evaluator
dev_evaluator = TripletEvaluator(
    anchors=eval_dataset["anchor"],
    positives=eval_dataset["positive"],
    negatives=eval_dataset["negative"],
    main_distance_function=SimilarityFunction.COSINE,
    name="all-nli-dev",
)
# You can run evaluation like so:
# results = dev_evaluator(model)
```

NanoBEIREvaluator

```
from sentence_transformers.evaluation import NanoBEIREvaluator

# Initialize the evaluator. Unlike most other evaluators, this one loads the relevant datasets
# directly from Hugging Face, so there's no mandatory arguments
dev_evaluator = NanoBEIREvaluator()
# You can run evaluation like so:
# results = dev_evaluator(model)
```

Tip

When evaluating frequently during training with a small `eval_steps`, consider using a tiny `eval_dataset` to minimize evaluation overhead. If youâre concerned about the evaluation set size, a 90-1-9 train-eval-test split can provide a balance, reserving a reasonably sized test set for final evaluations. After training, you can assess your modelâs performance using `trainer.evaluate(test_dataset)` for test loss or initialize a testing evaluator with `test_evaluator(model)` for detailed test metrics.

If you evaluate after training, but before saving the model, your automatically generated model card will still include the test results.

Warning

When using [Distributed Training](https://www.sbert.net/docs/sentence_transformer/training/distributed.html), the evaluator only runs on the first device, unlike the training and evaluation datasets, which are shared across all devices.

## Trainer[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#trainer "Link to this heading")

The [`SentenceTransformerTrainer`](https://www.sbert.net/docs/package_reference/sentence_transformer/trainer.html#sentence_transformers.trainer.SentenceTransformerTrainer "sentence_transformers.trainer.SentenceTransformerTrainer") is where all previous components come together. We only have to specify the trainer with the model, training arguments (optional), training dataset, evaluation dataset (optional), loss function, evaluator (optional) and we can start training. Letâs have a look at a script where all of these components come together:

```
from datasets import load_dataset
from sentence_transformers import (
    SentenceTransformer,
    SentenceTransformerTrainer,
    SentenceTransformerTrainingArguments,
    SentenceTransformerModelCardData,
)
from sentence_transformers.losses import MultipleNegativesRankingLoss
from sentence_transformers.training_args import BatchSamplers
from sentence_transformers.evaluation import TripletEvaluator

# 1. Load a model to finetune with 2. (Optional) model card data
model = SentenceTransformer(
    "microsoft/mpnet-base",
    model_card_data=SentenceTransformerModelCardData(
        language="en",
        license="apache-2.0",
        model_name="MPNet base trained on AllNLI triplets",
    )
)

# 3. Load a dataset to finetune on
dataset = load_dataset("sentence-transformers/all-nli", "triplet")
train_dataset = dataset["train"].select(range(100_000))
eval_dataset = dataset["dev"]
test_dataset = dataset["test"]

# 4. Define a loss function
loss = MultipleNegativesRankingLoss(model)

# 5. (Optional) Specify training arguments
args = SentenceTransformerTrainingArguments(
    # Required parameter:
    output_dir="models/mpnet-base-all-nli-triplet",
    # Optional training parameters:
    num_train_epochs=1,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    learning_rate=2e-5,
    warmup_ratio=0.1,
    fp16=True,  # Set to False if you get an error that your GPU can't run on FP16
    bf16=False,  # Set to True if you have a GPU that supports BF16
    batch_sampler=BatchSamplers.NO_DUPLICATES,  # MultipleNegativesRankingLoss benefits from no duplicate samples in a batch
    # Optional tracking/debugging parameters:
    eval_strategy="steps",
    eval_steps=100,
    save_strategy="steps",
    save_steps=100,
    save_total_limit=2,
    logging_steps=100,
    run_name="mpnet-base-all-nli-triplet",  # Will be used in W&B if `wandb` is installed
)

# 6. (Optional) Create an evaluator & evaluate the base model
dev_evaluator = TripletEvaluator(
    anchors=eval_dataset["anchor"],
    positives=eval_dataset["positive"],
    negatives=eval_dataset["negative"],
    name="all-nli-dev",
)
dev_evaluator(model)

# 7. Create a trainer & train
trainer = SentenceTransformerTrainer(
    model=model,
    args=args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    loss=loss,
    evaluator=dev_evaluator,
)
trainer.train()

# (Optional) Evaluate the trained model on the test set
test_evaluator = TripletEvaluator(
    anchors=test_dataset["anchor"],
    positives=test_dataset["positive"],
    negatives=test_dataset["negative"],
    name="all-nli-test",
)
test_evaluator(model)

# 8. Save the trained model
model.save_pretrained("models/mpnet-base-all-nli-triplet/final")

# 9. (Optional) Push it to the Hugging Face Hub
model.push_to_hub("mpnet-base-all-nli-triplet")
```

### Callbacks[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#callbacks "Link to this heading")

This Sentence Transformers trainer integrates support for various [`transformers.TrainerCallback`](https://huggingface.co/docs/transformers/main/en/main_classes/callback#transformers.TrainerCallback "(in transformers vmain)") subclasses, such as:

- [`WandbCallback`](https://huggingface.co/docs/transformers/main/en/main_classes/callback#transformers.integrations.WandbCallback "(in transformers vmain)") to automatically log training metrics to W&B if `wandb` is installed
- [`TensorBoardCallback`](https://huggingface.co/docs/transformers/main/en/main_classes/callback#transformers.integrations.TensorBoardCallback "(in transformers vmain)") to log training metrics to TensorBoard if `tensorboard` is accessible.
- [`CodeCarbonCallback`](https://huggingface.co/docs/transformers/main/en/main_classes/callback#transformers.integrations.CodeCarbonCallback "(in transformers vmain)") to track the carbon emissions of your model during training if `codecarbon` is installed.

  > - Note: These carbon emissions will be included in your automatically generated model card.

See the Transformers [Callbacks](https://huggingface.co/docs/transformers/main/en/main_classes/callback)
documentation for more information on the integrated callbacks and how to write your own callbacks.

## Multi-Dataset Training[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#multi-dataset-training "Link to this heading")

The top performing models are trained using many datasets at once. Normally, this is rather tricky, as each dataset has a different format. However, [`sentence_transformers.trainer.SentenceTransformerTrainer`](https://www.sbert.net/docs/package_reference/sentence_transformer/trainer.html#sentence_transformers.trainer.SentenceTransformerTrainer "sentence_transformers.trainer.SentenceTransformerTrainer") can train with multiple datasets without having to convert each dataset to the same format. It can even apply different loss functions to each of the datasets. The steps to train with multiple datasets are:

- Use a dictionary of [`Dataset`](https://huggingface.co/docs/datasets/main/en/package_reference/main_classes#datasets.Dataset "(in datasets vmain)") instances (or a [`DatasetDict`](https://huggingface.co/docs/datasets/main/en/package_reference/main_classes#datasets.DatasetDict "(in datasets vmain)")) as the `train_dataset` (and optionally also `eval_dataset`).
- (Optional) Use a dictionary of loss functions mapping dataset names to losses. Only required if you wish to use different loss function for different datasets.

Each training/evaluation batch will only contain samples from one of the datasets. The order in which batches are samples from the multiple datasets is defined by the [`MultiDatasetBatchSamplers`](https://www.sbert.net/docs/package_reference/sentence_transformer/sampler.html#sentence_transformers.training_args.MultiDatasetBatchSamplers "sentence_transformers.training_args.MultiDatasetBatchSamplers") enum, which can be passed to the [`SentenceTransformerTrainingArguments`](https://www.sbert.net/docs/package_reference/sentence_transformer/training_args.html#sentence_transformers.training_args.SentenceTransformerTrainingArguments "sentence_transformers.training_args.SentenceTransformerTrainingArguments") via `multi_dataset_batch_sampler`. Valid options are:

- `MultiDatasetBatchSamplers.ROUND_ROBIN`: Round-robin sampling from each dataset until one is exhausted. With this strategy, itâs likely that not all samples from each dataset are used, but each dataset is sampled from equally.
- `MultiDatasetBatchSamplers.PROPORTIONAL` (default): Sample from each dataset in proportion to its size. With this strategy, all samples from each dataset are used and larger datasets are sampled from more frequently.

This multi-task training has been shown to be very effective, e.g. [Huang et al.](https://huggingface.co/papers/2405.06932) employed [`MultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#sentence_transformers.losses.MultipleNegativesRankingLoss "sentence_transformers.losses.MultipleNegativesRankingLoss"), [`CoSENTLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#sentence_transformers.losses.CoSENTLoss "sentence_transformers.losses.CoSENTLoss"), and a variation on [`MultipleNegativesRankingLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#sentence_transformers.losses.MultipleNegativesRankingLoss "sentence_transformers.losses.MultipleNegativesRankingLoss") without in-batch negatives and only hard negatives to reach state-of-the-art performance on Chinese. They even applied [`MatryoshkaLoss`](https://www.sbert.net/docs/package_reference/sentence_transformer/losses.html#sentence_transformers.losses.MatryoshkaLoss "sentence_transformers.losses.MatryoshkaLoss") to allow the model to produce [Matryoshka Embeddings](https://www.sbert.net/examples/sentence_transformer/training/matryoshka/README.html).

Training on multiple datasets looks like this:

```
from datasets import load_dataset
from sentence_transformers import SentenceTransformer, SentenceTransformerTrainer
from sentence_transformers.losses import CoSENTLoss, MultipleNegativesRankingLoss, SoftmaxLoss

# 1. Load a model to finetune
model = SentenceTransformer("bert-base-uncased")

# 2. Load several Datasets to train with
# (anchor, positive)
all_nli_pair_train = load_dataset("sentence-transformers/all-nli", "pair", split="train[:10000]")
# (premise, hypothesis) + label
all_nli_pair_class_train = load_dataset("sentence-transformers/all-nli", "pair-class", split="train[:10000]")
# (sentence1, sentence2) + score
all_nli_pair_score_train = load_dataset("sentence-transformers/all-nli", "pair-score", split="train[:10000]")
# (anchor, positive, negative)
all_nli_triplet_train = load_dataset("sentence-transformers/all-nli", "triplet", split="train[:10000]")
# (sentence1, sentence2) + score
stsb_pair_score_train = load_dataset("sentence-transformers/stsb", split="train[:10000]")
# (anchor, positive)
quora_pair_train = load_dataset("sentence-transformers/quora-duplicates", "pair", split="train[:10000]")
# (query, answer)
natural_questions_train = load_dataset("sentence-transformers/natural-questions", split="train[:10000]")

# We can combine all datasets into a dictionary with dataset names to datasets
train_dataset = {
    "all-nli-pair": all_nli_pair_train,
    "all-nli-pair-class": all_nli_pair_class_train,
    "all-nli-pair-score": all_nli_pair_score_train,
    "all-nli-triplet": all_nli_triplet_train,
    "stsb": stsb_pair_score_train,
    "quora": quora_pair_train,
    "natural-questions": natural_questions_train,
}

# 3. Load several Datasets to evaluate with
# (anchor, positive, negative)
all_nli_triplet_dev = load_dataset("sentence-transformers/all-nli", "triplet", split="dev")
# (sentence1, sentence2, score)
stsb_pair_score_dev = load_dataset("sentence-transformers/stsb", split="validation")
# (anchor, positive)
quora_pair_dev = load_dataset("sentence-transformers/quora-duplicates", "pair", split="train[10000:11000]")
# (query, answer)
natural_questions_dev = load_dataset("sentence-transformers/natural-questions", split="train[10000:11000]")

# We can use a dictionary for the evaluation dataset too, but we don't have to. We could also just use
# no evaluation dataset, or one dataset.
eval_dataset = {
    "all-nli-triplet": all_nli_triplet_dev,
    "stsb": stsb_pair_score_dev,
    "quora": quora_pair_dev,
    "natural-questions": natural_questions_dev,
}

# 4. Load several loss functions to train with
# (anchor, positive), (anchor, positive, negative)
mnrl_loss = MultipleNegativesRankingLoss(model)
# (sentence_A, sentence_B) + class
softmax_loss = SoftmaxLoss(model, model.get_sentence_embedding_dimension(), 3)
# (sentence_A, sentence_B) + score
cosent_loss = CoSENTLoss(model)

# Create a mapping with dataset names to loss functions, so the trainer knows which loss to apply where.
# Note that you can also just use one loss if all of your training/evaluation datasets use the same loss
losses = {
    "all-nli-pair": mnrl_loss,
    "all-nli-pair-class": softmax_loss,
    "all-nli-pair-score": cosent_loss,
    "all-nli-triplet": mnrl_loss,
    "stsb": cosent_loss,
    "quora": mnrl_loss,
    "natural-questions": mnrl_loss,
}

# 5. Define a simple trainer, although it's recommended to use one with args & evaluators
trainer = SentenceTransformerTrainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    loss=losses,
)
trainer.train()

# 6. save the trained model and optionally push it to the Hugging Face Hub
model.save_pretrained("bert-base-all-nli-stsb-quora-nq")
model.push_to_hub("bert-base-all-nli-stsb-quora-nq")
```

## Deprecated Training[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#deprecated-training "Link to this heading")

Prior to the Sentence Transformers v3.0 release, models would be trained with the [`SentenceTransformer.fit()`](https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html#sentence_transformers.SentenceTransformer.fit "sentence_transformers.SentenceTransformer.fit") method and a [`DataLoader`](https://docs.pytorch.org/docs/stable/data.html#torch.utils.data.DataLoader "(in PyTorch v2.10)") of `InputExample`, which looked something like this:

```
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

# Define the model. Either from scratch of by loading a pre-trained model
model = SentenceTransformer("distilbert/distilbert-base-uncased")

# Define your train examples. You need more than just two examples...
train_examples = [
    InputExample(texts=["My first sentence", "My second sentence"], label=0.8),
    InputExample(texts=["Another pair", "Unrelated sentence"], label=0.3),
]

# Define your train dataset, the dataloader and the train loss
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.CosineSimilarityLoss(model)

# Tune the model
model.fit(train_objectives=[(train_dataloader, train_loss)], epochs=1, warmup_steps=100)
```

Since the v3.0 release, using [`SentenceTransformer.fit()`](https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html#sentence_transformers.SentenceTransformer.fit "sentence_transformers.SentenceTransformer.fit") is still possible, but it will initialize a [`SentenceTransformerTrainer`](https://www.sbert.net/docs/package_reference/sentence_transformer/trainer.html#sentence_transformers.trainer.SentenceTransformerTrainer "sentence_transformers.trainer.SentenceTransformerTrainer") behind the scenes. It is recommended to use the Trainer directly, as you will have more control via the [`SentenceTransformerTrainingArguments`](https://www.sbert.net/docs/package_reference/sentence_transformer/training_args.html#sentence_transformers.training_args.SentenceTransformerTrainingArguments "sentence_transformers.training_args.SentenceTransformerTrainingArguments"), but existing training scripts relying on [`SentenceTransformer.fit()`](https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html#sentence_transformers.SentenceTransformer.fit "sentence_transformers.SentenceTransformer.fit") should still work.

In case there are issues with the updated [`SentenceTransformer.fit()`](https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html#sentence_transformers.SentenceTransformer.fit "sentence_transformers.SentenceTransformer.fit"), you can also get exactly the old behaviour by calling [`SentenceTransformer.old_fit()`](https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html#sentence_transformers.SentenceTransformer.old_fit "sentence_transformers.SentenceTransformer.old_fit") instead, but this method is planned to be deprecated fully in the future.

## Best Base Embedding Models[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#best-base-embedding-models "Link to this heading")

The quality of your text embedding model depends on which transformer model you choose. Sadly we cannot infer from a better performance on e.g. the GLUE or SuperGLUE benchmark that this model will also yield better representations.

To test the suitability of transformer models, I use the [training\_nli\_v2.py](https://github.com/huggingface/sentence-transformers/blob/main/examples/sentence_transformer/training/nli/training_nli_v2.py) script and train on 560k (anchor, positive, negative)-triplets for 1 epoch with batch size 64. I then evaluate on 14 diverse text similarity tasks (clustering, semantic search, duplicate detection etc.) from various domains.

In the following table you find the performance for different models and their performance on this benchmark:

| Model | Performance (14 sentence similarity tasks) |
| --- | --- |
| [microsoft/mpnet-base](https://huggingface.co/microsoft/mpnet-base) | 60.99 |
| [nghuyong/ernie-2.0-en](https://huggingface.co/nghuyong/ernie-2.0-en) | 60.73 |
| [microsoft/deberta-base](https://huggingface.co/microsoft/deberta-base) | 60.21 |
| [roberta-base](https://huggingface.co/roberta-base) | 59.63 |
| [t5-base](https://huggingface.co/t5-base) | 59.21 |
| [bert-base-uncased](https://huggingface.co/bert-base-uncased) | 59.17 |
| [distilbert-base-uncased](https://huggingface.co/distilbert-base-uncased) | 59.03 |
| [nreimers/TinyBERT\_L-6\_H-768\_v2](https://huggingface.co/nreimers/TinyBERT_L-6_H-768_v2) | 58.27 |
| [google/t5-v1\_1-base](https://huggingface.co/google/t5-v1_1-base) | 57.63 |
| [nreimers/MiniLMv2-L6-H768-distilled-from-BERT-Large](https://huggingface.co/nreimers/MiniLMv2-L6-H768-distilled-from-BERT-Large) | 57.31 |
| [albert-base-v2](https://huggingface.co/albert-base-v2) | 57.14 |
| [microsoft/MiniLM-L12-H384-uncased](https://huggingface.co/microsoft/MiniLM-L12-H384-uncased) | 56.79 |
| [microsoft/deberta-v3-base](https://huggingface.co/microsoft/deberta-v3-base) | 54.46 |

## Comparisons with CrossEncoder Training[ï](https://www.sbert.net/docs/sentence_transformer/training_overview.html#comparisons-with-crossencoder-training "Link to this heading")

Training [`SentenceTransformer`](https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html#sentence_transformers.SentenceTransformer "sentence_transformers.SentenceTransformer") models is very similar as training [`CrossEncoder`](https://www.sbert.net/docs/package_reference/cross_encoder/cross_encoder.html#sentence_transformers.cross_encoder.CrossEncoder "sentence_transformers.cross_encoder.CrossEncoder") models, with some key differences:

- For [`CrossEncoder`](https://www.sbert.net/docs/package_reference/cross_encoder/cross_encoder.html#sentence_transformers.cross_encoder.CrossEncoder "sentence_transformers.cross_encoder.CrossEncoder") training, you can use (variably sized) lists of texts in a column. In [`SentenceTransformer`](https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html#sentence_transformers.SentenceTransformer "sentence_transformers.SentenceTransformer") training, you **cannot** use lists of inputs (e.g. texts) in a column of the training/evaluation dataset(s). In short: training with a variable number of negatives is not supported.

See the [Cross Encoder > Training Overview](https://www.sbert.net/docs/cross_encoder/training_overview.html) documentation for more details on training [`CrossEncoder`](https://www.sbert.net/docs/package_reference/cross_encoder/cross_encoder.html#sentence_transformers.cross_encoder.CrossEncoder "sentence_transformers.cross_encoder.CrossEncoder") models.
