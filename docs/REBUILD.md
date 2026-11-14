# Admission Setu rebuild

Share this file with the developer. Build a new site in a copy of this folder. The current pages are not the product. Do not extend them.

The public site is **Admission Setu**. The layout to follow is the DekhoCampus home, college list, and college page: search, streams, filters, photo cards, then a college page with the facts we actually have. The rank check is part of the same site. A prediction result uses the same college card, with opening rank, closing rank, and chance added.

## Do not use the old site as data

Delete these from the new build. They are the previous product.

- `frontend/`
- `web/`
- `api/`
- `college-dekho/`
- The old `colleges` rows in Postgres, including scraped HTML stored on those rows
- `setu-data.tar`

Do not copy text, fees, or photos out of those old files into the new database.

Keep only the source files named below, plus this document, until the new app runs. Then remove the old app.

## Catalogue data (latest download only)

Folder: `dekho-campus/`

`manifest.json` is the inventory. Load these files. Do not load any other college catalogue.

| File | Rows | Use |
| --- | --- | --- |
| `colleges.jsonl` | 13,021 | College name, slug, city, state, type, category, rating, reviews, fees text, image, logo, approvals, established year, description, admission, cutoff text, placement text, facilities, hostel, gallery |
| `courses.jsonl` | 877 | Course name, slug, category, level, duration, eligibility |
| `course_fees.jsonl` | 5,447 | One row per college course: `college_slug`, `course_name`, `course_group`, `specialization`, `academic_level`, `duration`, `fee_amount`, `fee_type`, `year` |
| `states_cities.jsonl` | 7,470 | State and city list for filters |
| `exams.jsonl` | 503 | Exam name, dates, eligibility, pattern. Show them. Do not use them as rank data |
| `faqs.jsonl` | 13,570 | Questions and answers, joined by `page` and `item_slug` |
| `articles.jsonl` | 5,525 | News and guides |
| `scholarships.jsonl` | 119 | Scholarship pages |
| `authors.jsonl` | 20 | Author names where an article has an author |
| `landing_pages.jsonl` | 6 | Landing copy |
| `also_check_modules.jsonl` | 3 | Related-link blocks |

A field that is empty stays empty. Do not invent a fee, a rank, an approval, a photo, or a review. Many college descriptions say the official fee or course list is still unchecked. Show that field only when the JSON has a value.

Images may point at DekhoCampus storage URLs. Download them into our own storage as part of the import. Do not hotlink those URLs in the finished site.

The public name, logo, and domain are Admission Setu. Do not show the DekhoCampus name or logo.

## Rank data (separate from the catalogue)

The predictor does not read `dekho-campus`. DekhoCampus cutoff paragraphs are not a rank.

Use only the official 2026 counselling files:

- JEE Main and JEE Advanced: JoSAA 2026 round 5 ORCR. The code expects `prediction/josaa-2026-round-5-orcr.csv`. That file is not in this folder. Use that official file if it is supplied with the copy. Do not replace it with an earlier round or with CSAB.
- NEET: `prediction/mcc-2026-final-orcr.csv` (present).
- `prediction/csab-2026-special-orcr.csv` is not a source for the predictor.

Columns used from those files: Year, Round, Exam, Institute, State, Academic Program Name, Quota, Seat Type, Gender, Opening Rank, Closing Rank, Preparatory.

Rules that must stay:

- Exams: JEE Main, JEE Advanced, NEET.
- JEE Advanced is IIT seats only. NIT, IIIT, and GFTI seats are JEE Main.
- NEET courses: MBBS, BDS, B.Sc Nursing.
- Categories: General (OPEN), EWS, OBC-NCL, SC, ST.
- Gender: male or female. A female-only pool is a separate seat.
- Home state chooses home-state and other-state seats. All-India seats stay available.
- A smaller rank is a better rank.
- Preparatory rows are excluded.
- Show opening rank, closing rank, and a chance from very high to very low.
- List seats the rank would have cleared. If none, show the nearest seats within 15 percent. Leave the rest off the list.
- The match is deterministic. An AI model must not produce the rank or the college list.

The current match lives in `prediction/match.py` and `prediction/institutes.py`. Port those rules. Do not rewrite them from memory. Check results against `prediction/test_match.py` before the predictor is shown to students.

## Stack

| Piece | Use |
| --- | --- |
| Public pages | Astro and Tailwind |
| College API, accounts, and the rank check | Python (FastAPI) |
| Database | Postgres, new database, loaded from the files above |
| Search and filters | Typesense |
| Pages and images | Cloudflare, with campus photos resized for phones |
| Rank seats | Kept in memory on the API, reloaded only when the official file changes |

Do not add Laravel, Vue, or MySQL for this build. Do not add WhatsApp or an AI chat in the first release. Login can stay a mobile number and a fixed code until WhatsApp exists. The account stores the prediction. Withdrawing consent deletes that account and its predictions.

## Pages

1. **Home.** Same order as the DekhoCampus home: search, suggested searches, what to do next, streams, top colleges, top exams. `web/try.html` is a rough trial of that order only. Do not keep that file.
2. **College list.** Photo card: picture, name, city, state, ownership, course group, fee, rating when present. Filters on the left on a wide screen. On a phone, filters sit behind one Filter control so the cards are first. Load 20 colleges, then more when asked.
3. **College page.** Photo, logo, name, city, state, ownership, established year, approvals, streams, overview, fees, courses, admission, cutoff text, placements, facilities, hostel, answers. Hide a section that has no value.
4. **Predict.** Form: exam, rank, category, gender, home state, and course when the exam is NEET. Results are the same college cards, plus opening rank, closing rank, and chance. The student can save a choice list, highest choice first, up to 40 seats.
5. **Exams and courses.** Pages from `exams.jsonl` and `courses.jsonl`. An exam page does not pretend to predict a rank unless that exam is JEE Main, JEE Advanced, or NEET.

## Filters

Build these from the new files, with a count beside each value.

| Filter | Source |
| --- | --- |
| State | `colleges.jsonl` `state`, and `states_cities.jsonl` |
| Course | `course_fees.jsonl` `course_group` (examples: B.E. / B.Tech, MBBS) |
| Branch | `course_fees.jsonl` `course_name` and `specialization` (examples: Computer Science, Electrical and Electronics) |
| Stream | `colleges.jsonl` `category` and `tags` |
| City | `colleges.jsonl` `city` |

Search matches college name, course name, city, and state through Typesense.

On a prediction, branch is the JoSAA or MCC program name, not the catalogue course name. Show a branch chip only when that program exists for the rank just checked.

## Import order

1. Create a new empty Postgres database.
2. Load `states_cities.jsonl`, then `courses.jsonl`, then `colleges.jsonl`, then `course_fees.jsonl`, then exams, articles, scholarships, and faqs.
3. Load JoSAA 2026 round 5 and `prediction/mcc-2026-final-orcr.csv` into the seat table.
4. Build the Typesense index from the new tables.
5. Run `prediction/test_match.py` against the loaded seats.

A college with no `course_fees` row still appears. Its course filter is empty. Do not fill it from the old database.

## Done when

- Home, college list, college page, and Predict are one site.
- Filters for state, course, and branch return colleges from `dekho-campus` only.
- A JEE Main, JEE Advanced, and NEET check matches the official file and the tests in `prediction/test_match.py`.
- Predicted colleges use the same card as the college list.
- The old frontend, old HTML, and old college rows are not served.
