from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order.line'

    process_status = fields.Char(
        compute="_compute_process_status",
        store=True,
    )
    
    fabrication_date = fields.Datetime(
        string='Fecha Fabricación',
        compute='_compute_fabrication_date',
        store=True,
    )

    @api.depends(
        'move_ids',
        'move_ids.date',
        'move_ids.production_id',
        'move_ids.production_id.state',
        'move_ids.move_orig_ids',
        'move_ids.move_orig_ids.date',
        'move_ids.move_orig_ids.production_id',
        'move_ids.move_orig_ids.production_id.state',
    )
    def _compute_fabrication_date(self):
        for line in self:
            all_moves = line._get_process_moves()
    
            mrp_moves = all_moves.filtered(
                lambda m: (
                    m.picking_type_id.code == 'mrp_operation'
                    and m.production_id
                    and m.production_id.state != 'cancel'
                )
            )
    
            if not mrp_moves:
                line.fabrication_date = False
                continue
    
            productions = mrp_moves.mapped('production_id')
    
            # Si alguna fabricación todavía no terminó,
            # no mostramos fecha.
            if any(production.state != 'done' for production in productions):
                line.fabrication_date = False
                continue
    
            done_moves = mrp_moves.filtered(
                lambda m: m.production_id.state == 'done'
            )
    
            line.fabrication_date = (
                max(done_moves.mapped('date'))
                if done_moves
                else False
            )

    def _compute_process_status(self):
        for line in self:
            # --------------------------------------------------
            # 1. Entrega cliente
            # --------------------------------------------------
            outgoing_moves = line.move_ids.filtered(
                lambda m: m.picking_type_id.code == 'outgoing'
            )
    
            if outgoing_moves and all(
                m.state == 'done'
                for m in outgoing_moves
            ):
                line.process_status = 'Entregado'
                continue
    
            if outgoing_moves and all(
                m.state == 'assigned'
                for m in outgoing_moves
            ):
                line.process_status = 'Pendiente de entrega (En despacho)'
                continue
    
            # --------------------------------------------------
            # 2. Movimientos internos
            # --------------------------------------------------
            internal_moves = line.move_ids.filtered(
                lambda m: m.picking_type_id.code == 'internal'
            )
    
            active_internal = internal_moves.filtered(
                lambda m: m.state == 'assigned'
            )
    
            if active_internal:
                move = active_internal.sorted(
                    key=lambda m: (m.date or fields.Datetime.now())
                )[0]
    
                # Muestra dónde está actualmente
                line.process_status =f" Ubicación: {move.location_id.display_name}"
                continue

            # --------------------------------------------------
            # 2. Recepción interna
            # --------------------------------------------------
            incoming_moves = line.move_ids.filtered(
                lambda m: m.picking_type_id.code == 'incoming'
            )
    
            active_incoming = incoming_moves.filtered(
                lambda m: m.state == 'assigned'
            )
    
            if active_incoming:
                move = active_incoming.sorted(
                    key=lambda m: (m.date or fields.Datetime.now())
                )[0]
    
                # Muestra dónde está actualmente
                line.process_status = f"Ubicación: {move.location_id.display_name}"
                continue
            # --------------------------------------------------
            # 3. Fabricación
            # --------------------------------------------------
            mrp_moves = line.move_ids.filtered(
                lambda m: m.picking_type_id.code == 'mrp_operation'
            )
            state_order = {
                'draft': 0,
                'confirmed': 1,
                'progress': 2,
                'to_close': 3,
                'done': 4,
                'cancel': 5,
            }

            if mrp_moves:
                productions = mrp_moves.mapped('production_id').filtered(
                    lambda p: p and p.state != 'cancel'
                )
                if productions:
                    production = min(
                        productions,
                        key=lambda p: state_order.get(p.state, 999)
                    )
                
                    state_labels = {
                        'draft': 'Borrador',
                        'confirmed': 'Confirmada',
                        'progress': 'En proceso',
                        'to_close': 'Por cerrar',
                        'done': 'Finalizada',
                    }
                
                    line.process_status = (
                        f"Fabricación - {state_labels.get(production.state, production.state)}"
                    )
                    continue
                    
            # --------------------------------------------------
            # 4. Fallback
            # --------------------------------------------------
            if internal_moves:
                move = internal_moves[0]
                line.process_status =f'Ubicación: {move.location_id.display_name}'
            if incoming_moves:
                move = incoming_moves[0]
                line.process_status =f'Ubicación: {move.location_id.display_name}'
            if outgoing_moves:

                for outgoing in outgoing_moves:
                    active_move = self._find_active_origin_move(outgoing)
            
                    if active_move:
            
                        # Si pertenece a una fabricación,
                        # mostrar el estado de la MO
                        if active_move.production_id:
            
                            production = active_move.production_id
            
                            state_labels = {
                                'draft': 'Borrador',
                                'confirmed': 'Confirmada',
                                'progress': 'En proceso',
                                'to_close': 'Por cerrar',
                                'done': 'Finalizada',
                            }
            
                            line.process_status = (
                                f"Fabricación - {state_labels.get(production.state, production.state)}"
                            )
            
                        else:
                            line.process_status = (
                                f"Ubicación: {active_move.location_id.display_name}"
                            )
            
                        break
            
                else:
                    line.process_status = 'Fabricación - Indefinido'
            
                continue
            line.process_status = 'Sin planificación'




    def _find_active_origin_move(self, move):
        visited = set()
        stack = [move]
    
        while stack:
            current = stack.pop()
    
            if current.id in visited:
                continue
    
            visited.add(current.id)
    
            if current.state == 'assigned':
                return current
    
            stack.extend(current.move_orig_ids)
    
        return False


    def _get_process_moves(self):
        self.ensure_one()
    
        direct_moves = self.move_ids
    
        process_moves = direct_moves.filtered(
            lambda m: m.picking_type_id.code in (
                'mrp_operation',
                'internal',
                'incoming',
            )
        )
    
        # Si ya tiene los movimientos de proceso relacionados
        # directamente con la línea, usamos esos.
        if process_moves:
            return direct_moves
    
        # Registros viejos:
        # la línea solamente tiene el outgoing y hay que recorrer
        # la cadena de movimientos hacia atrás.
        outgoing_moves = direct_moves.filtered(
            lambda m: m.picking_type_id.code == 'outgoing'
        )
    
        all_moves = direct_moves
    
        visited = set()
        stack = list(outgoing_moves)
    
        while stack:
            current = stack.pop()
    
            if current.id in visited:
                continue
    
            visited.add(current.id)
            all_moves |= current
    
            stack.extend(current.move_orig_ids)
    
        return all_moves