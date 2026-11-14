from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[2]


class BackupContractTests(SimpleTestCase):
    def test_respaldo_de_base_es_atomico_verificado_y_sin_claves_por_defecto(self):
        script = (ROOT / "scripts" / "backup_database.sh").read_text(encoding="utf-8")

        self.assertIn("set -eu", script)
        self.assertIn("umask 077", script)
        self.assertIn("require_env DB_PASSWORD", script)
        self.assertIn("--format=custom", script)
        self.assertIn("pg_restore --list", script)
        self.assertIn("sha256sum", script)
        self.assertNotIn("DB_PASSWORD:-postgres", script)

    def test_adjuntos_tambien_tienen_respaldo_verificable(self):
        script = (ROOT / "scripts" / "backup_media.sh").read_text(encoding="utf-8")

        self.assertIn("tar -tzf", script)
        self.assertIn("sha256sum", script)
        self.assertIn("umask 077", script)

    def test_existe_ensayo_de_restauracion_en_base_efimera(self):
        script = (ROOT / "scripts" / "verify_database_backup.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("createdb", script)
        self.assertIn("pg_restore", script)
        self.assertIn("dropdb --if-exists", script)
        self.assertIn("SELECT 1", script)
