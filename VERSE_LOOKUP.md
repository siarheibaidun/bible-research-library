# Look up a Bible verse

The lookup uses the JSON dataset generated from the World English Bible USFM archive. Python 3 is the only requirement.

From the repository root, first generate the dataset from your original ZIP:

```sh
python3 scripts/import_web_archive.py /path/to/engwebp_usfm.zip output/web
```

Then look up a verse:

```sh
python3 scripts/lookup_verse.py "John 3:16"
python3 scripts/lookup_verse.py "1 John 4:8"
python3 scripts/lookup_verse.py "GEN 1:1"
```

Full English book names and the USFM book codes are supported. Pass a different generated-data directory with `--data /path/to/dataset`. The command displays source notes and cross-references attached to the verse, source filename, and archive checksum. For an unsupported note format, it displays the original USFM instead. Note-only references are shown without inventing verse text. This is a single-verse lookup; it does not support passage ranges or alternate versifications.

The ZIP and generated files are not included in the repository. Preserve the original ZIP and see [IMPORT_WEB.md](IMPORT_WEB.md) for provenance, scope and limitations. The lookup does not interpret Strong's annotations or assert their accuracy. To run the tests:

```sh
python3 -m unittest discover -s tests -v
```
