from odoo import api, fields, models
from odoo.tools import SQL

class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    partner_category_names = fields.Char(string="Etiqueta", readonly=True)

    def _select(self):
        base_select = super()._select()
        lang = self.env.lang or 'en_US'

        extra = SQL("""
            , (
                SELECT STRING_AGG(
                    DISTINCT COALESCE(
                        pc.name->>%s,
                        pc.name->>'en_US'
                    ),
                    ', '
                )
                FROM res_partner_res_partner_category_rel rel
                JOIN res_partner_category pc
                    ON pc.id = rel.category_id
                WHERE rel.partner_id = move.partner_id
            ) AS partner_category_names
        """, lang)

        return SQL("%s %s", base_select, extra)