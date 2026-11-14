"""El editor y el flujo de emisión comparten integridad sin escribir en BD."""
from copy import deepcopy
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.documentos.presentation.protocolo_seguridad import campo_completo, secciones as secciones_protocolo
from apps.documentos.presentation.validacion_campos_documentales import validar_campos


def campo(clave, etiqueta, tipo, requerido=False, **datos):
    return SimpleNamespace(clave=clave, etiqueta=etiqueta, tipo=tipo, requerido=requerido,
                           columnas=datos.get('columnas', ()), opciones=datos.get('opciones', ()))


def seccion(codigo, titulo, descripcion, campos, **datos):
    return SimpleNamespace(codigo=codigo, titulo=titulo, campos=campos)


EJECUCION = campo('ejecucion_presupuestal', 'Ejecución', 'tabla', columnas=(
    ('item', 'Ítem', 'texto', ()), ('planificado', 'Planificado', 'numero', ()),
    ('ejecutado', 'Ejecutado', 'numero', ()),
    ('estado', 'Estado', 'opcion', (('adquirido', 'Adquirido'), ('no_ejecutado', 'No ejecutado'))),
    ('observacion', 'Observación', 'texto', ()),
))
ACCIONES = campo('acciones', 'Acciones de mejora', 'tabla', columnas=(
    ('hallazgo', 'Hallazgo', 'texto', ()), ('accion', 'Acción', 'texto', ()),
    ('responsable', 'Responsable', 'texto', ()), ('plazo', 'Plazo', 'texto', ()),
    ('estado', 'Estado', 'opcion', (('pendiente', 'Pendiente'), ('en_curso', 'En curso'))),
))
SECCIONES_INFORME = (seccion('informe', 'Informe', '', (EJECUCION, ACCIONES)),)


