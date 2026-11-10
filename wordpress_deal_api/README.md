# WordPress Deal API

REST API for the Burgtec WordPress website. Base path: `/api/wp/v1`

| Method | Path | Purpose |
|---|---|---|
| GET | `/deals` | List deals. Params: `q`, `deal_number`, `hubspot_deal_id`, `limit` (max 100, default 50), `offset` |
| GET | `/deals/<id>` | Read one deal |
| POST | `/deals/<id>/notes` | Add an internal note. JSON: `{"body": "...", "external_ref": "optional"}` |
| POST | `/deals/<id>/attachments` | Attach a PDF. `multipart/form-data`: `file` (required, .pdf, max 20 MB), `note`, `external_ref` (optional) |

`<id>` is the Odoo record id returned by the list call. Find a deal by Burgtec
deal number with `GET /deals?deal_number=602828`.

## Authentication
`Authorization: Bearer wpk_...` using a **WordPress API key**.

This is its own credential, not an Odoo user key:
* It is **not tied to any Odoo user**, so no licence seat and no user rights to manage.
* Odoo's standard RPC interface (`/xmlrpc`, `/jsonrpc`) **rejects it**. A leaked key
  cannot read contacts, products, sales or anything else. It only works on `/api/wp/v1`.
* Odoo API keys of real users are **not accepted** here either.
* Only a hash is stored. The key is shown once when generated.

### Create a key (administrator)
Settings > Technical > **Generate WordPress API Key**. Choose a name and validity
(1 to 365 days, default 90), click Generate, copy the key and send it to the developer
over a secure channel. It cannot be shown again.

### Revoke or review
Settings > Technical > **WordPress API Keys**: see state, expiry and last use.
Archive a key to revoke it immediately. To rotate, generate a new key first, switch
the website over, then revoke the old one.

## What it can and cannot do
* Reads a fixed whitelist of deal fields (see `_serialize` in `controllers/main.py`).
  Revenue, site contact details and prices are deliberately not exposed.
* Only creates chatter notes and PDF attachments. No edit, delete or confirm.
* Notes are internal (not emailed to followers), authored by the partner
  "WordPress Website", HTML is escaped.
* `external_ref` makes retries safe: the same ref on the same deal returns the
  first result with `"duplicate": true` instead of posting twice.

## Errors
JSON: `{"ok": false, "error": {"code": "...", "message": "..."}}`.
401 bad, expired, revoked or missing key, 404 deal not found, 400 bad input or
not a PDF, 413 file too large, 500 unexpected.

## Audit
Settings > Technical > WordPress API Log: key, call, deal, status, IP, time.
Failed key attempts are logged too. Kept 180 days.

## Deployment notes
* Needs a single Odoo database (or a database filter) so Odoo can select the database
  without a session. Production has one.
* Ask IT to restrict `/api/wp/` to the WordPress server IP (Nginx and/or Cloudflare)
  and to allow that IP through Cloudflare bot rules.
* Use a different key for each environment.

## Example
```bash
curl -H "Authorization: Bearer $KEY" "https://<host>/api/wp/v1/deals?deal_number=602828"
curl -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
     -d '{"body":"Customer approved the layout","external_ref":"wp-1001"}' \
     https://<host>/api/wp/v1/deals/8914/notes
curl -H "Authorization: Bearer $KEY" -F file=@quote.pdf -F note="Signed quote" \
     -F external_ref=wp-1002 https://<host>/api/wp/v1/deals/8914/attachments
```

## Tests
`odoo -d <db> -i wordpress_deal_api --test-enable --test-tags /wordpress_deal_api --stop-after-init`
