from odoo import models, fields
import requests
import logging
from dateutil import parser

_logger = logging.getLogger(__name__)


class HubspotMeetingData(models.Model):
    _name = 'hubspot.meeting.data'
    _description = 'HubSpot Meeting Data'
    _rec_name = 'name'

    name = fields.Char("Meeting Name")
    meeting_description = fields.Char("Meeting Body")
    meeting_start_time = fields.Datetime("Meeting Start Time")
    meeting_end_time = fields.Datetime("Meeting End Time")
    meeting_type = fields.Char("Meeting Type")
    hubspot_meeting_id = fields.Char("HubSpot Meeting ID")

    meeting_organized_by = fields.Char("Meeting Organized By")
    associated_companies = fields.Char("Associated Companies")
    associated_contacts = fields.Char("Associated Contacts")

    # ─── Configuration ────────────────────────────────────────────────────────

    def _get_hubspot_config(self):
        """Return (base_url, token) from Odoo system parameters."""
        get = self.env['ir.config_parameter'].sudo().get_param
        return (
            get('burgtec_hubspot_customization.hubspot_base_url'),
            get('burgtec_hubspot_customization.hubspot_integrations_token'),
        )

    def _get_headers(self, token):
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    # ─── HubSpot Lookup Helpers ────────────────────────────────────────────────

    def _fetch_all_owners(self, base_url, headers):
        """
        Return {owner_id: "First Last"} for every HubSpot owner.
        Called once before the sync loop to avoid per-meeting lookups.
        """
        try:
            resp = requests.get(
                f"{base_url}/crm/v3/owners",
                headers=headers,
                params={"limit": 500},
                timeout=30,
            )
            if resp.status_code != 200:
                _logger.warning("Could not fetch owners: %s", resp.text)
                return {}

            return {
                str(o["id"]): self._full_name(o.get("firstName"), o.get("lastName"), o.get("email"))
                for o in resp.json().get("results", [])
            }
        except Exception as e:
            _logger.warning("Error fetching owners: %s", e)
            return {}

    def _batch_fetch_names(self, base_url, headers, object_type, ids, name_fields):
        """
        Generic batch-read for contacts or companies.
        Returns {id: display_name}.

        - object_type : "contacts" or "companies"
        - ids         : iterable of HubSpot record IDs
        - name_fields : list of property keys to build the display name from
        """
        if not ids:
            return {}

        result = {}
        ids = list(ids)
        endpoint = f"{base_url}/crm/v3/objects/{object_type}/batch/read"

        for i in range(0, len(ids), 100):  # HubSpot max = 100 per batch
            chunk = ids[i:i + 100]
            payload = {
                "inputs": [{"id": cid} for cid in chunk],
                "properties": name_fields,
            }
            try:
                resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
                if resp.status_code != 200:
                    _logger.warning("Batch read failed (%s): %s", object_type, resp.text)
                    continue

                for item in resp.json().get("results", []):
                    props = item.get("properties", {})
                    values = [props.get(f) or "" for f in name_fields]
                    result[item["id"]] = " ".join(filter(None, values)).strip() or item["id"]

            except Exception as e:
                _logger.warning("Error in batch read (%s): %s", object_type, e)

        return result

    # ─── Date Parsing ─────────────────────────────────────────────────────────

    def _parse_hubspot_date(self, date_string):
        """Convert a HubSpot ISO date string to a naive UTC datetime for Odoo."""
        if not date_string:
            return False
        try:
            return parser.isoparse(date_string).replace(tzinfo=None)
        except Exception as e:
            _logger.warning("Could not parse date '%s': %s", date_string, e)
            return False

    # ─── Meeting Type Resolution ───────────────────────────────────────────────

    def get_meeting_type_name(self, internal_name):
        meeting_type = self.env['hubspot.meeting.types'].search(
            [('hubspot_internal_name', '=', internal_name)], limit=1
        )
        return meeting_type.name if meeting_type else False

    # ─── Main Sync ────────────────────────────────────────────────────────────

    def import_all_meetings_from_hubspot(self):
        """
        Pull all meetings from HubSpot and create Odoo records for new ones.

        Strategy (avoids N+1 API calls):
          1. Page through all meetings, collecting raw data + association IDs.
          2. Batch-resolve all contact names and company names in bulk.
          3. Fetch all owners once up-front.
          4. Create Odoo records, skipping any that already exist.
        """
        base_url, token = self._get_hubspot_config()
        if not token:
            _logger.error("HubSpot API token is not configured.")
            return False

        headers = self._get_headers(token)

        # ── Step 1: Page through all meetings ──────────────────────────────────
        raw_meetings = []
        after = None

        while True:
            params = {
                "limit": 100,
                "properties": ",".join([
                    "hs_meeting_title",
                    "hs_meeting_start_time",
                    "hs_meeting_end_time",
                    "hs_activity_type",
                    "hs_meeting_body",
                    "hubspot_owner_id",
                ]),
                "associations": "contacts,companies",
            }
            if after:
                params["after"] = after

            resp = requests.get(f"{base_url}/crm/v3/objects/meetings",
                                headers=headers, params=params, timeout=30)
            if resp.status_code != 200:
                _logger.error("HubSpot API error %s", resp.status_code)
                return False

            data = resp.json()
            raw_meetings.extend(data.get("results", []))

            next_page = data.get("paging", {}).get("next")
            after = next_page["after"] if next_page else None
            if not after:
                break

        # ── Step 2: Collect all association IDs across every meeting ───────────
        all_contact_ids = set()
        all_company_ids = set()

        for meeting in raw_meetings:
            assoc = meeting.get("associations") or {}
            all_contact_ids.update(c["id"] for c in assoc.get("contacts", {}).get("results", []))
            all_company_ids.update(c["id"] for c in assoc.get("companies", {}).get("results", []))

        # ── Step 3: Batch-resolve names + owners (a handful of API calls) ───────
        owner_map = self._fetch_all_owners(base_url, headers)
        contact_map = self._batch_fetch_names(base_url, headers, "contacts",
                                              all_contact_ids, ["firstname", "lastname"])
        company_map = self._batch_fetch_names(base_url, headers, "companies",
                                              all_company_ids, ["name"])

        # ── Step 4: Create Odoo records ────────────────────────────────────────
        created = 0
        for meeting in raw_meetings:
            hubspot_id = meeting.get("id")

            if self.search([("hubspot_meeting_id", "=", hubspot_id)], limit=1):
                continue  # already synced

            props = meeting.get("properties", {})
            assoc = meeting.get("associations") or {}

            # Owner → organizer name
            owner_id = str(props.get("hubspot_owner_id") or "")
            organized_by = owner_map.get(owner_id, "")

            # Associations → company name (first) + all contact names
            company_ids = [c["id"] for c in assoc.get("companies", {}).get("results", [])]
            contact_ids = [c["id"] for c in assoc.get("contacts", {}).get("results", [])]
            # company_name = company_map.get(company_ids[0], "") if company_ids else ""
            company_names = ", ".join(filter(None, [company_map.get(cid) for cid in company_ids]))
            contact_names = ", ".join(filter(None, [contact_map.get(cid) for cid in contact_ids]))

            self.create({
                "name": props.get("hs_meeting_title") or "No Title",
                "meeting_description": props.get("hs_meeting_body") or "",
                "meeting_start_time": self._parse_hubspot_date(props.get("hs_meeting_start_time")),
                "meeting_end_time": self._parse_hubspot_date(props.get("hs_meeting_end_time")),
                "meeting_type": self.get_meeting_type_name(props.get("hs_activity_type")),
                "hubspot_meeting_id": hubspot_id,
                "meeting_organized_by": organized_by,
                "associated_companies": company_names,
                "associated_contacts": contact_names,
            })
            created += 1

        _logger.info("HubSpot sync complete — %d new meeting(s) created.", created)
        return True

    # ─── Meeting Types Sync ───────────────────────────────────────────────────

    def fetch_hubspot_meeting_types(self):
        """Sync HubSpot meeting type options into hubspot.meeting.types."""
        _, token = self._get_hubspot_config()
        headers = self._get_headers(token)
        url = "https://api.hubapi.com/crm/v3/properties/meetings/hs_activity_type"

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"HubSpot API Error: {resp.text}")

        MeetingType = self.env['hubspot.meeting.types']
        for opt in resp.json().get("options", []):
            vals = {
                "name": opt.get("label"),
                "hubspot_internal_name": opt.get("value"),
            }
            existing = MeetingType.search(
                [("hubspot_internal_name", "=", opt.get("value"))], limit=1
            )
            existing.write(vals) if existing else MeetingType.create(vals)

    # ─── Internal Utilities ───────────────────────────────────────────────────

    @staticmethod
    def _full_name(*parts):
        """Join non-empty name parts, fall back to the last part (e.g. email)."""
        meaningful = [p for p in parts[:-1] if p]
        return " ".join(meaningful).strip() if meaningful else (parts[-1] or "")