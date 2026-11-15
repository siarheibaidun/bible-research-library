# Multilingual vector Bible search

The semantic index embeds overlapping passage windows from all five editions in the unified Bible snapshot: Russian Synodal, King James, Dutch 1917, Hebrew/Aramaic WLC and Greek UGNT. The model is `intfloat/multilingual-e5-small` at revision `614241f622f53c4eeff9890bdc4f31cfecc418b3` (MIT), using the publisher's 384-dimensional quantized ONNX variant. Text is embedded with `passage: ` and questions with `query: `, mean pooling and L2 normalization. Vectors are stored as float16 and evaluated in float32. The optional lexical prefix candidates are fused with semantic ranks; exact word search remains available separately.

Greek and Hebrew combining marks are removed **only for embedding**; the stored text and morphology are unchanged. Biblical Hebrew/Aramaic and Koine Greek retrieval quality is not independently established by the model's modern-language training. A similarity score is not a probability or theological judgment. Interpret and verify retrieved passages in context. Vector, keyword and multilingual retrieval are not exhaustive and cannot guarantee that every relevant passage is found.

## Search

```sh
python3 scripts/semantic_search.py --database /path/to/bible-research-search.sqlite3 \
 'Какие места говорят о воспитании и уважении родителей?' \
 --translation russyn --limit 30 --ru-term родител --ru-term детей

python3 scripts/semantic_search.py --database /path/to/bible-research-search.sqlite3 \
 'How should parents raise their children?' \
 --translation russyn --translation kjv --translation nld1917 --limit 30
```

A query in any supported language can retrieve candidates from any indexed edition. Optional `--ru-term`, `--en-term` and `--nl-term` are prefix terms used by the existing lexical index; they must be supplied explicitly and are not translated automatically. To inspect exact verses and cross-edition mappings, use `scripts/unified_search.py`. Search returns matched passage windows and similarity; it does not replace reference mapping or verify relationships.

The self-contained unified SQLite contains vectors, passage provenance, the inference model, tokenizer and runtime wheel archive. First use extracts checked assets into a temporary cache and installs the bundled wheels **without network access**. The current bundled runtime is built for Python 3.12, Linux x86-64 with AVX-512 VNNI; another environment needs a compatible runtime and model build. No model or API key is needed at query time. The original index/model asset checksums are stored in `semantic_metadata` and `semantic_assets`.

## Rebuild

Generate `vectors.sqlite3` from the exact unified Bible snapshot using the pinned model files. The builder checks SHA-256, tracks source checksums and can resume by passage/chunk. Long passages are split with overlap, and all content remains in the original verse index. `merge_vector_index.py` checks source identity, integrity, vector shape, existing passage IDs and verse coverage before creating a new database. The model archive must contain the checked ONNX model as `model.onnx`. The model and wheel assets should be obtained from their respective maintainers and their licenses retained. No model weights or generated datasets belong in this Git repository.

```sh
python3 scripts/build_vector_index.py --database /path/to/unified.sqlite3 \
 --model /path/to/model_qint8_avx512_vnni.onnx --tokenizer /path/to/tokenizer.json \
 --output /path/to/vectors.sqlite3 --threads 4
python3 scripts/merge_vector_index.py --bible /path/to/unified.sqlite3 \
 --vectors /path/to/vectors.sqlite3 --model /path/to/model_qint8_avx512_vnni.onnx \
 --model-archive /path/to/model.onnx.zip --tokenizer /path/to/tokenizer.json --wheels /path/to/runtime_wheels.zip \
 --model-license licenses/E5_MODEL_LICENSE.txt --output /path/to/bible-with-vectors.sqlite3
```

The reviewed model ONNX SHA-256 is `dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88`; tokenizer SHA-256 is `0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39`. Both are from the model's `onnx/` directory. Standard dependency versions and the platform-specific wheel filenames are recorded in the embedded wheel archive. Python wheel availability and dependency support may change.
