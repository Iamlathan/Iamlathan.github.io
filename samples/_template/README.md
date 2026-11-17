# One page sample template

`index.html` is the one page template. Its CSS is a base, not a finished look: every mockup gets its own colors, fonts and corner radius, and Northern Star Garage is the standard for polish, structure and detail. Until Lathan approves copying it over, the upgraded Northern Star lives only in the preview copy of the site. The copy in the lead mockup working folder may still be the older flat page, so do not copy its look.

## Its own look, the same system

The CSS has two `:root` blocks.

1. **This mockup's own look** (the first block). Change these per business: the grounds (`--bg` page, `--surface` raised cards, `--tint` bands, `--foot` footer), `--ink`, `--muted`, `--line`, one `--accent` for actions and key facts with its `--accent-hover` and a pale `--accent-soft` (the block behind photos and the step numbers), `--shadow` (the ink color as r g b, so shadows carry the page's own tint), `--texture` (a faint pattern on bands that fits the trade, or `none`), the fonts (`--font`, `--font-display`, `--display-weight`, with a matching Google Fonts link in the head) and the radius (`--r-ctl` buttons and fields, `--r-card` cards, `--r-photo` photo cards). Body text keeps 4.5 to 1 contrast on every ground.
2. **The system** (the second block and everything below it). Keep it the same on every mockup:
   - One spacing scale (`--s-1` to `--s-9`), one space between sections (`--sec`), one inside a band (`--band-pad`).
   - Three levels only: page (no shadow), raised (`--sh-1`: cards, photo cards, buttons) and floating (`--sh-3`: the card over a photo edge, the form panel). Light comes from the top left, so every shadow falls down and to the right. Things you can click lift on hover (`--sh-2`) and sink on press.
   - Rounded photo cards: every photo sits in a `figure class="photo"`, rounded by its wrapper. Full bleed backgrounds stay square.
   - Layered photos: wrap a photo card in `class="layer"` for the soft offset block behind it; the hero has a floating card (`class="float"`) over the photo edge.
   - Rhythm: open sections (`class="wrap sec"`) and contained bands (`class="band"` with a `wrap` inside) take turns. If deleting an OPTIONAL block puts two bands or two open sections side by side, swap the classes on the later one.
   - The same hover, focus and press on every button, link card and field. Hover rules sit inside `@media (hover:hover) and (pointer:fine)`. Motion is slow, plays once and is off for reduced motion; content shows without scripts.
   - Add your own touches in a third block at the end of the CSS (a frame shape, a pattern, a different hero layout), as long as they use the variables above.

## How to make a sample

1. Copy this folder to `samples/<slug>/`, where slug is the business name in lowercase with hyphens, for example `bradys-coffee-company`.
2. Put three photos beside `index.html` and replace `{{PHOTO_1}}`, `{{PHOTO_2}}` and `{{PHOTO_3}}` with their file names. The OPTIONAL photo strip takes three more (`{{PHOTO_4}}` to `{{PHOTO_6}}`); delete it when there are no more true photos to show.
3. Set this mockup's own look in the first `:root` block (see above). Then fill every `{{PLACEHOLDER}}` below. Search the file for `{{` when done; nothing may be left.
4. Delete every block marked `OPTIONAL` whose fact is unknown. Delete the whole block, never leave it half filled.
5. Choose ONE of the HOW IT WORKS or VISIT sections (both are in the file) and delete the other. Walk in shops and food use VISIT and delete CONTACT. Trades use HOW IT WORKS and CONTACT.
6. Keep one nav link per section still on the page.
7. Delete all HTML comments.
8. Write `photo-credits.txt` (file name, photographer, source page URL for each photo).
9. Open the page at 320, 390, 1024 and 1440 pixels wide and fix anything broken: no sideways scroll, the floating card clear of the text, the header name and Call button on one line at 320.

Finished examples for wording and how few facts are enough, all passing `check_mockup.py` on Nov 12 2026: `samples/cousin-garys-family-restaurant/` (fewest facts), `samples/main-street-coffee/` (a short menu) and `samples/johnson-garage/` (hours). All three use the older flat look; take their words, not their CSS.

