"""Defensa adicional de datos privados. La agenda compartida conserva su contrato de disponibilidad."""
from django.db import migrations

UID = "COALESCE(NULLIF(current_setting('slcid.user_id', true), ''), '0')::bigint"
UNITS = "COALESCE(NULLIF(current_setting('slcid.units', true), ''), '')"
SUPER = "COALESCE(current_setting('slcid.superuser', true), '') = 'on'"
UNIT_SCOPE = f"ANY(string_to_array({UNITS}, ',')::bigint[])"
COURSE = """EXISTS (
    SELECT 1 FROM webcitt_inscripcioncurso i
    JOIN webcitt_edicioncurso e ON e.id = i.edicion_id
    JOIN webcitt_curso c ON c.id = e.curso_id
    WHERE i.id = {table}.inscripcion_id AND (i.usuario_id = {uid} OR c.unidad_id = {scope})
)"""
POLICIES = {
    'webcitt_simulacionguardada': f'autor_id = {UID}',
    'webcitt_intentoejercicio': f"""estudiante_id = {UID} OR EXISTS (
        SELECT 1 FROM webcitt_ejercicioaula e WHERE e.id = ejercicio_id
        AND (e.creado_por_id = {UID} OR e.unidad_id = {UNIT_SCOPE}))""",
}
for table in ('webcitt_progresoleccion', 'webcitt_intentoevaluacion', 'webcitt_entregadeber', 'webcitt_pagoinscripcion'):
    POLICIES[table] = COURSE.format(table=table, uid=UID, scope=UNIT_SCOPE)


def install(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for table, rule in POLICIES.items():
        schema_editor.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        schema_editor.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
        schema_editor.execute(f'CREATE POLICY slcid_personal ON {table} '
                              f'USING (({SUPER}) OR ({rule})) WITH CHECK (({SUPER}) OR ({rule}))')


def remove(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    for table in POLICIES:
        schema_editor.execute(f'DROP POLICY IF EXISTS slcid_personal ON {table}')
        schema_editor.execute(f'ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY')
        schema_editor.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY')


class Migration(migrations.Migration):
    dependencies = [('webcitt', '0313_contador_peticion')]
    operations = [migrations.RunPython(install, remove)]
