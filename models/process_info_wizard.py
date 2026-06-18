from odoo import models, fields, api

class SaleProcessInfoWizard(models.TransientModel):
    _name = 'sale.process.info.wizard'
    _description = 'Detalle de Proceso de Venta'
    
    message = fields.Html(readonly=True)
    
    def _get_move_chain(self, move):
        visited = set()
        result = self.env['stock.move']
        stack = [move]

        while stack:
            current = stack.pop()

            if current.id in visited:
                continue

            visited.add(current.id)
            result |= current

            stack.extend(current.move_orig_ids)

        return result

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        sale_line_id = self.env.context.get('active_sale_line_id')
        sale_line = self.env['sale.order.line'].browse(sale_line_id)

        if not sale_line.exists():
            res['message'] = '<p>No se encontró la línea.</p>'
            return res

        direct_moves = sale_line.move_ids

        outgoing_moves = direct_moves.filtered(
            lambda m: m.picking_type_id.code == 'outgoing'
        )

        process_moves = direct_moves.filtered(
            lambda m: m.picking_type_id.code in (
                'mrp_operation',
                'internal',
                'incoming',
            )
        )

        # --------------------------------------------------
        # Casos nuevos:
        # Ya vienen relacionadas las MO e internos
        # --------------------------------------------------
        if process_moves:
            all_moves = direct_moves

        # --------------------------------------------------
        # Casos viejos:
        # Sólo está el outgoing y hay que recorrer
        # move_orig_ids
        # --------------------------------------------------
        else:
            all_moves = direct_moves

            for outgoing in outgoing_moves:
                all_moves |= self._get_move_chain(outgoing)

        # eliminar duplicados
        all_moves = all_moves.sorted(
            key=lambda m: (
                m.date_deadline or m.date or fields.Datetime.now(),
                m.id
            )
        )

        state_labels = {
            'draft': 'Borrador',
            'waiting': 'Esperando otro movimiento',
            'confirmed': 'En espera de disponibilidad',
            'assigned': 'Listo(Asignado)',
            'done': 'Finalizada',
            'cancel': 'Cancelada',
            'progress': 'En proceso',
            'to_close': 'Por cerrar',
        }

        type_labels = {
            'mrp_operation': 'Fabricación',
            'internal': 'Interno',
            'incoming': 'Recepción',
            'outgoing': 'Entrega',
        }

        rows = []

        shown_productions = set()
        shown_pickings = set()
        
        # --------------------------------------------------
        # Fabricaciones
        # --------------------------------------------------
        productions = all_moves.mapped('production_id').filtered(
            lambda p: p and p.id
        )
        
        for production in productions.sorted(
            key=lambda p: p.date_deadline or fields.Datetime.now()
        ):
        
            if production.id in shown_productions:
                continue
        
            shown_productions.add(production.id)
            state = production.state

            is_current = state not in ('done', 'cancel')
            
            row_style = (
                "background-color:#e99d00 !important;"
                "color:white;"
                "font-weight:bold;"
                if is_current else ""
            )
            rows.append(f"""
            <tr style="{row_style}">
                <td><strong>Fabricación</strong></td>
                <td>{production.name}</td>
                <td>{state_labels.get(production.state, production.state)}</td>
                <td>-</td>
                <td>-</td>
                <td>{production.date_deadline or ''}</td>
            </tr>
            """)
        
        # --------------------------------------------------
        # Pickings (Internos / Recepciones / Entregas)
        # --------------------------------------------------
        pickings = all_moves.mapped('picking_id').filtered(
            lambda p: p and p.id
        )
        
        for picking in pickings.sorted(
            key=lambda p: p.scheduled_date or fields.Datetime.now()
        ):
        
            if picking.id in shown_pickings:
                continue
        
            shown_pickings.add(picking.id)
        
            code = picking.picking_type_id.code
        

            state = picking.state
                
            origin = picking.location_id.display_name or ''
            dest = picking.location_dest_id.display_name or ''
            is_current = state in ('assigned', 'progress')

            row_style = (
                "background-color:#e99d00 !important;"
                "color:white;"
                "font-weight:bold;"
                if is_current else ""
            )
            rows.append(f"""
            <tr style="{row_style}">
                <td>
                    {type_labels.get(code, code)}
                </td>
                <td>
                    {picking.name}
                </td>
                <td>
                    {state_labels.get(state, state)}
                </td>
                <td>
                    {origin}
                </td>
                <td>
                    {dest}
                </td>
                <td>
                    {picking.scheduled_date or ''}
                </td>
            </tr>
            """)
        res['message'] = f"""
        <div style="padding:15px">

            <h3>{sale_line.product_id.display_name}</h3>

            <p>
                <strong>Pedido:</strong> {sale_line.order_id.name}<br/>
                <strong>Cantidad:</strong> {sale_line.product_uom_qty}<br/>
                <strong>Estado actual:</strong> {sale_line.process_status}<br/>
                <strong>Fecha compromiso:</strong> {sale_line.order_id.commitment_date or '-'}
            </p>

            <table class="table table-sm table-bordered">
                <thead>
                    <tr>
                        <th>Tipo</th>
                        <th>Documento</th>
                        <th>Estado</th>
                        <th>Origen</th>
                        <th>Destino</th>
                        <th>Fecha límite</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>

        </div>
        """

        return res