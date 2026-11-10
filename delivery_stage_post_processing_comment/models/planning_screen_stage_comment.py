import re

from odoo import api, fields, models
from odoo.exceptions import UserError

STAGE_RE = re.compile(r"^do_stage_\d+$")


class PlanningScreenStageComment(models.Model):
    _name = "planning.screen.stage.comment"
    _description = "Planning Screen Delivery Stage Comment"
    _rec_name = "stage_field"

    planning_screen_id = fields.Many2one(
        "planning.screen", required=True, ondelete="cascade", index=True
    )
    stage_field = fields.Char(required=True)
    comment = fields.Text()

    _sql_constraints = [
        (
            "uniq_screen_stage",
            "unique(planning_screen_id, stage_field)",
            "Only one comment per delivery stage.",
        ),
    ]

    @api.model
    def get_comments(self, screen_id):
        recs = self.search([("planning_screen_id", "=", screen_id)])
        return {r.stage_field: r.comment or "" for r in recs}

    @api.model
    def set_comment(self, screen_id, stage_field, comment):
        if not STAGE_RE.match(stage_field or ""):
            raise UserError(self.env._("Invalid delivery stage."))
        self.env["planning.screen"].browse(screen_id).check_access("write")
        rec = self.search(
            [("planning_screen_id", "=", screen_id), ("stage_field", "=", stage_field)],
            limit=1,
        )
        if rec:
            rec.comment = comment
        else:
            self.create({
                "planning_screen_id": screen_id,
                "stage_field": stage_field,
                "comment": comment,
            })
        return True