## Footer mark

The footer ends with the Granite City Digital mark: a small 2 second logo build beside the words "Website by Granite City Digital", linking to https://granitecitydigital.me/. It plays once, with no sound, when it scrolls into view, then rests as the still logo. It never loops and never replays. If the video is blocked or fails, if the visitor asks for reduced motion, or if JavaScript is off, the still logo shows instead.

- The block has three parts, all already in `index.html`: the `.gcd` CSS under `/* footer mark */`, the `a class="gcd"` link in the footer, and the second script tag at the end of the page. Leave all three exactly as they are.
- The files are shared by every mockup and live in `samples/mark/`: `gcd-mark-2s.webm`, `gcd-mark-2s.mp4`, `gcd-mark-still.webp` and `gcd-mark-still.png` (about 110 KB together). The page points at them as `../mark/<file>`, so nothing extra goes in the slug folder. The folder is `mark`, not `_mark`: the live site skips folders that start with `_`, so `_mark` 404s.
- The footer credit line holds only `{{PHOTO_CREDIT_LINE}}`. The mark is the one Granite City credit in the footer; the top line stays as well.

## Placeholders

| Placeholder | What goes in it | Example |
| --- | --- | --- |
| `{{SLUG}}` | The sample's folder name, used in the og:image URL `https://granitecitydigital.me/samples/{{SLUG}}/hero.jpg`, so the hero photo must be named `hero.jpg` | bradys-coffee-company |
| `{{BUSINESS_NAME}}` | Full name, exactly as the business writes it | Brady's Coffee Company |
| `{{NAME_FIRST}}` | First part of the name, shown dark in the header | Brady's |
| `{{NAME_REST}}` | Rest of the name, shown grey | Coffee Company |
| `{{TRADE}}` | Plain trade words for the page title | Coffee and doughnuts |
| `{{TOWN}}` | Town | Mount Airy |
| `{{STATE}}` | State abbreviation | NC |
| `{{ADDRESS}}` | Street address only | 717 W Independence Blvd |
| `{{MAPS_LINK}}` | Google Maps search link for name and address | https://www.google.com/maps/search/?api=1&query=Brady%27s+Coffee+Company+717+W+Independence+Blvd+Mount+Airy+NC |
| `{{PHONE}}` | Phone, written for people | (336) 710-9776 |
| `{{PHONE_LINK}}` | Phone, 10 digits only, no spaces. The file already adds `tel:+1` in front | 3367109776 |
| `{{EMAIL}}` | Email (OPTIONAL) | |
| `{{HOURS}}` | Hours as text, lines joined with `<br>` (OPTIONAL) | Every day, 6am to 3pm |
| `{{HOURS_SCHEMA}}` | Hours for the JSON-LD block, for example `Mo-Su 06:00-15:00`. Delete the line if hours are unknown | |
| `{{SCHEMA_TYPE}}` | schema.org type | Restaurant, CafeOrCoffeeShop, Plumber |
| `{{META_DESCRIPTION}}` | One or two plain sentences: what, where, phone | |
| `{{HERO_LINE_1}}` | Headline first line, dark. About 22 characters or fewer | Coffee and doughnuts |
| `{{HERO_LINE_2}}` | Headline second line, grey | in Mount Airy. |
| `{{INTRO}}` | One or two sentences under the headline | |
| `{{FACT_1}}` to `{{FACT_3}}` | Short facts under the intro (OPTIONAL) | Dine in |
| `{{SECOND_BUTTON_TEXT}}` / `{{SECOND_BUTTON_LINK}}` | "Get directions" plus `{{MAPS_LINK}}`, or "Get a free quote" plus `#contact` | |
| `{{MENU_OR_SERVICES}}` | Last word of the top sample line: "menu" for food, "services" for everyone else | menu |
| `{{SERVICES_HEADING}}` | Heading of the services block, also used in the nav | What we serve, Services, The menu |
| `{{SERVICES_INTRO}}` | One line beside that heading | |
| `{{SERVICE_1}}` to `{{SERVICE_4}}` | One known service or menu group each. Delete extra rows | Coffee |
| `{{SERVICE_n_PRICE}}` | Price (OPTIONAL, only if published by the business) | |
| `{{SERVICE_n_NOTE}}` | One line about it (OPTIONAL) | |
| `{{SERVICES_NOTE}}` | One closing line under the list (OPTIONAL) | `<b>Call ahead</b> to ask about today's menu.` |
| `{{HOW_INTRO}}`, `{{STEP_1}}` to `{{STEP_3}}`, `{{STEP_n_NOTE}}` | How it works (OPTIONAL, trades only) | |
| `{{VISIT_INTRO}}` | One line for the Visit section | Find us on W Pine St in Mount Airy. |
| `{{AREA_TOWNS}}` / `{{AREA_EXTRA}}` | Towns served (OPTIONAL) | |
| `{{REVIEW_n}}`, `{{REVIEW_n_NAME}}`, `{{REVIEW_n_TOWN}}` | Do not use until Lathan approves review quotes: delete the REVIEWS block. Quoting a business's real reviews (Google or any other) on a lead mockup is not approved yet. The placeholders stay in the template only so older mockups and the checker are unaffected (OPTIONAL) | |
| `{{FAQ_n_Q}}` / `{{FAQ_n_A}}` | Questions with known answers (OPTIONAL) | |
| `{{FORM_EXAMPLE}}` | Placeholder text in the quote form (OPTIONAL, trades only) | |
| `{{PHOTO_1}}`, `{{PHOTO_2}}`, `{{PHOTO_3}}` | Photo file names: hero (wide), services, visit or how it works | hero.jpg |
| `{{PHOTO_4}}` to `{{PHOTO_6}}` | Photo strip file names (OPTIONAL). Portrait crops work best | strip-1.jpg |
| `{{PHOTO_1_ALT}}` to `{{PHOTO_6_ALT}}` | What the photo shows, plainly | A tray of glazed doughnuts |
| `{{PHOTO_CREDIT_LINE}}` | Credit sentence in the footer | Photos by Kari Shea and Annie Spratt on Unsplash, shown as examples. |

