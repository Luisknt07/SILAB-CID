const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../../../apps/gestion_unidades/static/portal/js/pages/unidades/responsables_busqueda.js"), "utf8");

class Element {
  constructor() { this.value = ""; this.textContent = ""; this.children = []; this.events = {}; this.dataset = {}; }
  set innerHTML(_) { throw new Error("HTML injection is forbidden"); }
  addEventListener(type, handler) { (this.events[type] ||= []).push(handler); }
  dispatchEvent(event) { for (const handler of this.events[event.type] || []) handler(event); }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; }
  get options() { return this.children; }
}
function fixture() {
  const input = new Element(), results = new Element(), status = new Element(), select = new Element(), name = new Element(), email = new Element();
  const form = new Element();
  form.querySelector = (selector) => ({ '[name="usuario_id"]': select, '[name="nombre"]': name, '[name="email"]': email })[selector];
  const box = new Element();
  box.dataset = { searchUrl: "/reservas/usuarios/buscar/", unidad: "laboratorio-propio" };
  box.closest = () => form;
  box.querySelector = (selector) => ({ "[data-responsible-query]": input, "[data-responsible-results]": results, "[data-responsible-status]": status })[selector];
  const scope = { querySelectorAll: () => [box] };
  const document = { createElement: () => new Element(), ...scope };
  const timers = new Map(), requests = [];
  let timerId = 0;
  const window = {
    location: { href: "https://example.test/unidades/propia/gestion/" },
    setTimeout(fn) { timers.set(++timerId, fn); return timerId; },
    clearTimeout(id) { timers.delete(id); },
    fetch(url, options) { return new Promise((resolve, reject) => requests.push({ url, options, resolve, reject })); },
  };
  vm.runInNewContext(source, { window, document, URL, AbortController, Event });
  window.inicializarBusquedaResponsables(scope);
  const type = (value) => { input.value = value; input.dispatchEvent(new Event("input")); };
  const flushTimers = () => { const fns = Array.from(timers.values()); timers.clear(); for (const fn of fns) fn(); };
  const respond = async (index, users, ok = true) => {
    requests[index].resolve({ ok, json: async () => ({ success: true, usuarios: users }) });
    await new Promise(setImmediate);
  };
  return { window, scope, input, results, status, select, name, email, form, timers, requests, type, flushTimers, respond };
}

test("mínimo dos caracteres, debounce y arranque idempotente", () => {
  const f = fixture();
  f.window.inicializarBusquedaResponsables(f.scope);
  assert.equal(f.input.events.input.length, 1);
  f.type("a");
  assert.equal(f.timers.size, 0);
  f.type("Ana"); f.type("Andrea");
  assert.equal(f.timers.size, 1);
  f.flushTimers();
  assert.equal(f.requests.length, 1);
  assert.equal(f.requests[0].url.searchParams.get("q"), "Andrea");
  assert.equal(f.requests[0].url.searchParams.get("contexto"), "responsables");
  assert.equal(f.requests[0].url.searchParams.get("unidad"), "laboratorio-propio");
  assert.equal(f.requests[0].options.credentials, "same-origin");
});

test("selección crea opción y usa texto seguro sin sobrescribir datos editados", async () => {
  const f = fixture();
  f.type("Ana"); f.flushTimers();
  const malicious = '<img src=x onerror="alert(1)">';
  await f.respond(0, [{ id: 91, nombre: malicious, usuario: "ana", correo: "ana@example.test" }]);
  assert.equal(f.results.children.length, 1);
  const button = f.results.children[0];
  assert.equal(button.type, "button");
  assert.equal(button.textContent, malicious + " · ana@example.test");
  f.name.value = "Nombre editado";
  button.dispatchEvent(new Event("click"));
  assert.equal(f.select.value, "91");
  assert.equal(f.select.options.length, 1);
  assert.equal(f.select.options[0].textContent, button.textContent);
  assert.equal(f.name.value, "Nombre editado");
  assert.equal(f.email.value, "ana@example.test");
  assert.equal(f.results.children.length, 0);
});

test("respuesta tardía y petición abortada no reemplazan búsqueda actual", async () => {
  const f = fixture();
  f.type("Ana"); f.flushTimers();
  f.type("Beatriz"); f.flushTimers();
  assert.equal(f.requests[0].options.signal.aborted, true);
  await f.respond(1, [{ id: 2, nombre: "Beatriz", usuario: "bea" }]);
  await f.respond(0, [{ id: 1, nombre: "Ana", usuario: "ana" }]);
  assert.equal(f.results.children[0].textContent, "Beatriz · bea");
  f.type("a");
  assert.equal(f.results.children.length, 0);
  assert.equal(f.timers.size, 0);
});

test("error y reset limpian resultados y descartan respuestas pendientes", async () => {
  const f = fixture();
  f.type("Ana"); f.flushTimers();
  await f.respond(0, [], false);
  assert.match(f.status.textContent, /Vuelve a intentarlo/);
  f.type("Beatriz"); f.flushTimers();
  f.form.dispatchEvent(new Event("reset"));
  await f.respond(1, [{ id: 2, nombre: "Beatriz", usuario: "bea" }]);
  assert.equal(f.results.children.length, 0);
  assert.match(f.status.textContent, /dos caracteres/);
});

test("respuesta se limita a diez botones y no repite una opción existente", async () => {
  const f = fixture();
  const old = new Element(); old.value = "1"; f.select.appendChild(old);
  f.type("Persona"); f.flushTimers();
  await f.respond(0, Array.from({ length: 14 }, (_, i) => ({ id: i + 1, nombre: "Persona " + i, usuario: "persona" + i })));
  assert.equal(f.results.children.length, 10);
  f.results.children[0].dispatchEvent(new Event("click"));
  assert.equal(f.select.options.length, 1);
  assert.equal(f.name.value, "Persona 0");
  assert.equal(f.select.value, "1");
});

test("cambiar de cuenta actualiza valores sugeridos y conserva posteriores ediciones manuales", async () => {
  const f = fixture();
  f.type("Ana"); f.flushTimers();
  await f.respond(0, [{ id: 1, nombre: "Ana", usuario: "ana", correo: "ana@example.test" }]);
  f.results.children[0].dispatchEvent(new Event("click"));
  assert.equal(f.name.value, "Ana");
  assert.equal(f.email.value, "ana@example.test");
  f.type("Beatriz"); f.flushTimers();
  await f.respond(1, [{ id: 2, nombre: "Beatriz", usuario: "bea", correo: "bea@example.test" }]);
  f.results.children[0].dispatchEvent(new Event("click"));
  assert.equal(f.select.value, "2");
  assert.equal(f.name.value, "Beatriz");
  assert.equal(f.email.value, "bea@example.test");
  f.name.value = "Contacto público editado";
  f.email.value = "contacto@example.test";
  f.type("Carla"); f.flushTimers();
  await f.respond(2, [{ id: 3, nombre: "Carla", usuario: "carla", correo: "carla@example.test" }]);
  f.results.children[0].dispatchEvent(new Event("click"));
  assert.equal(f.select.value, "3");
  assert.equal(f.name.value, "Contacto público editado");
  assert.equal(f.email.value, "contacto@example.test");
});
