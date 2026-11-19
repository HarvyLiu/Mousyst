# Mousyst website

Bilingual English / Traditional Chinese showcase and documentation, built with Astro.

Run `npm install`, then `npm run dev` in this directory. Use `npm run build` for a static production build and `npm run preview` to inspect it.

Run `npm test` to check swipe recognition and verify that the bundled word list and credits match the Windows app.

## Vercel

Import HarvyLiu/Mousyst and set **Root Directory** to `website`. Astro is the framework; build command is `npm run build`, output directory is `dist`. No environment variables are required. Vercel can deploy changes automatically from the selected Git branch.

The homepage keeps its illustrated keyboard scenes. Open `/demo/` to type in the browser with clicks or swipes. The demo processes strokes locally and writes only to its own editor. Downloads link to the latest GitHub release. The language switch preserves the current page and remembers the choice locally. Search filters guide titles in both languages.
