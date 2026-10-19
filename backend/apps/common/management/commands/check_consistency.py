"""Verifica que la cache de stock coincida con el libro mayor.

Uso:
    python manage.py check_consistency

Devuelve codigo de salida 1 si encuentra diferencias, para poder usarlo en CI.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.inventory.services import find_consistency_issues


class Command(BaseCommand):
    help = "Compara el stock almacenado con la suma de los movimientos de inventario."

    def handle(self, *args, **options):
        issues = find_consistency_issues()
        if not issues:
            self.stdout.write(self.style.SUCCESS("Inventario consistente: sin diferencias."))
            return

        self.stdout.write(
            self.style.ERROR(f"Se encontraron {len(issues)} lote(s) con diferencias:")
        )
        for issue in issues:
            self.stdout.write(
                f"  lote {issue['lot_id']} · {issue['product']} · {issue['batch_number']}: "
                f"cache={issue['cached']} libro={issue['ledger']} "
                f"diferencia={issue['difference']}"
            )
        raise CommandError("El inventario no es consistente.")
