# Versification mapping: research and edition checks

## Candidate

[CrossWire JSword Synodal mapping, pinned revision](https://github.com/crosswire/jsword/blob/a2c51f3c3a55416f3c991a67ef3d635c7ee55330/src/main/resources/org/crosswire/jsword/versification/Synodal.properties) identifies its mapping as Russian Synodal to English KJV. Its header states LGPL 2.1 or later and gives contributor attribution. It is a promising candidate for research, not a mapping that can be applied wholesale to our two editions. JSword's [mapper documentation](https://ftp.crosswire.org/jsword/javadoc/org/crosswire/jsword/versification/VersificationToKJVMapper.html) explains that its format supports ranges, titles and parts of verses. Its [versification mapper documentation](https://ftp.crosswire.org/jsword/javadoc/org/crosswire/jsword/versification/VersificationsMapper.html) discusses limitations of using KJV as an intermediary.

These pilot records were derived by checking the actual source texts, not by copying or distributing the JSword data file. If we redistribute or adapt that mapping file in the future, preserve its license and attribution and assess how its license applies to the planned distribution.

## Checks against the supplied archives

| Russian Synodal | WEB | Result of inspecting source texts |
| --- | --- | --- |
| Numbers 13:1 | Numbers 12:16 | Both describe leaving Hazeroth for Paran. |
| Jonah 2:1 | Jonah 1:17 | Both describe Jonah and the great fish. |
| Daniel 3:31 | Daniel 4:1 | Both contain Nebuchadnezzar's greeting. |
| Romans 14:24 | Romans 14:24 | Both contain the beginning of the doxology. |

The first three are consistent with the candidate's Synodal-to-KJV mapping. The Romans case is a material exception: the candidate maps the Russian reference to Romans 16:25 in KJV, while **both supplied archives place that text at 14:24**. WEB 16:25 is a note-only record about the alternative placement, not the target verse text. This shows why KJV references cannot be treated as WEB references without edition-specific validation.

Another issue is Psalm 3:1: the Russian source has the psalm heading as a numbered verse, while the English source places the heading outside numbered verse 1. A whole-verse-only model cannot express this faithfully. The importer retains the English chapter preamble as raw USFM; a future model needs explicit heading and verse-part references before mapping this case.

These four pairs were text-checked and added to the existing pilot. Many other entries, titles, partial verses, and disputed textual placements remain unreviewed. Source records are pinned by archive checksum. A generated manifest proves which archive it claims as source, not that generated output is unchanged.

## Next engineering step

Compare candidate system rules against both editions at scale, retain provenance and verification status per relation, and represent source headings, parts and missing material before enabling wider coverage. No default same-reference mapping should be asserted merely because both verse numbers exist.
