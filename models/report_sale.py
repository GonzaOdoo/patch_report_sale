from odoo import api, fields, models

class SaleReport(models.Model):
    _inherit = 'sale.report'

    cliente_final = fields.Char(string='Cliente Final', readonly=True)
    cliente_stock = fields.Char(string='Stock Cliente', readonly=True)
    commitment_date = fields.Datetime(string='Fecha Programada', readonly=True)
    effective_date = fields.Datetime(string='Fecha Entregada', readonly=True)
    process_status = fields.Char(string='Estado Proceso', readonly=True)
    prioridad = fields.Char(
        string='Prioridad',
        readonly=True,
    )
    delivery_days = fields.Integer(
        string='Días de entrega',
        readonly=True,
        aggregator='avg',  # o 'sum' si lo preferís, aunque avg suele tener más sentido
    )
    def _select_sale(self):
        select = super()._select_sale()
        # Añadimos el campo personalizado
        select += ", l.x_studio_cliente_final AS cliente_final"
        select += ", s.x_studio_stockcliente AS cliente_stock"
        select += ", s.commitment_date AS commitment_date"
        select += ", s.effective_date AS effective_date"
        select += ", l.process_status AS process_status"
        select += """
            , CASE s.x_studio_prioridad
                WHEN '0' THEN 'Normal'
                WHEN '1' THEN 'Baja'
                WHEN '2' THEN 'Media'
                WHEN 'Alta' THEN 'Alta'
              END AS prioridad
        """
        select += """
            , CASE
                WHEN s.effective_date IS NOT NULL
                THEN (DATE(s.effective_date) - DATE(s.date_order))
                ELSE NULL
              END AS delivery_days
        """

        return select

    def _group_by_sale(self):
        group_by = super()._group_by_sale()
        # Aseguramos que el campo esté en GROUP BY
        group_by += ", l.x_studio_cliente_final"
        group_by += ", s.x_studio_stockcliente"
        group_by += ", s.commitment_date"
        group_by += ", s.effective_date"
        group_by += ", l.process_status"
        group_by += ", s.x_studio_prioridad"
        
        return group_by

    def action_show_process_detail(self):
        self.ensure_one()
    
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detalle de proceso',
            'res_model': 'sale.process.info.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_sale_line_id': self.id,
            }
        }