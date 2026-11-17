from io import BytesIO
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import ExitStack

from django.test import SimpleTestCase
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from pypdf import PdfReader

from apps.core.presentation.pdf_institucional import ALTO_ENCABEZADO, ANCHO_LOGO, ANCHO_METADATOS, _bloques_encabezado


class EncabezadoPdfTests(SimpleTestCase):
    def test_documento_usa_una_familia_y_sangria_real_sin_imprimir_contador_de_generacion(self):
        from apps.documentos.presentation.expediente_pdf import render_documento_pdf
        identidad = (SimpleNamespace(codigo='PRUEBA'),
                     SimpleNamespace(nombre='Institución de prueba', siglas='IP', paleta={}))
        compuesto = dict(tipo='informe', titulo='Informe de prueba', codigo_formato='FORMATO-01', version=7,
            unidad=SimpleNamespace(nombre='Unidad de prueba'), periodo='2026-B',
            tramo=(date(2026, 1, 1), date(2026, 12, 31)), firmas=[],
            secciones=[dict(numero=1, codigo='contenido', titulo='CONTENIDO INSTITUCIONAL', bloques=[
                dict(tipo='subtitulo', texto='Criterio de prueba'),
                dict(tipo='parrafo', texto='Párrafo breve de prueba.'),
                dict(tipo='lista', items=['Elemento breve de prueba.']),
                dict(tipo='rico', bloques=[dict(tipo='lista', ordenada=True, items=[
                    dict(html='Elemento numerado.', sub=[dict(tipo='lista', ordenada=False,
                        items=[dict(html='Elemento subordinado.', sub=[])])])])]),
            ])])
        with ExitStack() as pila:
            for modulo in ('apps.core.presentation.identidad', 'apps.core.presentation.pdf_institucional',
                           'apps.documentos.presentation.expediente_pdf'):
                pila.enter_context(patch(modulo+'.identidad_actual', return_value=identidad))
            for modulo in ('apps.core.presentation.identidad', 'apps.core.presentation.pdf_institucional'):
                pila.enter_context(patch(modulo+'.logo_institucional', return_value=None))
            pdf = PdfReader(BytesIO(render_documento_pdf(compuesto)))
            # Lo que no es documento principal conserva el encabezado de tres columnas. El número de versión
            # es un contador interno de archivos y no se imprime.
            anexo = PdfReader(BytesIO(render_documento_pdf(dict(compuesto, tipo='mejora'))))
        texto_anexo = '\n'.join(p.extract_text() or '' for p in anexo.pages)
        self.assertIn('Revisión: 01', texto_anexo)
        self.assertNotIn('Versión', texto_anexo)
        posiciones, fuentes = {}, set()
        def recoger(texto, cm, tm, fuente, tamano):
            if texto.strip():
                fuentes.add(str((fuente or {}).get('/BaseFont', '')).split('+')[-1].lstrip('/'))
            for etiqueta in ('Criterio de prueba', 'Párrafo breve de prueba.', 'Elemento breve de prueba.',
                             'Elemento numerado.', 'Elemento subordinado.'):
                if etiqueta in texto:
                    posiciones[etiqueta] = cm[0]*tm[4]+cm[2]*tm[5]+cm[4]
        texto = '\n'.join(p.extract_text(visitor_text=recoger) or '' for p in pdf.pages)
        # El informe es documento principal: su encabezado lleva código y cobertura, sin versión; nunca en el cuerpo.
        self.assertNotIn('Versión:', texto)
        self.assertNotIn('Versión del documento:', texto)
        self.assertEqual(fuentes, {'LiberationSans', 'LiberationSans-Bold'})
        self.assertGreater(posiciones['Párrafo breve de prueba.'], posiciones['Criterio de prueba'])
        self.assertGreater(posiciones['Elemento breve de prueba.'], posiciones['Párrafo breve de prueba.'])
        self.assertGreater(posiciones['Elemento subordinado.'], posiciones['Elemento numerado.'])

    def _renderizar_reporte_sin_bd(self, reporte):
        from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf
        identidad = (SimpleNamespace(codigo='PRUEBA'),
                     SimpleNamespace(nombre='Institución de prueba', siglas='IP', paleta={}))
        with ExitStack() as pila:
            for modulo in ('apps.core.presentation.pdf_institucional',
                           'apps.gestion_unidades.presentation.gestion_reportes'):
                pila.enter_context(patch(modulo + '.identidad_actual', return_value=identidad))
            pila.enter_context(patch('apps.core.presentation.pdf_institucional.logo_institucional', return_value=None))
            return PdfReader(BytesIO(render_unit_report_pdf(reporte)))

    def _cuerpo_de_pagina(self, pagina):
        textos = []
        def recoger(texto, cm, tm, fuente, tamano):
            y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
            if 40 < y < float(pagina.mediabox.height) - 105:
                textos.append(texto)
        pagina.extract_text(visitor_text=recoger)
        return ''.join(textos)

    def _reporte_base(self):
        from datetime import datetime
        return dict(category='mantenimiento', category_label='Mantenimiento de equipos', scope_label='Unidad de prueba',
            start_date=date(2026, 8, 17), end_date=date(2026, 12, 8),
            generated_at=datetime(2026, 12, 9, 9), filter_summary=[], is_generic=True)

    def test_la_banda_de_mantenimiento_permanece_con_las_primeras_filas(self):
        reporte = self._reporte_base()
        reporte['dataset'] = dict(headers=['Identificación de equipo y referencia patrimonial. ' * 20, 'Procedimiento'],
            rows=[['EQUIPO-CENTINELA', 'Resultado documentado. ' * 10]],
            document_meta={'title': 'SECCIÓN DEL MANTENIMIENTO'},
            notes=['Nota de contexto: alcance, período y responsabilidad de la intervención.'] * 20)
        pdf = self._renderizar_reporte_sin_bd(reporte)
        paginas_con_banda = [self._cuerpo_de_pagina(p) for p in pdf.pages
                            if 'SECCIÓN DEL MANTENIMIENTO' in self._cuerpo_de_pagina(p)]
        self.assertTrue(paginas_con_banda)
        self.assertTrue(all('EQUIPO-CENTINELA' in texto for texto in paginas_con_banda))

    def test_la_banda_complementaria_permanece_con_el_inicio_de_su_tabla(self):
        reporte = self._reporte_base()
        reporte['dataset'] = dict(headers=['Equipo', 'Estado'], rows=[['Equipo', 'Disponible']],
            notes=['Nota de contexto: alcance, período y responsabilidad de la intervención.'] * 14,
            tablas=[dict(titulo='DETALLE COMPLEMENTARIO',
                headers=['Identificación de orden de mantenimiento y referencia. ' * 20, 'Resultado'], rows=[
                ['ORDEN-CENTINELA', 'Resultado documentado. ' * 10]])])
        pdf = self._renderizar_reporte_sin_bd(reporte)
        paginas_con_banda = [self._cuerpo_de_pagina(p) for p in pdf.pages
                            if 'DETALLE COMPLEMENTARIO' in self._cuerpo_de_pagina(p)]
        self.assertTrue(paginas_con_banda)
        self.assertTrue(all('ORDEN-CENTINELA' in texto for texto in paginas_con_banda))

    def test_tabla_larga_empieza_en_la_primera_pagina_sin_arrastrar_todas_las_filas(self):
        reporte = self._reporte_base()
        reporte['dataset'] = dict(headers=['Referencia', 'Resultado documentado'],
            rows=[[f'REGISTRO-{n:03}', 'Detalle de seguimiento y comprobación. ' * 5] for n in range(100)],
            notes=['Los resultados pendientes conservan su estado real.'])
        pdf = self._renderizar_reporte_sin_bd(reporte)
        self.assertGreater(len(pdf.pages), 1)
        self.assertIn('REGISTRO-000', self._cuerpo_de_pagina(pdf.pages[0]))
        self.assertIn('REGISTRO-099', ''.join(p.extract_text() for p in pdf.pages))

    def test_reporte_ancho_se_lee_por_bloques_y_conserva_todos_los_campos(self):
        reporte=self._reporte_base()
        reporte.update(category='asignaturas',category_label='Planificación semestral de prácticas por asignatura')
        campos=[f'Campo {i}' for i in range(12)]
        valores=[0,*[f'DATO_CONSERVADO_{i}' for i in range(1,12)]]
        reporte['dataset']=dict(headers=['Asignatura','Sesión',*campos],
            rows=[['ASIGNATURA-CENTINELA','1',*valores]])
        pdf=self._renderizar_reporte_sin_bd(reporte)
        texto='\n'.join(p.extract_text() or '' for p in pdf.pages)
        normalizado=''.join(texto.split())
        for valor in valores[1:]:
            self.assertIn(valor,normalizado)
        for campo in campos:
            self.assertIn(''.join(campo.split()),normalizado)
        self.assertRegex(texto,r'\s0\s')
        self.assertIn('Responsables y respaldo docente',texto)

    def test_tabla_complementaria_larga_aprovecha_el_espacio_de_la_primera_pagina(self):
        reporte = self._reporte_base()
        reporte['dataset'] = dict(headers=['Referencia', 'Estado'], rows=[['PRINCIPAL', 'Disponible']],
            tablas=[dict(titulo='RESULTADOS COMPLEMENTARIOS', headers=['Referencia', 'Comprobación'],
                rows=[[f'COMPLEMENTO-{n:03}', 'Seguimiento y resultado. ' * 5] for n in range(100)])])
        pdf = self._renderizar_reporte_sin_bd(reporte)
        self.assertGreater(len(pdf.pages), 1)
        self.assertIn('COMPLEMENTO-000', self._cuerpo_de_pagina(pdf.pages[0]))
        self.assertIn('COMPLEMENTO-099', ''.join(p.extract_text() for p in pdf.pages))

    def test_un_valor_cero_sigue_visible_como_dato_en_el_pdf(self):
        reporte = self._reporte_base()
        reporte['dataset'] = dict(headers=['Referencia', 'Cantidad'], rows=[['REGISTRO-CERO', 0]])
        pdf = self._renderizar_reporte_sin_bd(reporte)
        self.assertRegex(pdf.pages[0].extract_text(), r'REGISTRO-CERO\s+0')

    def test_reservas_escapan_texto_editable_y_ajustan_grupos_largos(self):
        from datetime import time
        reporte = self._reporte_base()
        grupo = 'Investigación aplicada y colaboración interdisciplinaria ' * 9
        reserva = SimpleNamespace(codigo_reserva='RESERVA-001', fecha=date(2026, 9, 1),
            hora_inicio=time(8), hora_fin=time(9), titulo_solicitud='Uso <impresora & corte>',
            nombre_completo_solicitante='Ana <Responsable>', responsable_asignado_id=None,
            get_tipo_solicitud_display=lambda: 'Trabajo <académico>', tipo_solicitud_reportado='Trabajo <académico>',
            get_estado_display=lambda: 'Completada', es_efectiva=True,
            detalle_ejecucion={'asistentes_total': 2}, numero_participantes=2)
        reporte.update(is_generic=False, category='reservas', category_label='Registro de uso',
            metrics=dict(total=1, confirmed=1, hours=1, participants=2), group_label='Propósito',
            rows=[dict(label=grupo, total=1, hours=1, participants=2, percentage=100)],
            reservations=[reserva])
        pdf = self._renderizar_reporte_sin_bd(reporte)
        texto = ''.join(p.extract_text() for p in pdf.pages)
        self.assertIn('Uso <impresora & corte>', texto)
        self.assertIn('Ana <Responsable>', texto)
        self.assertIn('Trabajo <académico>', ' '.join(texto.split()))

    def test_seis_practicas_y_su_control_documental_caben_sin_una_fila_huerfana(self):
        reporte = self._reporte_base()
        reporte.update(category='planificaciones', category_label='FT02 · Planificación de uso de laboratorios',
            scope_label='Laboratorio de Fabricación Digital y Prototipado')
        codigos = [f'PL-26-{n:04d}' for n in range(1, 7)]
        fila = ['24/08/2026', '08:00', '10:00', 'Computación', 'Quinto',
            'Diseño y fabricación digital', 'Docente responsable de la asignatura',
            'Área de fabricación aditiva', 'GUIA-FAB-01 · v1',
            'Diseño y comprobación de un prototipo funcional',
            'Modela un soporte con parámetros dimensionales y comprueba restricciones y tolerancias.',
            '4', 'Docencia', 'Laboratorio de Fabricación Digital y Prototipado', 'Responsable técnico']
        reporte['dataset'] = dict(matrix=True, matrix_kind='planificaciones',
            headers=['N.º planif.', 'Fecha', 'Hora inicio', 'Hora fin', 'Carrera', 'Nivel',
                'Asignatura', 'Docente', 'Escenario', 'Código guía', 'Tema', 'Resultado de aprendizaje',
                'Estudiantes', 'Categoría', 'Laboratorio', 'Responsable técnico'],
            rows=[[codigo, *fila] for codigo in codigos],
            notes=['El FT02 registra la programación; la ejecución se comprueba por separado.'],
            tablas=[dict(titulo='Comprobación del respaldo documental',
                headers=['Código de práctica', 'Respaldo completo', 'Pendientes por completar'],
                rows=[[codigo, 'Sí', 'Completo'] for codigo in codigos])])
        pdf = self._renderizar_reporte_sin_bd(reporte)
        self.assertEqual(len(pdf.pages), 1)
        texto = pdf.pages[0].extract_text()
        for codigo in codigos:
            self.assertEqual(texto.count(codigo), 2)

    def test_matrices_ft02_y_ft03_respetan_los_margenes_de_la_hoja(self):
        from datetime import datetime
        from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf

        institucion = SimpleNamespace(nombre='Institución de prueba', siglas='IP', paleta={})
        identidad = (SimpleNamespace(codigo='PRUEBA'), institucion)
        reporte = {
            'category': 'planificaciones', 'category_label': 'FT02', 'scope_label': 'Unidad',
            'start_date': date(2026, 8, 17), 'end_date': date(2026, 12, 8),
            'generated_at': datetime(2026, 10, 16, 12), 'filter_summary': [], 'is_generic': True,
            'dataset': {'matrix': True, 'matrix_kind': 'planificaciones',
                        'headers': ['Campo'] * 16, 'rows': [['Dato'] * 16]},
        }
        contenidos = []
        with ExitStack() as pila:
            for modulo in ('apps.core.presentation.pdf_institucional',
                           'apps.gestion_unidades.presentation.gestion_reportes'):
                pila.enter_context(patch(modulo + '.identidad_actual', return_value=identidad))
            pila.enter_context(patch('apps.core.presentation.pdf_institucional.logo_institucional', return_value=None))
            for codigo, columnas in (('planificaciones', 16), ('ejecuciones', 13), ('planificaciones', 17)):
                reporte['dataset'].update(matrix_kind=codigo, headers=['Campo'] * columnas,
                                          rows=[['Dato'] * columnas])
                contenidos.append(render_unit_report_pdf(reporte))
        for pagina in (p for contenido in contenidos for p in PdfReader(BytesIO(contenido)).pages):
            extremos = []

            def recoger_lineas(operador, argumentos, matriz, _texto):
                if operador in (b'm', b'l'):
                    x, y = map(float, argumentos[:2])
                    extremos.append(matriz[0] * x + matriz[2] * y + matriz[4])

            pagina.extract_text(visitor_operand_before=recoger_lineas)
            self.assertTrue(extremos)
            self.assertGreaterEqual(min(extremos), 13 * mm - .1)
            self.assertLessEqual(max(extremos), float(pagina.mediabox.width) - 13 * mm + .1)

    def test_formacion_previa_y_descarga_repiten_identidad_en_todas_las_paginas(self):
        from datetime import datetime
        from apps.gestion_unidades.presentation.gestion_reportes import render_unit_report_pdf
        from apps.gestion_unidades.presentation.exportaciones_reportes import descargar_unidad

        institucion = SimpleNamespace(nombre='Institución de prueba', siglas='IP', paleta={})
        reporte = {
            'category': 'cursos', 'category_label': 'Formación: cursos, inscripciones y certificados',
            'scope_label': 'Unidad de prueba', 'unit': SimpleNamespace(slug='prueba'),
            'start_date': date(2026, 8, 17), 'end_date': date(2026, 12, 8),
            'generated_at': datetime(2026, 10, 16, 12), 'filter_summary': [], 'is_generic': True,
            'dataset': {'cards': [], 'headers': ['Código', 'Curso'],
                        'rows': [[str(i), 'Contenido del curso ' * 20] for i in range(80)]},
        }
        with ExitStack() as pila:
            pila.enter_context(patch('apps.core.presentation.pdf_institucional.identidad_actual',
                                     return_value=(SimpleNamespace(codigo='PRUEBA'), institucion)))
            pila.enter_context(patch('apps.core.presentation.pdf_institucional.logo_institucional', return_value=None))
            for contenido in (render_unit_report_pdf(reporte), descargar_unidad(reporte, 'pdf').content):
                pdf = PdfReader(BytesIO(contenido))
                self.assertGreater(len(pdf.pages), 1)
                for indice, pagina in enumerate(pdf.pages, 1):
                    texto = pagina.extract_text()
                    self.assertIn('INSTITUCIÓN DE PRUEBA', texto)
                    self.assertIn('Centro de reportes', texto)
                    self.assertIn('17/08/2026', texto)
                    self.assertIn(f'Página: {indice} de {len(pdf.pages)}', texto)

    def test_maquetas_toman_la_paleta_por_documento_sin_colores_globales(self):
        from apps.laboratorios.operacion.presentation.maquetas_pdf import MaquetaPDF
        with patch('apps.laboratorios.operacion.presentation.maquetas_pdf.colores_institucionales',
                   return_value={'oscuro': colors.navy}):
            azul = MaquetaPDF('asistencia')
        with patch('apps.laboratorios.operacion.presentation.maquetas_pdf.colores_institucionales',
                   return_value={'oscuro': colors.maroon}):
            rojo = MaquetaPDF('asistencia')
        self.assertEqual(azul.base.textColor, colors.navy)
        self.assertEqual(rojo.base.textColor, colors.maroon)

    def test_fila_extensa_del_expediente_continua_en_otras_paginas(self):
        from apps.documentos.presentation.expediente_pdf import render_documento_pdf
        from apps.core.presentation.pdf_institucional import marco_institucional
        institucion = SimpleNamespace(nombre='Institución de prueba', siglas='IP', paleta={})
        identidad = (SimpleNamespace(codigo='PRUEBA'), institucion)
        compuesto = {
            'tipo': 'informe',
            'titulo': 'Informe de prueba', 'codigo_formato': 'FORMATO-01',
            'unidad': SimpleNamespace(nombre='Unidad de prueba'), 'periodo': '2026-B',
            'tramo': (date(2026, 1, 1), date(2026, 12, 31)), 'firmas': [],
            'secciones': [{'numero': 1, 'titulo': 'Hallazgos', 'bloques': [
                {'tipo': 'pares', 'pares': [('Observaciones', 'Detalle ' * 3000)]},
                {'tipo': 'parrafo', 'texto': 'FIN DE LOS HALLAZGOS'},
            ]}],
        }
        with patch('apps.core.presentation.pdf_institucional.identidad_actual', return_value=identidad), \
                patch('apps.core.presentation.pdf_institucional.logo_institucional', return_value=None), \
                patch('apps.documentos.presentation.expediente_pdf.identidad_actual', return_value=identidad), \
                patch('apps.documentos.presentation.expediente_pdf.marco_institucional', wraps=marco_institucional) as marco:
            contenido = render_documento_pdf(compuesto)
        self.assertTrue(contenido.startswith(b'%PDF'))
        self.assertGreater(contenido.count(b'/Type /Page\n'), 1)
        # Documento principal: encabezado del informe institucional, con su título sin «Formato».
        self.assertEqual(marco.call_args.kwargs['estilo'], 'informe')
        self.assertEqual(marco.call_args.kwargs['formato'], 'Informe de prueba')
        self.assertEqual(tuple(marco.call_args.kwargs['metadatos']), ('Código: FORMATO-01', 'Cobertura: 2026-B'))

    def test_titulo_y_codigo_largos_quedan_dentro_de_sus_columnas(self):
        ancho = 182 * mm
        for repeticiones in (1, 4):
            with self.subTest(repeticiones=repeticiones):
                centro, derecha = _bloques_encabezado(
                    'FORMATO INFORME DE INCUMPLIMIENTO Y MEJORA CONTINUA ' * repeticiones,
                    'UNIVERSIDAD POLITÉCNICA ESTATAL DEL CARCHI',
                    ['Código: AP-P-LAP-GO - Mejora continua ' * repeticiones,
                     'Revisión: 01', 'Período: 2026-B', 'Versión: 2'],
                    ancho, {'oscuro': colors.black},
                )
                canvas = Canvas(BytesIO())
                alto_maximo = ALTO_ENCABEZADO - 4 * mm
                for bloque, ancho_maximo in (
                    (centro, ancho - ANCHO_LOGO - ANCHO_METADATOS - 6 * mm),
                    (derecha, ANCHO_METADATOS - 6 * mm),
                ):
                    ancho_real, alto_real = bloque.wrapOn(canvas, ancho_maximo, alto_maximo)
                    self.assertLessEqual(ancho_real, ancho_maximo)
                    self.assertLessEqual(alto_real, alto_maximo)
                    bloque.drawOn(canvas, 0, 0)
