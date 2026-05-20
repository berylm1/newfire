# Seeding a Client's Qdrant Collection with Real Content

When a client onboards, they get `company_<id>` with 3-4 identity chunks (auto, from their onboarding answers). That stops agents from inventing an identity but does NOT stop them from inventing specifics (prices, hours, policies).

This guide shows how to add their real content.

## What to ask the client for

One or more plain-text files, between 500 and 5000 words each, covering:

1. Pricing: exact rates, packages, tiers, minimums, cancellation fees
2. Services: what they do, what they do NOT do, service area boundaries
3. Hours and availability: by day, exceptions, holiday schedule
4. Policies: refunds, warranties, payment methods, privacy posture
5. Tone samples: 3-5 examples of emails or messages in their own voice
6. FAQs: the top 10 questions clients ask

Formats accepted: `.md`, `.txt`, even dumped Google Doc content. Avoid PDFs (can be noisy); ask them to copy-paste the content into a text file.

Plain paragraphs separated by blank lines work best. The chunker splits on blank lines first, then packs paragraphs into ~800-char chunks.

## Running the seed

On Minisforum, with the backend source env loaded:

```
cd /home/newwaveclaw/newfire-backend-docker
set -a; . ./.env; set +a
bash seed_company_content.sh <company_id> /path/to/their_content.md
```

Example (Sherifah's collection, once she onboards and gets company_id=7):

```
bash seed_company_content.sh 7 /tmp/sherifah_services_and_pricing.md
```

Output will name each chunk and show the final points_count.

## After seeding, verify in the SPA

1. Admin Dashboard > ROI per Company > her card should show "RAG on"
2. Log in as her (or mint a test JWT), go to one of her agents, ask a specific pricing or policy question
3. Response should cite the seeded facts; no invented specifics

## For Funmi specifically

Per `project_funmi_privacy.md`, her data handling is stricter:
- Source files live ONLY on DGX (never transit through Mac or cloud)
- Collection creation uses local inference only for embeds
- After seeding, chat routing must exclude OpenRouter for any request that retrieves from her collection
- All drafts she generates must carry the attorney-review disclaimer
- Deletion script must purge collection + chat history + backups

Follow her privacy playbook before seeding any real immigration content.

## When content changes

Re-run the script with `--start-id <high_number>` to append without overwriting identity chunks. Or use `--force` on the backfill script to wipe and start fresh (only do this if the new content fully replaces the old).

Ideal cadence: re-seed anytime the client's pricing, hours, or policies change. Typical: quarterly for most small businesses, monthly if they're actively iterating.
