// Las fechas civiles del calendario se conservan; "hoy" usa la zona institucional.
(() => {
  const element = document.getElementById('configuracion-regional-institucion');
  if (!element) return;
  const regional = JSON.parse(element.textContent);
  const formatter = new Intl.DateTimeFormat('en', {
    timeZone: regional.zona_horaria, year: 'numeric', month: '2-digit', day: '2-digit'
  });
  window.regionalInstitucion = Object.freeze({
    idioma: regional.idioma,
    zonaHoraria: regional.zona_horaria,
    hoy(ahora = new Date()) {
      const parts = Object.fromEntries(formatter.formatToParts(ahora).map(part => [part.type, part.value]));
      return new Date(Number(parts.year), Number(parts.month) - 1, Number(parts.day));
    }
  });
})();
