# One page sample template

`index.html` is the Ridgeline plumbing demo (`sample-plumbing.html`) turned into a template. The CSS is a byte for byte copy, so every sample has the same look. Do not edit the CSS.

## How to make a sample

1. Copy this folder to `samples/<slug>/`, where slug is the business name in lowercase with hyphens, for example `bradys-coffee-company`.
2. Put three photos beside `index.html` and replace `{{PHOTO_1}}`, `{{PHOTO_2}}` and `{{PHOTO_3}}` with their file names.
3. Fill every `{{PLACEHOLDER}}` below. Search the file for `{{` when done; nothing may be left.
4. Delete every block marked `OPTIONAL` whose fact is unknown. Delete the whole block, never leave it half filled.
5. Choose ONE of the HOW IT WORKS or VISIT sections (both are in the file) and delete the other. Walk in shops and food use VISIT and delete CONTACT. Trades use HOW IT WORKS and CONTACT.
6. Keep one nav link per section still on the page.
7. Delete all HTML comments.
8. Write `photo-credits.txt` (file name, photographer, source page URL for each photo).
9. Open the page at 390 and 1280 pixels wide and fix anything broken.

Finished examples to copy from: `samples/bradys-coffee-company/` (fewest facts) and `samples/rusty-rooster-southern-breakfast/` (menu and hours).

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
| `{{SERVICES_HEADING}}` | Heading of the services block, also used in the nav | What we serve, Services, The menu |
| `{{SERVICES_INTRO}}` | One line beside that heading | |
| `{{SERVICE_1}}` to `{{SERVICE_4}}` | One known service or menu group each. Delete extra rows | Coffee |
| `{{SERVICE_n_PRICE}}` | Price (OPTIONAL, only if published by the business) | |
| `{{SERVICE_n_NOTE}}` | One line about it (OPTIONAL) | |
| `{{SERVICES_NOTE}}` | One closing line under the list (OPTIONAL) | `<b>Call ahead</b> to ask about today's menu.` |
| `{{HOW_INTRO}}`, `{{STEP_1}}` to `{{STEP_3}}`, `{{STEP_n_NOTE}}` | How it works (OPTIONAL, trades only) | |
| `{{VISIT_INTRO}}` | One line for the Visit section | Find us on W Pine St in Mount Airy. |
| `{{AREA_TOWNS}}` / `{{AREA_EXTRA}}` | Towns served (OPTIONAL) | |
| `{{REVIEW_n}}`, `{{REVIEW_n_NAME}}`, `{{REVIEW_n_TOWN}}` | Real reviews only (OPTIONAL) | |
| `{{FAQ_n_Q}}` / `{{FAQ_n_A}}` | Questions with known answers (OPTIONAL) | |
| `{{FORM_EXAMPLE}}` | Placeholder text in the quote form (OPTIONAL, trades only) | |
| `{{PHOTO_1}}`, `{{PHOTO_2}}`, `{{PHOTO_3}}` | Photo file names: hero (wide), services, visit or how it works | hero.jpg |
| `{{PHOTO_1_ALT}}` to `{{PHOTO_3_ALT}}` | What the photo shows, plainly | A tray of glazed doughnuts |
| `{{PHOTO_CREDIT_LINE}}` | Credit sentence in the footer | Photos by Kari Shea and Annie Spratt on Unsplash, shown as examples. |

Set the `width` and `height` on each `<img>` to the photo's real pixel size.

## Rules

- Facts come only from the lead line or the business's own public page (its own site, its own ordering page, or its own Facebook page if it really loads). Directories, review sites and tourism pages do not count.
- Never invent reviews, ratings, prices, menu items, years in business, hours, owner names or claims. If a fact is unknown, delete the block.
- Food businesses can use plain trade words as services ("Coffee", "Doughnuts") when the lead says so, and nothing more specific than the facts support. "Call ahead" and "Find us at <address>" are fine.
- Keep the top line: "Sample site made for <business> by Granite City Digital." with the link to https://granitecitydigital.me/.
- Keep `<meta name="robots" content="noindex">`.
- Shared files use paths that work from `/samples/<slug>/`: `../../favicon.svg` and `../../apple-touch-icon.png`. Photos sit beside `index.html`.
- Photos: three per sample, free license (Unsplash or Pexels), about 1600 px wide, jpg, under about 400 KB each. Candid and generic. Never show a food or job the business is not known to offer as if it were theirs. No visible brand names or readable text in the photo.
- Keep every Granite City Digital phone number, email and Gumroad link exactly as it is, if any appear.
- Never publish or push. Lathan approves every sample first.
- The plumbing demo's price helper is not in the template, because it only made sense for one trade with published prices.
