class ModuloTabs {
    constructor() {
        this.activeTab = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.showInitialModule();
        // detalle_unidad.js restaura el enlace al terminar de registrar todos los manejadores.
    }

    abrirEnlaceDirecto() {
        let modulo = '';
        try { modulo = decodeURIComponent(window.location.hash.slice(1)).trim(); } catch (_error) { /* ancla inválida */ }
        const tab = [...document.querySelectorAll('#modulo-tabs .nav-link[data-modulo]')]
            .find(item => item.dataset.modulo === modulo);
        if (tab) this.handleTabClick(tab);
        const parametros = new URLSearchParams(window.location.search);
        const recurso = parametros.get('recurso');
        const guia = parametros.get('guia');
        const id = recurso && /^[\w-]+$/.test(recurso) ? recurso : (guia && /^\d+$/.test(guia) ? 'guia-actividad-' + guia : '');
        const botones = [...document.querySelectorAll('.recurso-btn[data-id]')];
        const candidatos = tab ? botones.filter(b => b.closest('.modulo-carpeta-list[data-modulo]')?.dataset.modulo === modulo) : botones;
        const boton = candidatos.find(item => item.dataset.id === id)
            || (!recurso && botones.find(item => item.dataset.id === id));
        if (boton) {
            const lista = boton.closest('.modulo-carpeta-list[data-modulo]');
            if (lista) this.setActiveTab(lista.dataset.modulo, { reiniciarVisor: false });
            boton.click();
            return true;
        }
        return Boolean(tab);
    }

    setupEventListeners() {
        const tabList = document.getElementById('modulo-tabs');
        tabList?.addEventListener('click', event => {
            const tab = event.target.closest('.nav-link[data-modulo]');
            if (!tab) return;
            event.preventDefault();
            this.handleTabClick(tab);
        });
    }

    handleTabClick(tab, { reiniciarVisor = true } = {}) {
        // Remover active de todos los tabs
        document.querySelectorAll('#modulo-tabs .nav-link').forEach(t => {
            t.classList.remove('active');
            t.setAttribute('aria-selected', 'false');
            t.removeAttribute('aria-current');
        });
        
        // Agregar active al tab seleccionado
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');
        tab.setAttribute('aria-current', 'page');
        
        // Obtener el módulo del tab
        const modulo = tab.getAttribute('data-modulo');
        this.activeTab = modulo;
        
        // Mostrar carpetas del módulo
        this.showModuleCarpetas(modulo);
        
        // El visor no se queda con el documento de la pestaña anterior: vuelve
        // a la portada de esta, que explica qué es y qué contiene.
        if (reiniciarVisor) {
            window.mostrarPortadaModulo?.(modulo);
        }
    }

    showModuleCarpetas(modulo) {
        const carpetaLists = document.querySelectorAll('.modulo-carpeta-list');
        carpetaLists.forEach(list => {
            const isActive = list.getAttribute('data-modulo') === modulo;
            list.classList.toggle('hublab-module-hidden', !isActive);
            list.classList.toggle('hublab-module-visible', isActive);
        });
    }

    showInitialModule() {
        const firstTab = document.querySelector('#modulo-tabs .nav-link.active');
        if (firstTab) {
            const modulo = firstTab.getAttribute('data-modulo');
            this.activeTab = modulo;
            this.showModuleCarpetas(modulo);
        }
    }

    setActiveTab(modulo, opciones) {
        const tab = document.querySelector(`#modulo-tabs .nav-link[data-modulo="${modulo}"]`);
        if (tab) {
            this.handleTabClick(tab, opciones);
        }
    }

    getActiveTab() {
        return this.activeTab;
    }
}

// Crear instancia global
window.moduloTabs = new ModuloTabs();