class ValidacionCamposDocumentalesTests(SimpleTestCase):
    def validar(self, contenido, campos, tipo='informe'):
        return validar_campos(tipo, contenido, (seccion('general', 'General', '', campos),))

    def test_los_campos_requeridos_no_aceptan_html_vacio_ni_estructuras_arbitrarias(self):
        campos = (campo('nombre', 'Nombre', 'texto', True), campo('resumen', 'Resumen', 'rico', True))
        hallazgos = self.validar(dict(nombre={'texto': 'parece lleno'}, resumen='<p>&nbsp;<br></p>'), campos)
        self.assertEqual({h['clave'] for h in hallazgos}, {'nombre', 'resumen'})
        self.assertTrue(all(h['seccion'] == 'general' and h['severidad'] == 'bloqueo' for h in hallazgos))

    def test_los_parrafos_heredados_siguen_validos_y_el_script_no_completa_texto(self):
        campos = (campo('resumen', 'Resumen', 'rico', True),)
        self.assertEqual(self.validar(dict(resumen=['Primer párrafo', 'Segundo párrafo']), campos), [])
        self.assertTrue(self.validar(dict(resumen='<script>Texto no visible</script>'), campos))

    def test_un_selector_requerido_debe_pertenecer_al_catalogo(self):
        campos = (campo('revision_propuestas', 'Revisión', 'opcion', True,
                        opciones=(('revisado', 'He revisado'),)),)
        for valor in ('', 'invalido', {'revisado': True}):
            with self.subTest(valor=valor):
                self.assertTrue(self.validar(dict(revision_propuestas=valor), campos, 'protocolo'))
        self.assertEqual(self.validar(dict(revision_propuestas='revisado'), campos, 'protocolo'), [])

    def test_las_marcas_y_selectores_opcionales_no_aceptan_valores_fuera_del_catalogo(self):
        campos = (campo('sector', 'Sector', 'marcas', True, opciones=(('docencia', 'Docencia'),)),
                  campo('fundamento', 'Fundamento', 'opcion', opciones=(('inicio', 'Inicio'),)))
        self.assertEqual(self.validar(dict(sector=['docencia']), campos), [])
        hallazgos = self.validar(dict(sector=['ajeno'], fundamento='ajeno'), campos)
        self.assertEqual({h['clave'] for h in hallazgos}, {'sector', 'fundamento'})

    def test_estructura_de_contenido_invalida_no_causa_un_error_del_servidor(self):
        self.assertEqual(validar_campos('informe', [], SECCIONES_INFORME)[0]['clave'], 'contenido')
        for valor in ({'item': 'Equipo'}, [None], ['equipo']):
            with self.subTest(valor=valor):
                self.assertTrue(validar_campos('informe', {'ejecucion_presupuestal': valor}, SECCIONES_INFORME))

    def test_las_tablas_opcionales_vacias_no_son_obligaciones_nuevas(self):
        contenido = dict(ejecucion_presupuestal=[dict(item=' ', planificado='', origen='propuesta')], acciones=[{}])
        anterior = deepcopy(contenido)
        self.assertEqual(validar_campos('informe', contenido, SECCIONES_INFORME), [])
        self.assertEqual(contenido, anterior)
        self.assertEqual(validar_campos('informe', {}, SECCIONES_INFORME), [])

    def test_fila_parcial_de_ejecucion_exige_datos_y_no_observacion(self):
        hallazgos = validar_campos('informe', {'ejecucion_presupuestal': [{'item': 'Equipo'}]}, SECCIONES_INFORME)
        self.assertIn('Planificado', hallazgos[0]['mensaje'])
        self.assertIn('Ejecutado', hallazgos[0]['mensaje'])
        self.assertIn('Estado', hallazgos[0]['mensaje'])
        self.assertNotIn('Observación', hallazgos[0]['mensaje'])

    def test_ejecucion_acepta_cero_y_decimales_sin_observacion(self):
        for importe in (0, '0', '10,25', '10.25'):
            with self.subTest(importe=importe):
                contenido = dict(ejecucion_presupuestal=[dict(item='Equipo', planificado=importe,
                                                            ejecutado=0, estado='no_ejecutado')])
                self.assertEqual(validar_campos('informe', contenido, SECCIONES_INFORME), [])

    def test_ejecucion_bloquea_importes_invalidos_y_estados_ajenos(self):
        for importe in ('-1', 'NaN', 'Infinity', '-Infinity', 'monto', True, {'valor': 1}):
            with self.subTest(importe=importe):
                contenido = dict(ejecucion_presupuestal=[dict(item='Equipo', planificado=importe,
                                                            ejecutado='0', estado='adquirido')])
                self.assertTrue(validar_campos('informe', contenido, SECCIONES_INFORME))
        contenido['ejecucion_presupuestal'][0].update(planificado='0', estado='ajeno')
        self.assertIn('catálogo', validar_campos('informe', contenido, SECCIONES_INFORME)[0]['mensaje'])

    def test_accion_parcial_no_pasa_y_el_plazo_conserva_el_formato_libre(self):
        accion = dict(hallazgo='Falta registro', accion='Registrar', responsable='Ana', plazo='2026-08', estado='en_curso')
        for plazo in ('2026-08', 'Durante el siguiente semestre'):
            accion['plazo'] = plazo
            self.assertEqual(validar_campos('informe', {'acciones': [accion]}, SECCIONES_INFORME), [])
        for clave in accion:
            copia = dict(accion, **{clave: ''})
            with self.subTest(clave=clave):
                self.assertTrue(validar_campos('informe', {'acciones': [copia]}, SECCIONES_INFORME))

    def test_protocolo_no_aplica_requiere_actividad_y_justificacion(self):
        secciones = secciones_protocolo(campo, seccion)
        riesgos = next(s for s in secciones if s.codigo == 'riesgos_protocolo').campos[0]
        fila = dict(aplica='no', actividad='Actividad descartada', control='No se realiza en esta unidad')
        self.assertTrue(campo_completo(riesgos, [fila, {}]))
        self.assertEqual(self.validar({'riesgos_protocolo': [fila, {}]}, (riesgos,), 'protocolo'), [])
        for clave in ('actividad', 'control'):
            with self.subTest(clave=clave):
                self.assertTrue(self.validar({'riesgos_protocolo': [dict(fila, **{clave: ''})]}, (riesgos,), 'protocolo'))

    def test_contacto_adicional_es_opcional_pero_una_fila_parcial_no(self):
        secciones = secciones_protocolo(campo, seccion)
        contacto = next(c for s in secciones for c in s.campos if c.clave == 'contactos_emergencia')
        self.assertEqual(self.validar({'contactos_emergencia': [{}]}, (contacto,), 'protocolo'), [])
        self.assertTrue(self.validar({'contactos_emergencia': [{'servicio': 'Aviso interno'}]}, (contacto,), 'protocolo'))

    def test_protocolo_no_rechaza_responsables_y_frecuencias_heredados(self):
        secciones = secciones_protocolo(campo, seccion)
        control = next(c for s in secciones for c in s.campos if c.clave == 'controles_protocolo')
        contenido = dict(controles_protocolo=[dict(control='Inspección', frecuencia='Cada viernes de operación',
                                                  responsable='Responsable registrado al emitir', registro='Bitácora')])
        self.assertEqual(self.validar(contenido, (control,), 'protocolo'), [])
        contenido['controles_protocolo'][0]['registro'] = {'valor': 'bitácora'}
        self.assertFalse(campo_completo(control, contenido['controles_protocolo']))
        self.assertTrue(self.validar(contenido, (control,), 'protocolo'))

    def test_no_duplica_las_reglas_de_presupuesto_que_tienen_alternativa_justificada(self):
        tabla = campo('inversion', 'Presupuesto', 'tabla', columnas=(('item', 'Ítem', 'texto', ()),))
        self.assertEqual(self.validar({'inversion': []}, (tabla,), 'planificacion'), [])

    def test_la_revision_opcional_no_puede_dejar_nombre_o_cargo_suelto(self):
        secciones = (seccion('firmas', 'Firmas', '', (
            campo('revisa_nombre', 'Revisado por', 'texto'), campo('revisa_cargo', 'Cargo', 'texto'))),)
        self.assertEqual(validar_campos('informe', {}, secciones), [])
        self.assertEqual(validar_campos('informe', dict(revisa_nombre='Ana', revisa_cargo='Coordinación'), secciones), [])
        for contenido in (dict(revisa_nombre='Ana'), dict(revisa_cargo='Coordinación')):
            with self.subTest(contenido=contenido):
                self.assertTrue(validar_campos('informe', contenido, secciones))
