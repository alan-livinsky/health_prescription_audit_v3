# SPDX-FileCopyrightText: 2024 Custom GNU Health
# SPDX-License-Identifier: GPL-3.0-or-later

from trytond.pool import Pool
from . import health_prescription_audit


def register():
    Pool.register(
        health_prescription_audit.MedicationPurchasePackage,
        health_prescription_audit.MedicationAudit,
        health_prescription_audit.CreatePackageStart,
        health_prescription_audit.SelectPrescriptionStart,
        health_prescription_audit.ExportResult,
        module='health_prescription_audit_v3', type_='model')
    Pool.register(
        health_prescription_audit.CreatePackageWizard,
        health_prescription_audit.SelectPrescriptionWizard,
        health_prescription_audit.PrescriptionAuditExport,
        module='health_prescription_audit_v3', type_='wizard')
