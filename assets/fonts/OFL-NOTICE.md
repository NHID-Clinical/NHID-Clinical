# Vendored fonts — SIL Open Font License 1.1

These TrueType fonts are bundled so the generated PDF suite matches the
NHID-Clinical website typography without a network dependency. Each is
licensed under the SIL Open Font License, Version 1.1 (https://openfontlicense.org).

- **Raleway** (SemiBold/Bold/ExtraBold) — © The Raleway Project Authors
  (https://github.com/impallari/Raleway). Display / headline face.
- **Inter** (Regular/SemiBold/Bold/Italic) — © The Inter Project Authors
  (https://github.com/rsms/inter). Body face.
- **IBM Plex Mono** (Regular/Medium) — © IBM Corp.
  (https://github.com/IBM/plex). Matches the website's monospace face.
- **JetBrains Mono** (Regular/Bold) — © JetBrains s.r.o.
  (https://github.com/JetBrains/JetBrainsMono). Technical / code face.

Source: Google Fonts (fonts.gstatic.com). No modifications made.

## Web fonts (`web/`)

The website's own faces, served from this origin instead of Google Fonts:

- **Space Grotesk** (variable, 300–700) — © The Space Grotesk Project Authors
  (https://github.com/floriankarsten/space-grotesk). Headings.
- **Inter** (variable, 100–900) — © The Inter Project Authors
  (https://github.com/rsms/inter). Body text.
- **IBM Plex Mono** (Regular/Medium) — © IBM Corp.
  (https://github.com/IBM/plex). Code and control IDs.

Latin and Latin Extended subsets in woff2, taken unmodified from the
@fontsource packages (npm), which repackage the Google Fonts releases.
`web/fonts.css` declares them.
