# SPDX-FileCopyrightText: 2024 Custom GNU Health
# SPDX-License-Identifier: GPL-3.0-or-later

import csv
import io
from datetime import datetime
import logging

from trytond.exceptions import UserError
from trytond.model import fields, ModelSQL, ModelView, Unique
from trytond.pool import Pool
from trytond.pyson import Bool, Eval
from trytond.transaction import Transaction
from trytond.wizard import Button, StateAction, StateTransition, StateView, Wizard

__all__ = [
    'MedicationAudit',
    'SelectPrescriptionStart',
    'SelectPrescriptionWizard',
    'ExportResult',
    'PrescriptionAuditExport',
]
logger = logging.getLogger(__name__)


class MedicationAudit(ModelSQL, ModelView):
    'Medication Audit'
    __name__ = 'gnuhealth.medication.audit'

    source_prescription = fields.Many2One(
        'gnuhealth.prescription.order', 'Cargar Receta',
        states={'invisible': Bool(Eval('prescription_line', False))},
        depends=['prescription_line'],
        help='Seleccione una receta para cargar todas sus líneas de medicamentos')

    prescription_line = fields.Many2One(
        'gnuhealth.prescription.line', 'Línea de Receta',
        readonly=True,
        help='La línea de receta (medicamento) que se está auditando')

    prescription = fields.Function(
        fields.Many2One('gnuhealth.prescription.order', 'Receta'),
        'get_from_line')

    patient = fields.Function(
        fields.Many2One('gnuhealth.patient', 'Paciente'),
        'get_from_line')

    medicament = fields.Function(
        fields.Many2One('gnuhealth.medicament', 'Medicamento'),
        'get_from_line')

    audit_state = fields.Selection([
        ('pending', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ], 'Estado Auditoría', sort=False,
        states={'readonly': True},
        help='Estado de auditoría para este medicamento')

    audit_notes = fields.Text('Notas',
        states={'readonly': Eval('audit_state') != 'pending'},
        depends=['audit_state'],
        help='Notas sobre la decisión de auditoría para este medicamento')

    audit_date = fields.DateTime('Fecha Auditoría',
        states={'readonly': True},
        help='Fecha en que se auditó este medicamento')

    audit_user = fields.Many2One('res.user', 'Auditor',
        states={'readonly': True},
        help='Usuario que auditó este medicamento')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        table = cls.__table__()
        cls._sql_constraints = [
            ('prescription_line_unique',
                Unique(table, table.prescription_line),
                'Cada línea de medicamento solo puede ser auditada una vez.'),
        ]
        cls._buttons.update({
            'approve_line': {
                'invisible': Eval('audit_state') != 'pending',
                'depends': ['audit_state'],
            },
            'reject_line': {
                'invisible': Eval('audit_state') != 'pending',
                'depends': ['audit_state'],
            },
            'reset_line': {
                'invisible': Eval('audit_state') == 'pending',
                'depends': ['audit_state'],
            },
        })

    @classmethod
    def get_from_line(cls, records, name):
        result = {}
        for record in records:
            line = record.prescription_line
            if not line:
                result[record.id] = None
                continue
            if name == 'prescription':
                result[record.id] = line.name.id if line.name else None
            elif name == 'patient':
                result[record.id] = (
                    line.name.patient.id
                    if line.name and line.name.patient else None)
            elif name == 'medicament':
                result[record.id] = (
                    line.medicament.id if line.medicament else None)
        return result

    @staticmethod
    def default_audit_state():
        return 'pending'

    @classmethod
    def create(cls, vlist):
        Prescription = Pool().get('gnuhealth.prescription.order')
        expanded = []
        for vals in vlist:
            vals = dict(vals)
            source_id = vals.pop('source_prescription', None)
            if source_id:
                prescription = Prescription(source_id)
                existing = cls.search([
                    ('prescription_line.name', '=', prescription.id)])
                existing_ids = {r.prescription_line.id for r in existing}
                for line in prescription.prescription_line:
                    if line.id not in existing_ids:
                        expanded.append({'prescription_line': line.id})
            elif vals.get('prescription_line'):
                expanded.append(vals)
            else:
                raise UserError(
                    'Seleccione una receta en el campo "Cargar Receta".')
        if not expanded:
            return []
        return super().create(expanded)

    @classmethod
    @ModelView.button
    def approve_line(cls, records):
        current_user = Pool().get('res.user')(Transaction().user)
        cls.write(records, {
            'audit_state': 'aprobada',
            'audit_date': datetime.utcnow(),
            'audit_user': current_user.id,
        })
        logger.info(
            'Medication audit record(s) approved by %s', current_user.name)

    @classmethod
    @ModelView.button
    def reject_line(cls, records):
        current_user = Pool().get('res.user')(Transaction().user)
        cls.write(records, {
            'audit_state': 'rechazada',
            'audit_date': datetime.utcnow(),
            'audit_user': current_user.id,
        })
        logger.info(
            'Medication audit record(s) rejected by %s', current_user.name)

    @classmethod
    @ModelView.button
    def reset_line(cls, records):
        cls.write(records, {
            'audit_state': 'pending',
            'audit_date': None,
            'audit_user': None,
        })
        logger.info('Medication audit record(s) reset to pending')


class SelectPrescriptionStart(ModelView):
    'Seleccionar Receta para Auditoría'
    __name__ = 'gnuhealth.medication.audit.select.start'

    prescription = fields.Many2One(
        'gnuhealth.prescription.order', 'Receta',
        required=True,
        help='Receta a cargar en auditoría')


class SelectPrescriptionWizard(Wizard):
    'Cargar Receta en Auditoría'
    __name__ = 'gnuhealth.medication.audit.select'

    start_state = 'start'
    start = StateView(
        'gnuhealth.medication.audit.select.start',
        'health_prescription_audit_v3.view_select_prescription_start',
        [
            Button('Cancelar', 'end', 'tryton-cancel'),
            Button('Confirmar', 'create_records', 'tryton-ok', default=True),
        ])
    create_records = StateTransition()
    open_audit = StateAction(
        'health_prescription_audit_v3.act_medication_audit_v3')

    def transition_create_records(self):
        MedicationAudit = Pool().get('gnuhealth.medication.audit')
        MedicationAudit.create([{
            'source_prescription': self.start.prescription.id,
        }])
        return 'open_audit'


class ExportResult(ModelView):
    'Resultado de Exportación de Auditoría'
    __name__ = 'gnuhealth.medication.audit.export.result'

    csv_file = fields.Binary('Archivo CSV', filename='filename')
    filename = fields.Char('Nombre de archivo', readonly=True)


class PrescriptionAuditExport(Wizard):
    'Exportar Auditoría de Medicamentos a CSV'
    __name__ = 'gnuhealth.medication.audit.export'

    start_state = 'result'
    result = StateView(
        'gnuhealth.medication.audit.export.result',
        'health_prescription_audit_v3.view_audit_export_result',
        [Button('Cerrar', 'end', 'tryton-ok', default=True)])

    _STATE_LABELS = {
        'pending': 'Pendiente',
        'aprobada': 'Aprobada',
        'rechazada': 'Rechazada',
    }

    def default_result(self, fields_names):
        MedicationAudit = Pool().get('gnuhealth.medication.audit')
        active_ids = Transaction().context.get('active_ids') or []

        if active_ids:
            records = MedicationAudit.browse(active_ids)
        else:
            records = MedicationAudit.search([])

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'ID Receta', 'Paciente', 'Medicamento',
            'Estado Auditoría', 'Fecha Auditoría', 'Auditor', 'Notas',
        ])

        for record in records:
            try:
                prescription_id = (
                    record.prescription.prescription_id
                    if record.prescription else '')
            except Exception:
                prescription_id = ''
            try:
                patient_name = (
                    record.patient.rec_name if record.patient else '')
            except Exception:
                patient_name = ''
            try:
                medicament_name = (
                    record.medicament.rec_name if record.medicament else '')
            except Exception:
                medicament_name = ''
            try:
                audit_date = (
                    str(record.audit_date.date()) if record.audit_date else '')
            except Exception:
                audit_date = ''
            try:
                auditor = record.audit_user.name if record.audit_user else ''
            except Exception:
                auditor = ''

            writer.writerow([
                prescription_id,
                patient_name,
                medicament_name,
                self._STATE_LABELS.get(
                    record.audit_state, record.audit_state or ''),
                audit_date,
                auditor,
                record.audit_notes or '',
            ])

        csv_bytes = output.getvalue().encode('utf-8-sig')
        return {
            'csv_file': csv_bytes,
            'filename': 'auditoria_medicamentos.csv',
        }
