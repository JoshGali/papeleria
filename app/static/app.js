/* Interfaz del gestor de inventario.
 *
 * JavaScript sin dependencias ni compilacion: la pagina la sirve el propio
 * FastAPI, asi que las llamadas van al mismo origen y no hace falta CORS.
 */
"use strict";

// --------------------------------------------------------------- Utilidades
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

/** Cambia aqui la moneda si la papeleria no factura en pesos mexicanos. */
const dinero = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
const numero = new Intl.NumberFormat("es-MX");

const estado = {
  productos: [],
  movimientos: [],
  orden: { campo: "name", asc: true },
  umbral: 10,
};

/** Error de la API que conserva el mensaje del contrato de errores. */
class ApiError extends Error {
  constructor(mensaje, status, detalles) {
    super(mensaje);
    this.status = status;
    this.detalles = detalles || [];
  }
}

/** Llama a la API y traduce cualquier fallo a un ApiError con mensaje util. */
async function api(ruta, opciones = {}) {
  let respuesta;
  try {
    respuesta = await fetch(ruta, {
      headers: opciones.body ? { "content-type": "application/json" } : undefined,
      ...opciones,
    });
  } catch (fallo) {
    throw new ApiError("No se pudo contactar al servidor. Verifica que siga en ejecucion.", 0);
  }

  if (respuesta.status === 204) return null;

  const cuerpo = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    const mensaje = (cuerpo && cuerpo.message) || `Error ${respuesta.status}`;
    throw new ApiError(mensaje, respuesta.status, cuerpo && cuerpo.errors);
  }
  return cuerpo;
}

function avisar(mensaje, tipo = "ok", duracion = 4500) {
  const nodo = document.createElement("div");
  nodo.className = `aviso aviso--${tipo}`;
  nodo.textContent = mensaje;
  $("#avisos").append(nodo);
  setTimeout(() => nodo.remove(), duracion);
}

function fecha(iso) {
  const d = new Date(iso);
  const hoy = new Date();
  const mismoDia = d.toDateString() === hoy.toDateString();
  return mismoDia
    ? `Hoy ${d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })}`
    : d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
}

