(function(){
  // ⚠️ Clave simple (solo UI). Si quieres, cámbiala por una de tu .env y pásala como variable inline.
  const ACCESS_CODE = "itm2025"; 
  const gate = document.getElementById("gate");
  const btnAcceder = document.getElementById("btnAcceder");
  const clave = document.getElementById("clave");
  const msg = document.getElementById("msg");

  // Guardar la clave en sessionStorage para no pedirla de nuevo
  const ok = sessionStorage.getItem("csv_access_ok") === "1";
  if(ok){ gate.style.display = "none"; }

  btnAcceder.addEventListener("click", ()=>{
    if(clave.value.trim() === ACCESS_CODE){
      sessionStorage.setItem("csv_access_ok", "1");
      gate.style.display = "none";
      init();
    }else{
      msg.textContent = "Clave incorrecta.";
    }
  });

  // Si ya tiene acceso, cargar
  if(ok){ init(); }

  // -------------- LÓGICA CSV --------------
  async function init(){
    setStatus("cargando...");
    try{
      // Cargar EDA consolidado; si no existe, mostrar el raw
      const eda = await fetchCsv("/csv-data/eda_ia_consolidado.csv");
      if(eda && eda.length){
        setStatus("EDA consolidado");
        renderEda(eda);
      }else{
        const raw = await fetchCsv("/csv-data/respuestas_ia.csv");
        if(raw && raw.length){
          setStatus("respuestas (raw)");
          renderRaw(raw);
        }else{
          setStatus("sin datos");
          document.getElementById("csvInfo").innerHTML = "<p>No hay datos aún. Usa el botón Recalcular o envía respuestas.</p>";
        }
      }
    }catch(e){
      setStatus("error");
      document.getElementById("csvInfo").innerHTML = `<p class="warn">Error cargando CSV: ${e}</p>`;
    }

    // Recalcular (llama al backend para regenerar CSVs)
    document.getElementById("btnRecompute").addEventListener("click", async ()=>{
      setStatus("recalculando…");
      const res = await fetch("/api/recompute", {method: "POST"});
      const json = await res.json().catch(()=>({}));
      if(json.ok){
        setStatus("actualizado");
        // recargar vista
        location.reload();
      }else{
        setStatus("error");
        alert("Error al recalcular: " + (json.error || "desconocido"));
      }
    });
  }

  function setStatus(text){
    const s = document.getElementById("csvStatus");
    s.textContent = "estado: " + text;
  }

  async function fetchCsv(url){
    const res = await fetch(url, {cache: "no-store"});
    if(!res.ok) return [];
    const text = await res.text();
    // Parse muy simple (no hay comas internas porque usamos ; para arrays)
    const rows = text.trim().split(/\r?\n/).map(line => line.split(","));
    if(!rows.length) return [];
    const headers = rows[0];
    const data = rows.slice(1).map(r => {
      const o = {};
      headers.forEach((h,i)=> o[h] = (r[i] ?? "").trim());
      return o;
    });
    // guarda headers como propiedad
    data._headers = headers;
    return data;
  }

  function renderTable(title, headers, rows, small=false){
    const wrap = document.createElement("div");
    wrap.className = "section";
    const h = document.createElement("h2");
    h.textContent = title;
    wrap.appendChild(h);

    const tWrap = document.createElement("div");
    tWrap.className = "tbl-wrap";
    const table = document.createElement("table");
    table.className = small ? "tbl tbl--sm" : "tbl";
    // head
    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    headers.forEach(x=>{
      const th = document.createElement("th"); th.textContent = x; trh.appendChild(th);
    });
    thead.appendChild(trh);
    table.appendChild(thead);
    // body
    const tbody = document.createElement("tbody");
    rows.forEach(row=>{
      const tr = document.createElement("tr");
      headers.forEach(h=>{
        const td = document.createElement("td");
        td.textContent = (row[h] ?? "");
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    tWrap.appendChild(table);
    wrap.appendChild(tWrap);
    document.getElementById("tables").appendChild(wrap);
  }

  function renderEda(eda){
    const info = document.getElementById("csvInfo");
    info.innerHTML = `<p>Fuente: <code>eda_ia_consolidado.csv</code>. Filtra por columna <b>dataset</b> para ver diferentes bloques.</p>`;

    // Secciones: resumen, edad_stats, por_fecha, por_facultad, por_carrera, freq_simple, freq_multi, cross_*
    const datasets = groupBy(eda, x => x.dataset);
    // Resumen
    if(datasets.resumen){
      renderTable("Resumen", ["metric","value"], datasets.resumen);
    }
    if(datasets.edad_stats){
      renderTable("Edad — Stats", ["metric","value"], datasets.edad_stats, true);
    }
    if(datasets.por_fecha){
      renderTable("Respuestas por Fecha", ["fecha","conteo"], datasets.por_fecha);
    }
    if(datasets.por_facultad){
      renderTable("Respuestas por Facultad", ["facultad","conteo"], datasets.por_facultad);
    }
    if(datasets.por_carrera){
      renderTable("Respuestas por Carrera", ["carrera","conteo"], datasets.por_carrera);
    }
    if(datasets.freq_simple){
      renderTable("Frecuencias Simples", ["campo","categoria","conteo"], datasets.freq_simple);
    }
    if(datasets.freq_multi){
      renderTable("Frecuencias Multiselección", ["campo","categoria","conteo"], datasets.freq_multi);
    }
    if(datasets.cross_facultad_familiaridad){
      renderTable("Facultad × Familiaridad", ["facultad","familiaridad","conteo"], datasets.cross_facultad_familiaridad);
    }
    if(datasets.cross_facultad_confianza){
      renderTable("Facultad × Confianza", ["facultad","confianza","conteo"], datasets.cross_facultad_confianza);
    }
  }

  function renderRaw(raw){
    const info = document.getElementById("csvInfo");
    info.innerHTML = `<p>Fuente: <code>respuestas_ia.csv</code>. Muestra los datos crudos exportados.</p>`;
    renderTable("Respuestas (raw)", raw._headers, raw);
  }

  function groupBy(arr, keyFn){
    const out = {};
    for(const x of arr){
      const k = keyFn(x) || "_";
      (out[k] ||= []).push(x);
    }
    return out;
  }
})();
