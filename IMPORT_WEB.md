# WEB 66-book archive importer

This is an archive-specific import pilot for the supplied World English Bible USFM ZIP. It requires Python 3 and no external dependencies:

```sh
python3 scripts/import_web_archive.py /path/to/engwebp_usfm.zip output/web
python3 -m unittest discover -s tests -v
```

The output is 66 per-book JSON files and a manifest. Do not edit generated files by hand. The archive is read without extracting it; retain the original ZIP separately. This pilot was validated against SHA-256 `a93df5571009fed56f77e3ac1d3ce71c9a3a3df1486f7570cc7a8f823192fdba`. The ZIP's notice identifies the World English Bible and a 2020 stable text edition; its generation line refers to 30 October 2026. The exact download URL and download date of this copy were not independently established. The supplied notice says the WEB text is public domain and the name is a trademark; separately verify provenance and rights of the Strong's annotations before redistribution.

Each verse has normalized readable text, raw USFM, footnotes and cross-references as raw USFM, and Strong's annotations as they appear in the source. Note-only verses have empty text and retain the source note. Source headings and poetry formatting remain in raw USFM; heading text is not rendered in the verse text. Book introductions and chapter material before the first verse are retained as raw USFM in the book and chapter preambles. They are not parsed into structured notes or headings; the unchanged archive remains authoritative. This is not a lossless round-trip conversion.

The importer validates the 66 expected unique book IDs, sequential chapter and verse numbers, and unsupported markers. It fails on unknown structures instead of silently dropping them. These checks do not establish textual correctness, versification, or the accuracy of source annotations. It does not align English words to Hebrew or Greek. The manifest records source file and ZIP checksums but leaves versification and unverified download URL unset.
