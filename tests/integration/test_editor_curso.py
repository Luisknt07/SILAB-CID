"""Edición completa del curso, con el mismo alcance desde ficha y gestión."""
from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.formacion.models.cursos import Curso, EdicionCurso, EntregaDeber, InscripcionCurso, IntentoEvaluacion, LeccionCurso, ModuloCurso, PreguntaEvaluacion, ProgresoLeccion
from apps.gestion_unidades.models.espacios import ResponsableUnidad
from apps.directorio_unidades.models.core import Unidad
from tests.integration.utiles import identificar


class EditorCursoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model()
        cls.gestor = usuarios.objects.create_user('editor-curso-gestor', password='clave')
        cls.tecnico = usuarios.objects.create_user('editor-curso-tecnico', password='clave')
        cls.participante = usuarios.objects.create_user('editor-curso-alumno', password='clave')
        for persona in (cls.gestor, cls.tecnico):
            identificar(persona, tipo_usuario='administrativo', carrera='')
        identificar(cls.participante, tipo_usuario='estudiante')
        cls.unidad = Unidad.objects.create(
            nombre='Laboratorio editor integral', slug='lab-editor-integral',
            dependencia='laboratorios', administrador=cls.gestor, descripcion='Prueba',
            fecha_inicio=date(2026, 1, 1),
        )
        cls.otra_unidad = Unidad.objects.create(
            nombre='Otro laboratorio editor', slug='otro-lab-editor-integral',
            dependencia='laboratorios', descripcion='Prueba', fecha_inicio=date(2026, 1, 1),
        )
        cls.responsable = ResponsableUnidad.objects.create(
            unidad=cls.unidad, usuario=cls.tecnico, rol='responsable_tecnico',
            permisos_operativos={'practicas': False}, activo=True,
        )
        cls.curso = Curso.objects.create(
            unidad=cls.unidad, codigo='EDITOR-CUR-001', nombre='Curso integral sin publicar',
            publicado=False, duracion_horas=40, emite_certificado=False,
        )
        cls.otro_curso = Curso.objects.create(
            unidad=cls.otra_unidad, codigo='EDITOR-CUR-AJENO', nombre='Curso ajeno reservado',
            publicado=False,
        )
        cls.modulo = ModuloCurso.objects.create(curso=cls.curso, titulo='Operaciones logísticas', orden=1)
        cls.vacio = ModuloCurso.objects.create(curso=cls.curso, titulo='Módulo todavía vacío', orden=2)
        cls.lectura = LeccionCurso.objects.create(
            modulo=cls.modulo, titulo='Lectura publicada', tipo='texto', orden=1,
            contenido='Texto original', publicada=True,
        )
        cls.examen = LeccionCurso.objects.create(
            modulo=cls.modulo, titulo='Evaluación todavía en borrador', tipo='evaluacion', orden=2,
            publicada=False, nota_minima=70, intentos=3,
        )
        cls.pregunta = PreguntaEvaluacion.objects.create(
            leccion=cls.examen, enunciado='Pregunta privada del borrador', tipo='unica',
            opciones='*Inventario\nVentas', explicacion='La cantidad disponible.',
        )
        cls.deber = LeccionCurso.objects.create(
            modulo=cls.modulo, titulo='Proyecto final', tipo='deber', orden=3,
        )
        cls.modulo_ajeno = ModuloCurso.objects.create(curso=cls.otro_curso, titulo='Módulo ajeno')
        cls.leccion_ajena = LeccionCurso.objects.create(
            modulo=cls.modulo_ajeno, titulo='Lección ajena', tipo='texto',
        )
        cls.grupo = EdicionCurso.objects.create(curso=cls.curso, nombre='Grupo editor', anio=2026)
        cls.inscripcion = InscripcionCurso.objects.create(
            edicion=cls.grupo, usuario=cls.participante, estado='aceptada',
        )

    def setUp(self):
        self.client.force_login(self.gestor)
        self.url = reverse('editor_curso', args=[self.unidad.slug, self.curso.codigo])

    def registro_url(self, clave, pk):
        return reverse('editar_registro', args=[self.unidad.slug, clave, pk])

    @staticmethod
    def datos_leccion(leccion, **cambios):
        datos = {
            'registro-orden': str(leccion.orden), 'registro-titulo': leccion.titulo,
            'registro-tipo': leccion.tipo, 'registro-contenido': leccion.contenido,
            'registro-sala': leccion.sala, 'registro-nota_minima': '7',
            'registro-intentos': str(leccion.intentos),
            'registro-obligatoria': 'on', 'registro-publicada': 'on',
        }
        datos.update(cambios)
        return datos

    def comprobar_rechazo_sin_guardar(self, respuesta):
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['formulario'].errors)

    def test_editor_exige_sesion_y_permiso_de_cursos(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        for usuario in (self.participante, self.tecnico):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                self.assertEqual(self.client.get(self.url).status_code, 403)
        self.responsable.permisos_operativos = {'practicas': True}
        self.responsable.save(update_fields=['permisos_operativos'])
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_editor_consulta_solo_curso_de_su_unidad_activa(self):
        cruzada = reverse('editor_curso', args=[self.unidad.slug, self.otro_curso.codigo])
        self.assertEqual(self.client.get(cruzada).status_code, 404)
        ajena = reverse('editor_curso', args=[self.otra_unidad.slug, self.otro_curso.codigo])
        self.assertEqual(self.client.get(ajena).status_code, 403)
        Unidad.objects.filter(pk=self.unidad.pk).update(activo=False)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_editor_es_get_privado_y_no_modifica_el_curso(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('no-store', respuesta['Cache-Control'])
        self.assertEqual(self.client.post(self.url, {'publicado': 'on'}).status_code, 405)
        self.curso.refresh_from_db()
        self.assertFalse(self.curso.publicado)

    def test_editor_incluye_arbol_completo_borradores_modulos_vacios_y_preguntas(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        editor = respuesta.context['editor']
        self.assertEqual([fila['modulo'].pk for fila in editor['modulos']],
                         [self.modulo.pk, self.vacio.pk])
        self.assertEqual(editor['modulos'][1]['lecciones'], [])
        lecciones = editor['modulos'][0]['lecciones']
        self.assertEqual([fila['leccion'].pk for fila in lecciones],
                         [self.lectura.pk, self.examen.pk, self.deber.pk])
        self.assertEqual([fila['pregunta'].pk for fila in lecciones[1]['preguntas']], [self.pregunta.pk])
        self.assertTrue(lecciones[1]['nueva_pregunta_url'])
        self.assertFalse(lecciones[0]['nueva_pregunta_url'])
        self.assertEqual(editor['resumen'], {
            'modulos': 2, 'lecciones': 3, 'evaluaciones': 1, 'deberes': 1, 'preguntas': 1,
        })
        self.assertNotContains(respuesta, self.otro_curso.nombre)
        self.assertNotContains(respuesta, self.leccion_ajena.titulo)

    def test_enlaces_del_editor_conservan_padres_y_regreso_al_programa(self):
        editor = self.client.get(self.url).context['editor']
        nuevo_modulo = urlsplit(editor['nuevo_modulo_url'])
        self.assertEqual(nuevo_modulo.path, self.registro_url('modulo_curso', 'nuevo'))
        consulta = parse_qs(nuevo_modulo.query)
        self.assertEqual(consulta['padre'], [str(self.curso.pk)])
        self.assertEqual(consulta['volver'], [self.url + '#programa'])
        leccion = editor['modulos'][0]['lecciones'][1]
        nueva_pregunta = urlsplit(leccion['nueva_pregunta_url'])
        self.assertEqual(nueva_pregunta.path, self.registro_url('pregunta_curso', 'nuevo'))
        self.assertEqual(parse_qs(nueva_pregunta.query)['padre'], [str(self.examen.pk)])
        self.assertEqual(urlsplit(leccion['editar_url']).path,
                         self.registro_url('leccion_curso', self.examen.pk))

    def test_gestion_ficha_y_aula_abren_el_mismo_editor_completo(self):
        panel = self.client.get(reverse('gestion_unidad', args=[self.unidad.slug]), {'view': 'cursos'})
        self.assertEqual(panel.status_code, 200)
        fila = next(fila for fila in panel.context['cursos_gestion']['cursos']
                    if fila['curso'].pk == self.curso.pk)
        self.assertEqual(urlsplit(fila['urls']['editar']).path, self.url)
        for nombre in ('curso_unidad', 'aula_curso'):
            with self.subTest(pagina=nombre):
                respuesta = self.client.get(reverse(nombre, args=[self.unidad.slug, self.curso.codigo]))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, self.url)

    def test_ficha_publica_no_muestra_editor_ni_preguntas_privadas(self):
        Curso.objects.filter(pk=self.curso.pk).update(publicado=True)
        self.client.logout()
        respuesta = self.client.get(reverse('curso_unidad', args=[self.unidad.slug, self.curso.codigo]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, self.url)
        self.assertNotContains(respuesta, self.pregunta.enunciado)

    def test_presentacion_se_guarda_sin_alterar_programa_y_datos_no_editados(self):
        respuesta = self.client.post(self.registro_url('curso', self.curso.pk), {
            'grupo': 'presentacion', 'registro-nombre': 'Curso logístico actualizado',
            'registro-lema': 'Aplicaciones para operaciones reales',
            'registro-clasificacion': 'corto', 'registro-modalidad': 'mixto',
            'registro-publicado': 'on',
        }, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        self.curso.refresh_from_db()
        self.assertEqual(self.curso.nombre, 'Curso logístico actualizado')
        self.assertEqual(self.curso.duracion_horas, 40)
        self.assertEqual(self.curso.modulos.count(), 2)
        self.assertEqual(LeccionCurso.objects.filter(modulo__curso=self.curso).count(), 3)

    def test_nuevo_modulo_y_pregunta_reutilizan_validaciones_y_unidad(self):
        respuesta = self.client.post(self.registro_url('modulo_curso', 'nuevo'), {
            'padre': self.curso.pk, 'registro-orden': '3', 'registro-titulo': 'Distribución',
            'registro-descripcion': 'Gestión de entregas',
        }, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        self.assertTrue(self.curso.modulos.filter(titulo='Distribución').exists())
        pregunta_url = self.registro_url('pregunta_curso', 'nuevo')
        datos = {
            'padre': self.examen.pk, 'registro-orden': '2',
            'registro-enunciado': '¿Qué identifica un producto?', 'registro-tipo': 'unica',
            'registro-opciones': '*SKU\nPasillo', 'registro-puntos': '2',
            'registro-explicacion': 'El SKU identifica una referencia.',
        }
        self.assertEqual(self.client.post(pregunta_url, datos, HTTP_X_REQUESTED_WITH='fetch').json(), {'ok': True})
        self.assertEqual(self.examen.preguntas.count(), 2)
        datos['registro-opciones'] = '*SKU\n*Pasillo'
        respuesta = self.client.post(pregunta_url, datos)
        self.comprobar_rechazo_sin_guardar(respuesta)
        self.assertEqual(self.examen.preguntas.count(), 2)
        respuesta = self.client.post(self.registro_url('leccion_curso', 'nuevo'), {
            'padre': self.modulo_ajeno.pk, **self.datos_leccion(self.lectura),
        })
        self.assertEqual(respuesta.status_code, 404)

    def test_editar_leccion_conserva_fuente_wiki_y_configura_examen_sobre_diez(self):
        contenido = '[AULA_WIKI]\n## Inventario\n| SKU | Unidades |\n| --- | --- |\n| A01 | 5 |'
        datos = self.datos_leccion(self.examen, **{
            'registro-contenido': contenido, 'registro-nota_minima': '7.5', 'registro-intentos': '3',
        })
        respuesta = self.client.post(self.registro_url('leccion_curso', self.examen.pk), datos,
                                     HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True})
        self.examen.refresh_from_db()
        self.assertEqual(self.examen.nota_minima, 75)
        self.assertEqual(self.examen.intentos, 3)
        self.assertEqual(self.examen.contenido, contenido)
        self.assertEqual(self.examen.preguntas.count(), 1)
        formulario = self.client.get(self.registro_url('leccion_curso', self.examen.pk)).context['formulario']
        self.assertEqual(formulario.initial['nota_minima'], Decimal('7.5'))
        for nombre in ('contenido', 'archivo', 'video_url', 'enlace', 'fecha_hora', 'nota_minima',
                       'intentos', 'fecha_limite', 'obligatoria', 'publicada'):
            self.assertIn(nombre, formulario.fields)

    def test_material_sin_archivo_o_enlace_no_se_guarda(self):
        respuesta = self.client.post(self.registro_url('leccion_curso', self.lectura.pk),
            self.datos_leccion(self.lectura, **{'registro-tipo': 'material'}))
        self.comprobar_rechazo_sin_guardar(respuesta)
        self.lectura.refresh_from_db()
        self.assertEqual(self.lectura.tipo, 'texto')

    def test_no_elimina_leccion_con_progreso_ni_modulo_con_historial(self):
        progreso = ProgresoLeccion.objects.create(inscripcion=self.inscripcion, leccion=self.lectura)
        respuesta = self.client.post(self.registro_url('leccion_curso', self.lectura.pk),
            self.datos_leccion(self.lectura, **{'registro-eliminar': 'on'}))
        self.comprobar_rechazo_sin_guardar(respuesta)
        respuesta = self.client.post(self.registro_url('modulo_curso', self.modulo.pk), {
            'registro-orden': '1', 'registro-titulo': self.modulo.titulo, 'registro-eliminar': 'on',
        })
        self.comprobar_rechazo_sin_guardar(respuesta)
        self.assertTrue(ProgresoLeccion.objects.filter(pk=progreso.pk).exists())
        self.assertTrue(ModuloCurso.objects.filter(pk=self.modulo.pk).exists())
        self.assertTrue(LeccionCurso.objects.filter(pk=self.lectura.pk).exists())

    def test_no_cambia_tipo_ni_elimina_evaluacion_que_ya_se_rindio(self):
        intento = IntentoEvaluacion.objects.create(
            inscripcion=self.inscripcion, leccion=self.examen, nota=Decimal('60.00'), aprobado=False,
        )
        url = self.registro_url('leccion_curso', self.examen.pk)
        for cambios in ({'registro-tipo': 'texto'}, {'registro-eliminar': 'on'}):
            with self.subTest(cambios=cambios):
                respuesta = self.client.post(url, self.datos_leccion(self.examen, **cambios))
                self.comprobar_rechazo_sin_guardar(respuesta)
        self.examen.refresh_from_db()
        self.assertEqual(self.examen.tipo, 'evaluacion')
        self.assertTrue(IntentoEvaluacion.objects.filter(pk=intento.pk).exists())

    def test_no_elimina_deber_con_entrega_ni_pregunta_de_examen_rendido(self):
        entrega = EntregaDeber.objects.create(inscripcion=self.inscripcion, leccion=self.deber, comentario='Mi proyecto')
        respuesta = self.client.post(self.registro_url('leccion_curso', self.deber.pk),
            self.datos_leccion(self.deber, **{'registro-eliminar': 'on'}))
        self.comprobar_rechazo_sin_guardar(respuesta)
        IntentoEvaluacion.objects.create(
            inscripcion=self.inscripcion, leccion=self.examen, nota=Decimal('60.00'), aprobado=False,
        )
        respuesta = self.client.post(self.registro_url('pregunta_curso', self.pregunta.pk), {
            'registro-orden': '1', 'registro-enunciado': self.pregunta.enunciado,
            'registro-tipo': 'unica', 'registro-opciones': self.pregunta.opciones,
            'registro-puntos': '1', 'registro-eliminar': 'on',
        })
        self.comprobar_rechazo_sin_guardar(respuesta)
        self.assertTrue(EntregaDeber.objects.filter(pk=entrega.pk).exists())
        self.assertTrue(PreguntaEvaluacion.objects.filter(pk=self.pregunta.pk).exists())

    def test_no_agrega_preguntas_a_una_evaluacion_con_intentos_existentes(self):
        IntentoEvaluacion.objects.create(
            inscripcion=self.inscripcion, leccion=self.examen, nota=Decimal('60.00'), aprobado=False,
        )
        respuesta = self.client.post(self.registro_url('pregunta_curso', 'nuevo'), {
            'padre': self.examen.pk, 'registro-orden': '2',
            'registro-enunciado': 'Pregunta que alteraría el resultado histórico',
            'registro-tipo': 'unica', 'registro-opciones': '*Correcta\nIncorrecta', 'registro-puntos': '1',
        })
        self.comprobar_rechazo_sin_guardar(respuesta)
        self.assertEqual(self.examen.preguntas.count(), 1)

    def test_eliminar_curso_solo_se_ofrece_en_presentacion_o_formulario_completo(self):
        url = self.registro_url('curso', self.curso.pk)
        for grupo in ('', 'presentacion'):
            with self.subTest(grupo=grupo):
                formulario = self.client.get(url, {'grupo': grupo}).context['formulario']
                self.assertIn('eliminar', formulario.fields)
        for grupo in ('contenido', 'datos', 'instructores', 'pagos'):
            with self.subTest(grupo=grupo):
                formulario = self.client.get(url, {'grupo': grupo}).context['formulario']
                self.assertNotIn('eliminar', formulario.fields)

    def test_borrar_curso_sin_matriculas_regresa_a_gestion_en_vez_de_recargar_editor_inexistente(self):
        curso = Curso.objects.create(unidad=self.unidad, codigo='EDITOR-CUR-ELIM', nombre='Curso sin matrículas')
        gestion = reverse('gestion_unidad', args=[self.unidad.slug]) + '?view=cursos'
        respuesta = self.client.post(self.registro_url('curso', curso.pk), {
            'grupo': 'presentacion', 'volver': reverse('editor_curso', args=[self.unidad.slug, curso.codigo]),
            'registro-nombre': curso.nombre, 'registro-clasificacion': 'corto',
            'registro-modalidad': 'autoguiado', 'registro-eliminar': 'on',
        }, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(respuesta.json(), {'ok': True, 'redirigir': gestion})
        self.assertFalse(Curso.objects.filter(pk=curso.pk).exists())

    def test_borrar_modulo_vacio_conserva_el_regreso_al_editor_del_curso(self):
        volver = self.url + '#programa'
        respuesta = self.client.post(self.registro_url('modulo_curso', self.vacio.pk), {
            'volver': volver, 'registro-orden': str(self.vacio.orden),
            'registro-titulo': self.vacio.titulo, 'registro-eliminar': 'on',
        })
        self.assertRedirects(respuesta, volver, fetch_redirect_response=False)
        self.assertFalse(ModuloCurso.objects.filter(pk=self.vacio.pk).exists())
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())