Set the `width` and `height` on each `<img>` to the photo's real pixel size.

## Rules

- Facts come only from the lead line or the business's own public page (its own site, its own ordering page, or its own Facebook page if it really loads). Directories, review sites and tourism pages do not count.
- Never invent reviews, ratings, prices, menu items, years in business, hours, owner names or claims. If a fact is unknown, delete the block.
- Food businesses can use plain trade words as services ("Coffee", "Doughnuts") when the lead says so, and nothing more specific than the facts support. "Call ahead" and "Find us at <address>" are fine.
- Keep the top line: "Sample site made for <business> by Granite City Digital." with the link to https://granitecitydigital.me/.
- Keep `<meta name="robots" content="noindex">`.
- Every mockup keeps the footer mark block unchanged: muted, plays once, still logo fallback. Its files live in `samples/mark/` and must publish together with the first mockup that uses them. The mark files total under 150 KB.
- Shared files use paths that work from `/samples/<slug>/`: `../../favicon.svg` and `../../apple-touch-icon.png`. Photos sit beside `index.html`.
- Photos: three, or six with the strip, free license (Unsplash or Pexels), about 1600 px wide, jpg, under about 400 KB each. Candid and generic. Never show a food or job the business is not known to offer as if it were theirs. No visible brand names or readable text in the photo.
- Brand rule (Lathan, Nov 4 2026): remove any brand that is not the lead's own from a mockup, then it may go live. Anything held for another reason waits for Lathan. Every photo and video in the folder, strays too, is checked for a readable brand, logo, product name, store name, vehicle badge or watermark that is not the lead's own. If one is found, swap that photo for a clean one (same source rules, same file name, credit updated) and recheck.
- Keep every Granite City Digital phone number, email and Gumroad link exactly as it is, if any appear.
- Never publish or push. Lathan approves every sample first.
- The template has no price helper, because it only made sense for one trade with published prices.
