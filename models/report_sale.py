from odoo import api, fields, models

class SaleReport(models.Model):
    _inherit = 'sale.report'

    cliente_final = fields.Char(string='Cliente Final', readonly=True)

    def _select_sale(self):
        select = super()._select_sale()
        # Añadimos el campo personalizado
        select += ", l.x_studio_cliente_final AS cliente_final"
        return select

    def _group_by_sale(self):
        group_by = super()._group_by_sale()
        # Aseguramos que el campo esté en GROUP BY
        group_by += ", l.x_studio_cliente_final"
        return group_by