function fechaHora(iso) {
  return new Date(iso).toLocaleString("es-MX", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

// ------------------------------------------------------------ Carga de datos
async function cargarProductos() {
  // include_unavailable: la vista de administracion necesita ver tambien los
  // agotados y los que aun no tienen precio, que el listado publico oculta.
  estado.productos = await api("/products?include_unavailable=true");
  pintarInventario();
}

async function cargarMovimientos() {
  estado.movimientos = await api("/stock/movements?limit=500");
  pintarMovimientos();
}

async function comprobarConexion() {
  const pill = $("#estado-conexion");
  try {
    const salud = await api("/health");
    pill.textContent = `En linea - ${numero.format(salud.products)} productos`;
    pill.className = "pill pill--ok";
  } catch (error) {
    pill.textContent = "Sin conexion";
    pill.className = "pill pill--error";
    throw error;
  }
}

// ------------------------------------------------------- Filtrado y ordenado
/** Filtro en el navegador: evita una peticion por cada tecla escrita. */
function productosFiltrados() {
  const texto = $("#buscador").value.trim().toLowerCase();
  const filtro = $("#filtro-estado").value;

  let lista = estado.productos.filter((p) => {
    if (texto) {
      const heno = `${p.name} ${p.description} ${p.product_id}`.toLowerCase();
      if (!heno.includes(texto)) return false;
    }
    if (filtro === "disponibles") return p.stock > 0;
    if (filtro === "agotados") return p.stock === 0;
    // "Stock bajo" son los que conviene resurtir, no los ya agotados: usa la
    // misma definicion que el indicador de la cabecera.
    if (filtro === "bajos") return p.stock > 0 && p.stock <= estado.umbral;
    if (filtro === "sin-precio") return p.price === 0;
    return true;
  });

  const { campo, asc } = estado.orden;
  lista.sort((a, b) => {
    const x = a[campo], y = b[campo];
    const cmp = typeof x === "string" ? x.localeCompare(y, "es") : x - y;
    return asc ? cmp : -cmp;
  });
  return lista;
}

function claseStock(producto) {
  if (producto.stock === 0) return "badge badge--cero";
  if (producto.stock <= estado.umbral) return "badge badge--bajo";
  return "badge badge--ok";
}

// ------------------------------------------------------------- Pintar tablas
function pintarInventario() {
  const productos = estado.productos;
  const bajos = productos.filter((p) => p.stock > 0 && p.stock <= estado.umbral);
  const valor = productos.reduce((suma, p) => suma + p.price * p.stock, 0);

  $("#kpi-total").textContent = numero.format(productos.length);
  $("#kpi-disponibles").textContent = numero.format(productos.filter((p) => p.stock > 0).length);
  $("#kpi-bajos").textContent = numero.format(bajos.length);
  $("#kpi-agotados").textContent = numero.format(productos.filter((p) => p.stock === 0).length);
  $("#kpi-valor").textContent = dinero.format(valor);

  const visibles = productosFiltrados();
  const cuerpo = $("#tabla-productos");
  cuerpo.replaceChildren();

  for (const p of visibles) {
    const fila = document.createElement("tr");

    const celdaNombre = document.createElement("td");
    const nombre = document.createElement("div");
    nombre.className = "producto__nombre";
    nombre.textContent = p.name;
    const desc = document.createElement("div");
    desc.className = "producto__desc";
    desc.textContent = p.description;
    celdaNombre.append(nombre, desc);

    const celdaPrecio = document.createElement("td");
    celdaPrecio.className = "num";
    celdaPrecio.textContent = dinero.format(p.price);
    if (p.price === 0) celdaPrecio.title = "Sin precio: no aparece en el listado publico";

    const celdaStock = document.createElement("td");
    celdaStock.className = "num";
    const badge = document.createElement("span");
    badge.className = claseStock(p);
    badge.textContent = numero.format(p.stock);
    celdaStock.append(badge);

    const celdaFecha = document.createElement("td");
    celdaFecha.className = "fecha";
    celdaFecha.textContent = fecha(p.updated_at);
    celdaFecha.title = `Alta: ${fechaHora(p.created_at)}\nUltima modificacion: ${fechaHora(p.updated_at)}`;

    const celdaAcciones = document.createElement("td");
    const acciones = document.createElement("div");
    acciones.className = "acciones";
    acciones.append(
      boton("Entrada", () => abrirStock(p, "entry")),
      boton("Salida", () => abrirStock(p, "exit"), p.stock === 0),
      boton("Editar", () => abrirProducto(p)),
      boton("Eliminar", () => eliminarProducto(p), false, "btn--peligro"),
    );
    celdaAcciones.append(acciones);

    fila.append(celdaNombre, celdaPrecio, celdaStock, celdaFecha, celdaAcciones);
    cuerpo.append(fila);
  }

  const vacio = $("#vacio-productos");
  vacio.hidden = visibles.length > 0;
  vacio.textContent = productos.length === 0
    ? "Aun no hay productos. Usa «Nuevo producto» para dar de alta el primero."
    : "Ningun producto coincide con el filtro.";

  $("#resumen-filtro").textContent = productos.length
    ? `Mostrando ${visibles.length} de ${productos.length} productos.`
    : "";

  $$(".sortable").forEach((th) => {
    th.classList.toggle("is-sorted", th.dataset.sort === estado.orden.campo);
    th.classList.toggle("desc", th.dataset.sort === estado.orden.campo && !estado.orden.asc);
  });
}

function boton(texto, alPulsar, desactivado = false, clase = "") {
  const b = document.createElement("button");
  b.className = `btn btn--mini ${clase}`.trim();
  b.textContent = texto;
  b.disabled = desactivado;
  b.addEventListener("click", alPulsar);
  return b;
}

function pintarMovimientos() {
  const texto = $("#buscador-mov").value.trim().toLowerCase();
  const tipo = $("#filtro-tipo").value;

  const visibles = estado.movimientos.filter((m) => {
    if (tipo !== "todos" && m.type !== tipo) return false;
    return !texto || m.product_name.toLowerCase().includes(texto);
  });

  const cuerpo = $("#tabla-movimientos");
  cuerpo.replaceChildren();

  for (const m of visibles) {
    const fila = document.createElement("tr");
    const esEntrada = m.type === "entry";

    const celdaFecha = document.createElement("td");
    celdaFecha.className = "fecha";
    celdaFecha.textContent = fechaHora(m.created_at);

    const celdaProducto = document.createElement("td");
    celdaProducto.textContent = m.product_name;

    const celdaTipo = document.createElement("td");
    celdaTipo.className = esEntrada ? "mov--entry" : "mov--exit";
    celdaTipo.textContent = esEntrada ? "Entrada" : "Salida";

    const celdaCantidad = document.createElement("td");
    celdaCantidad.className = `num ${esEntrada ? "mov--entry" : "mov--exit"}`;
    celdaCantidad.textContent = `${esEntrada ? "+" : "-"}${numero.format(m.quantity)}`;

    const celdaResultado = document.createElement("td");
    celdaResultado.className = "num";
    celdaResultado.textContent = `${numero.format(m.stock_before)} → ${numero.format(m.stock_after)}`;

    fila.append(celdaFecha, celdaProducto, celdaTipo, celdaCantidad, celdaResultado);
    cuerpo.append(fila);
  }

  const vacio = $("#vacio-movimientos");
  vacio.hidden = visibles.length > 0;
  vacio.textContent = estado.movimientos.length === 0
    ? "Todavia no se ha registrado ningun movimiento de stock."
    : "Ningun movimiento coincide con el filtro.";

  $("#resumen-mov").textContent = estado.movimientos.length
    ? `Mostrando ${visibles.length} de ${estado.movimientos.length} movimientos.`
    : "";
}

// ------------------------------------------------------- Alta y edicion
let productoEnEdicion = null;

function abrirProducto(producto = null) {
  productoEnEdicion = producto;
  const editando = producto !== null;

  $("#titulo-producto").textContent = editando ? "Editar producto" : "Nuevo producto";
  $("#p-nombre").value = editando ? producto.name : "";
  $("#p-descripcion").value = editando ? producto.description : "";
  $("#p-precio").value = editando ? producto.price : "";
  $("#p-stock").value = 0;

  // El stock no es editable desde el alta: se mueve con entradas y salidas.
  $("#campo-stock-inicial").hidden = editando;
  $("#nota-stock").hidden = editando;
  $("#error-producto").hidden = true;

  $("#modal-producto").showModal();
  $("#p-nombre").focus();
}

async function guardarProducto(evento) {
  evento.preventDefault();
  const error = $("#error-producto");
  error.hidden = true;

  const datos = {
    name: $("#p-nombre").value.trim(),
    description: $("#p-descripcion").value.trim(),
    price: Number($("#p-precio").value),
  };

  const boton = $("#btn-guardar");
  boton.disabled = true;
  try {
    if (productoEnEdicion) {
      await editarProducto(datos);
    } else {
      await crearProducto(datos, Number($("#p-stock").value) || 0);
    }
    $("#modal-producto").close();
    await Promise.all([cargarProductos(), cargarMovimientos(), comprobarConexion()]);
  } catch (fallo) {
    error.textContent = fallo.message;
    error.hidden = false;
  } finally {
    boton.disabled = false;
  }
}

/** Req 3.7: enviar los mismos valores devuelve 400, asi que no se envian. */
async function editarProducto(datos) {
  const cambios = {};
  for (const campo of ["name", "description", "price"]) {
    if (datos[campo] !== productoEnEdicion[campo]) cambios[campo] = datos[campo];
  }
  if (Object.keys(cambios).length === 0) {
    throw new ApiError("No hay cambios que guardar en este producto.", 400);
  }
  await api(`/products/${productoEnEdicion.product_id}`, {
    method: "PATCH",
    body: JSON.stringify(cambios),
  });
  avisar("Producto actualizado.");
}

/**
 * El alta son dos operaciones: crear el producto y registrar su primera
 * entrada. Si la segunda falla, el producto ya existe, asi que se avisa de
 * forma explicita en lugar de dejar la pantalla en un estado ambiguo.
 */
async function crearProducto(datos, stockInicial) {
  const creado = await api("/products", { method: "POST", body: JSON.stringify(datos) });

  if (stockInicial <= 0) {
    avisar(`"${creado.name}" se dio de alta sin existencias.`);
    return;
  }

  try {
    await api("/stock/entries", {
      method: "POST",
      body: JSON.stringify({ product_id: creado.product_id, quantity: stockInicial }),
    });
    avisar(`"${creado.name}" se dio de alta con ${numero.format(stockInicial)} unidades.`);
  } catch (fallo) {
    avisar(
      `El producto "${creado.name}" SI se creo, pero no se pudo registrar su stock ` +
      `inicial (${fallo.message}). Registralo con el boton "Entrada".`,
      "aviso",
      12000,
    );
  }
}

async function eliminarProducto(producto) {
  const confirmado = confirm(
    `Se eliminara "${producto.name}" del inventario.\n\n` +
    "Su historial de movimientos se conserva. Esta accion no se puede deshacer.",
  );
  if (!confirmado) return;

  try {
    await api(`/products/${producto.product_id}`, { method: "DELETE" });
    avisar(`"${producto.name}" se elimino del inventario.`);
    await Promise.all([cargarProductos(), comprobarConexion()]);
  } catch (fallo) {
    avisar(fallo.message, "error");
  }
}

// ------------------------------------------------------ Movimientos de stock
let movimientoActual = null;

function abrirStock(producto, tipo) {
  movimientoActual = { producto, tipo };
  const esEntrada = tipo === "entry";

  $("#titulo-stock").textContent = esEntrada ? "Registrar entrada" : "Registrar salida";
  $("#stock-producto").textContent = `${producto.name} - existencias actuales: ${numero.format(producto.stock)}`;
  $("#ayuda-stock").textContent = esEntrada
    ? "Unidades que ingresan al almacen (maximo 999999 por operacion)."
    : `Unidades que salen del almacen. No puede superar las ${numero.format(producto.stock)} disponibles.`;
  $("#s-cantidad").value = 1;
  $("#s-cantidad").max = esEntrada ? 999999 : producto.stock;
  $("#btn-confirmar-stock").textContent = esEntrada ? "Registrar entrada" : "Registrar salida";
  $("#error-stock").hidden = true;

  $("#modal-stock").showModal();
  $("#s-cantidad").focus();
  $("#s-cantidad").select();
}

async function registrarMovimiento(evento) {
  evento.preventDefault();
  const error = $("#error-stock");
  error.hidden = true;

  const { producto, tipo } = movimientoActual;
  const cantidad = Number($("#s-cantidad").value);
  const ruta = tipo === "entry" ? "/stock/entries" : "/stock/exits";

  const boton = $("#btn-confirmar-stock");
  boton.disabled = true;
  try {
    const actualizado = await api(ruta, {
      method: "POST",
      body: JSON.stringify({ product_id: producto.product_id, quantity: cantidad }),
    });
    avisar(
      `${tipo === "entry" ? "Entrada" : "Salida"} de ${numero.format(cantidad)} unidades. ` +
      `"${actualizado.name}" queda en ${numero.format(actualizado.stock)}.`,
    );
    $("#modal-stock").close();
    await Promise.all([cargarProductos(), cargarMovimientos(), comprobarConexion()]);
  } catch (fallo) {
    error.textContent = fallo.message;
    error.hidden = false;
  } finally {
    boton.disabled = false;
  }
}

// -------------------------------------------------------------- Arranque
function conectarEventos() {
  $("#buscador").addEventListener("input", pintarInventario);
  $("#filtro-estado").addEventListener("change", pintarInventario);
  $("#umbral").addEventListener("input", (e) => {
    estado.umbral = Math.max(1, Number(e.target.value) || 1);
    pintarInventario();
  });

  $("#buscador-mov").addEventListener("input", pintarMovimientos);
  $("#filtro-tipo").addEventListener("change", pintarMovimientos);
  $("#btn-refrescar-mov").addEventListener("click", () => refrescar());

  $("#btn-nuevo").addEventListener("click", () => abrirProducto());
  $("#form-producto").addEventListener("submit", guardarProducto);
  $("#form-stock").addEventListener("submit", registrarMovimiento);
  $$("[data-cerrar]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));

  $$(".sortable").forEach((th) => {
    th.addEventListener("click", () => {
      const campo = th.dataset.sort;
      estado.orden = campo === estado.orden.campo
        ? { campo, asc: !estado.orden.asc }
        : { campo, asc: true };
      pintarInventario();
    });
  });

  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".tab").forEach((t) => {
        const activa = t === tab;
        t.classList.toggle("is-active", activa);
        t.setAttribute("aria-selected", String(activa));
      });
      $("#panel-inventario").hidden = tab.dataset.tab !== "inventario";
      $("#panel-movimientos").hidden = tab.dataset.tab !== "movimientos";
    });
  });
}

async function refrescar() {
  try {
    await comprobarConexion();
    await Promise.all([cargarProductos(), cargarMovimientos()]);
  } catch (fallo) {
    avisar(fallo.message, "error", 8000);
  }
}

conectarEventos();
refrescar();
