from odoo import _, api, fields, models
import logging

_logger = logging.getLogger(__name__)
class ProductTemplate(models.Model):
    _inherit = "product.template"

    volume = fields.Float(
        'Volume',
        digits='Volume',
        compute='_compute_volume',
        inverse='_inverse_volume',
        store=True
    )

    product_height = fields.Float(
        inverse="_inverse_dimensions",
        related='',
        store=True
    )
    product_length = fields.Float(
        inverse="_inverse_dimensions",
        related='',
        store=True
    )
    product_width = fields.Float(
        inverse="_inverse_dimensions",
        related='',
        store=True
    )

    def _inverse_dimensions(self):
        for template in self:
            _logger.info("Inverse")
            _logger.info(template.product_variant_ids)
            template.product_variant_ids.write({
                'product_height': template.product_height,
                'product_length': template.product_length,
                'product_width': template.product_width,
            })

    def _inverse_volume(self):
        for template in self:
            _logger.info("Inverse variant, volume")
            template.product_variant_ids.write({
                'volume': template.volume
            })