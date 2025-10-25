document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("iaForm");
  const mensaje = document.getElementById("mensaje");

  // Mostrar/ocultar campos "Otro" en checkboxes (solo si existen)
  const camposOtro = [
    { checkboxId: "otraHerramienta", inputId: "herramientas_otra_texto" },
    { checkboxId: "otroUso", inputId: "usos_otra_texto" },
    { checkboxId: "otroSector", inputId: "sectores_otro_texto" },
  ];
  camposOtro.forEach(({ checkboxId, inputId }) => {
    const checkbox = document.getElementById(checkboxId);
    const input = document.getElementById(inputId);
    if (checkbox && input) {
      input.classList.toggle("oculto", !checkbox.checked);
      checkbox.addEventListener("change", () => {
        input.classList.toggle("oculto", !checkbox.checked);
      });
    }
  });

  // Select con opción "Otro" (definición) – sólo si existen
  const definicionSelect = document.getElementById("definicion");
  const definicionOtro = document.getElementById("definicion_otro_texto");
  if (definicionSelect && definicionOtro) {
    definicionOtro.classList.toggle("oculto", definicionSelect.value !== "otro");
    definicionSelect.addEventListener("change", () => {
      definicionOtro.classList.toggle("oculto", definicionSelect.value !== "otro");
    });
  }

  // Select carrera con opción "Otra" – sólo si existen
  const carreraSelect = document.getElementById("carrera");
  const carreraOtro = document.getElementById("carrera_otro_texto");
  if (carreraSelect && carreraOtro) {
    carreraOtro.classList.toggle("oculto", carreraSelect.value !== "otra");
    carreraSelect.addEventListener("change", () => {
      carreraOtro.classList.toggle("oculto", carreraSelect.value !== "otra");
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    mensaje.textContent = "Enviando...";
    const data = {};

    // --- Datos del estudiante (solo si existen esos campos) ---
    const elNombre = form.elements["nombre_completo"];
    const elEdad = form.elements["edad"];
    const elFac = form.elements["facultad"];
    const elCarr = form.elements["carrera"];

    if (elNombre) data.nombre_completo = elNombre.value.trim();
    if (elEdad)   data.edad = Number(elEdad.value);
    if (elFac)    data.facultad = elFac.value;
    if (elCarr)   data.carrera = elCarr.value;

    // Validaciones básicas (solo si existen)
    if (elNombre && (!data.nombre_completo || data.nombre_completo.length > 120)) {
      mensaje.textContent = "⚠️ Ingresa un nombre válido (1–120 caracteres).";
      return;
    }
    if (elEdad && (!Number.isInteger(data.edad) || data.edad < 15 || data.edad > 99)) {
      mensaje.textContent = "⚠️ La edad debe ser un entero entre 15 y 99.";
      return;
    }
    if (elCarr && data.carrera === "otra") {
      const txt = (carreraOtro?.value || "").trim();
      if (!txt) {
        mensaje.textContent = "⚠️ Indica cuál es tu carrera (campo 'Otra').";
        carreraOtro?.focus();
        return;
      }
      data.carrera_otro_texto = txt;
    }

    // --- Selects simples (encuesta) – agregar solo si existen ---
    ["familiaridad","definicion","frecuencia","confianza","percepcion_social","regulacion","emocion"]
      .forEach((field) => {
        const el = form.elements[field];
        if (el) data[field] = el.value || "";
      });

    // Si definicion = "otro", exigir texto (si existen ambos)
    if (definicionSelect && definicionOtro && data.definicion === "otro") {
      const txt = definicionOtro.value.trim();
      if (!txt) {
        mensaje.textContent = "⚠️ Indica cuál es tu definición (campo 'Otro').";
        definicionOtro.focus();
        return;
      }
      data.definicion_otro_texto = txt;
    }

    // --- Checkboxes múltiples (si existe el grupo) ---
    ["herramientas","usos","sectores"].forEach((groupId) => {
      const group = document.getElementById(groupId);
      const selected = group
        ? Array.from(group.querySelectorAll('input[type="checkbox"]:checked')).map(el => el.value)
        : [];
      data[groupId] = selected;

      const inputOtro = document.getElementById(`${groupId}_otra_texto`);
      const eligioOtro = selected.includes("otra") || selected.includes("otro");
      if (eligioOtro && inputOtro) {
        const txt = (inputOtro.value || "").trim();
        if (!txt) {
          mensaje.textContent = "⚠️ Indica cuál en el campo 'Otro'.";
          inputOtro.focus();
          return;
        }
        data[`${groupId}_otra_texto`] = txt;
      }
    });

    // --- Envío robusto: si el backend devuelve HTML por 500, lo mostramos ---
    try {
      const res = await fetch("/api/response", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const ct = res.headers.get("content-type") || "";
      if (!ct.includes("application/json")) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status} ${res.statusText}: ${text.slice(0,200)}`);
      }

      const result = await res.json();
      if (result.ok) {
        mensaje.textContent = "✅ ¡Gracias! Tu respuesta ha sido registrada.";
        form.reset();

        // Re-ocultar posibles "otro"
        definicionOtro?.classList.add("oculto");
        carreraOtro?.classList.add("oculto");
        ["herramientas_otra_texto","usos_otra_texto","sectores_otra_texto"]
          .forEach(id => document.getElementById(id)?.classList.add("oculto"));
      } else {
        mensaje.textContent = "⚠️ Error al enviar: " + JSON.stringify(result.errors || result.error);
      }
    } catch (err) {
      console.error(err);
      mensaje.textContent = "❌ Error de red/servidor: " + String(err).slice(0,200);
    }
  });
});
