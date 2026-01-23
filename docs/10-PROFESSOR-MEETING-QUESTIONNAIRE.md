# Professor Meeting: NAR Web Server - Quick Reference

**Deadline:** 15 days | **Meeting Duration:** 30-45 min

---

## BLOCKING DECISIONS (Must Decide Today)

| # | Question | Options | Notes |
|---|----------|---------|-------|
| 1 | **Hosting** | University IT / AWS / GCP / DigitalOcean | Fallback: DigitalOcean ~$20/mo |
| 2 | **Domain Name** | `splicing.lab.edu` / `splicingpredictor.org` | Who registers & pays? |
| 3 | **Example Sequences** | From paper / New biologically meaningful | Need 2-3 for "Try Example" button |

---

## DECISIONS NEEDED THIS WEEK

| # | Question | Your Answer |
|---|----------|-------------|
| 4 | Who writes **help pages**? | _____________ |
| 5 | Who writes **tutorial**? | _____________ |
| 6 | **5-year maintenance** - who is responsible? | _____________ |
| 7 | **Data retention** - how long to store results? | _____ days |

---

## CAN SKIP FOR MVP (Defer to later)

- [ ] Email notifications
- [ ] Batch processing (multiple sequences)
- [ ] External database integrations
- [ ] Open source license decision

---

## TECHNICAL TRADE-OFFS (Explain if asked)

| Decision | Recommendation | Why |
|----------|----------------|-----|
| Database | SQLite (start simple) | Easy backup, sufficient for ~50 users/day |
| Job Queue | FastAPI BackgroundTasks | Built-in, no extra setup |
| GPU | Not needed | Model is small, CPU inference <1 sec |

---

## NAR REQUIREMENTS CHECKLIST

**Must Have:**
- [x] HTTPS on port 443
- [ ] "Try Example" button with sample data
- [ ] Help pages (how to interpret results)
- [ ] Tutorial with sample output links
- [ ] Bookmarkable result URLs
- [ ] Free access statement on landing page
- [ ] No login required

**Must NOT Have:**
- No tracking cookies
- No Flash/Java plugins
- No registration requirement

---

## 15-DAY SPRINT PLAN

| Days | Milestone |
|------|-----------|
| 1-2 | Server setup + domain + SSL |
| 3-7 | Core prediction API + frontend |
| 8-10 | Force plot visualization |
| 11-13 | Help pages + tutorial |
| 14-15 | Testing + NAR proposal |

---

## MEETING ACTION ITEMS

Fill in after meeting:

```
Hosting Decision:     _________________________
Domain Name:          _________________________
Domain Registrar:     _________________________
Example Sequences:    _________________________
Help Page Author:     _________________________
Tutorial Author:      _________________________
Data Retention:       _________ days
Maintenance Owner:    _________________________
Budget Approved:      $_________/month
```

---

## RISKS TO MENTION

| Risk | Mitigation |
|------|------------|
| ViennaRNA can hang on complex sequences | 30-second timeout |
| Hosting decision delayed | Need answer today to start |
| Help content not ready in time | Can write basic version, iterate later |

---

## QUESTIONS FOR PROFESSOR

1. Is there existing university server infrastructure we should use?
2. Are there lab branding requirements (logo, colors)?
3. Which validation datasets should we highlight in the proposal?
4. Any integration requirements with other lab tools?
5. Who should be listed as authors on the NAR proposal?

---

*Full questionnaire: `/docs/` or `.claude/plans/swift-munching-thunder.md`*
