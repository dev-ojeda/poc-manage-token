
export function renderKPIs(metrics) {
    const apiContainer = document.getElementById('kpiContainer');
    if (!apiContainer) return;
    apiContainer.innerHTML = "";
    metrics.forEach(m => {
        const el = document.createElement('div');
        el.className = 'p-2 border rounded shadow-sm bg-white';
        el.style.minWidth = '140px';
        el.innerHTML = `
      <div class="small text-muted">${m.name}</div>
      <div class="h5 mb-0">${m.avg}${m.name === 'CLS' ? '' : ' ms'}</div>
      <div class="small text-muted">count: ${m.count}</div>`;
        apiContainer.appendChild(el);
    });
}

export function renderEndpointsTable(endpoints) {
    const body = document.querySelector("#endpointsTable tbody");
    if (!body) return;
    body.innerHTML = "";
    let html = "";
    endpoints.forEach(ep => {
        html += `
            <tr>
                <td class="pointer" data-path="${ep.path}">${ep.path}</td>
                <td>${ep.role}</td>
                <td>${ep.requests}</td>
                <td>${ep.avg}</td>
                <td>${ep.max}</td>
            </tr>`;
    });
    //html.querySelector('td').addEventListener('click', (e) => showEndpointDetails(e));
    body.innerHTML = html;
}

function showEndpointDetails(ep) {
    const container = document.getElementById('endpointDetails');
    if (container) {
        container.innerHTML = `<h6>${ep.path}</h6>
      <p>Rol: ${ep.role} · Requests: ${ep.requests}</p>
      <p>Avg: ${ep.avg} ms · Max: ${ep.max} ms</p>`;
    }
}

export function renderErrors(errors) {
    const ul = document.getElementById('errorsList');
    if (!ul) return;
    ul.innerHTML = "";
    errors.forEach(err => {
        const li = document.createElement('li');
        li.className = 'list-group-item';
        li.textContent = `${err.ts} — ${err.msg}`;
        ul.appendChild(li);
    });
}

export function getBrowserInfo() {
    const ua = navigator.userAgent;
    let browser = "Desconocido";
    if (ua.includes("Chrome") && !ua.includes("Edg")) browser = "Chrome";
    else if (ua.includes("Firefox")) browser = "Firefox";
    else if (ua.includes("Safari") && !ua.includes("Chrome")) browser = "Safari";
    else if (ua.includes("Edg")) browser = "Edge";
    else if (ua.includes("OPR") || ua.includes("Opera")) browser = "Opera";

    let os = "Desconocido";
    if (ua.includes("Windows")) os = "Windows";
    else if (ua.includes("Mac OS")) os = "MacOS";
    else if (ua.includes("Linux")) os = "Linux";
    else if (/Android/.test(ua)) os = "Android";
    else if (/iPhone|iPad|iPod/.test(ua)) os = "iOS";

    return { browser, os };
}

export function setView(view) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('d-none'));
    const el = document.getElementById('view-' + view);
    if (el) el.classList.remove('d-none');

    document.querySelectorAll('#sidebar .list-group-item').forEach(l => l.classList.remove('active'));
    document.querySelector(`#sidebar .list-group-item[data-view="${view}"]`)?.classList.add('active');
}

export function updateLastRefresh(elementId) {
    const now = new Date().toLocaleString();
    const el = document.getElementById(elementId);
    if (el) el.textContent = `Última actualización: ${now}`;
}