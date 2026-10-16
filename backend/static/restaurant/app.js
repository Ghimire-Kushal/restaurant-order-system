(() => {
  const root = document.getElementById("app");
  const mode = document.body.dataset.mode || "customer";
  let token = document.body.dataset.token || "";
  let auth = "";
  let cart = null;
  const esc = (value) => String(value ?? "").replace(/[&<>\"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;", "'":"&#39;"}[c]));
  const money = (v) => Number(v || 0).toFixed(2);
  const request = async (url, options = {}) => {
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
    const headers = { ...(options.body ? {"Content-Type":"application/json"} : {}), ...(csrf && csrf !== "NOTPROVIDED" ? {"X-CSRFToken": csrf} : {}), ...(auth ? {Authorization:`Basic ${auth}`} : {}), ...(options.headers || {}) };
    const response = await fetch(url, {...options, credentials:"same-origin", headers});
    const type = response.headers.get("content-type") || "";
    const data = type.includes("json") ? await response.json() : await response.text();
    if (!response.ok) throw new Error(data?.message || `Request failed (${response.status})`);
    return data;
  };
  const fail = (error) => { root.innerHTML = `<div class="error">${esc(error.message || error)}</div>`; };
  const toast = (message) => { const node = document.createElement("div"); node.className="toast"; node.textContent=message; document.body.append(node); setTimeout(() => node.remove(), 2800); };
  const setContext = (text) => { document.getElementById("context").textContent = text; };

  async function startCustomer() {
    if (!token) throw new Error("This page needs a table QR token.");
    const scan = await request(`/table/scan/${token}/`);
    token = scan.session.session_token;
    setContext(`Table ${scan.table.number}${scan.table.name ? ` · ${scan.table.name}` : ""}`);
    await loadMenu();
  }
  async function loadMenu() {
    const data = await request(`/api/menu/${token}/`);
    const sections = data.menu || [];
    root.innerHTML = `<section class="hero"><div><p class="muted">Welcome to the table</p><h1>Choose your meal</h1><p class="muted">Your order stays linked to this table session.</p></div><button id="refresh">Refresh menu</button></section><div id="menu"></div><aside id="cart" class="panel cart"></aside>`;
    document.getElementById("refresh").onclick = loadMenu;
    document.getElementById("menu").innerHTML = sections.length ? sections.map(section => `<section><h2>${esc(section.name)}</h2>${section.categories.map(category => `<h3>${esc(category.name)}</h3><div class="menu-grid">${category.food_items.map(foodCard).join("")}</div>`).join("")}</section>`).join("") : `<div class="empty">The menu is currently empty.</div>`;
    document.querySelectorAll("[data-add]").forEach(button => button.onclick = () => addToCart(button.dataset.add).catch(fail));
    await loadCart();
  }
  const foodCache = {};
  function foodCard(item) {
    foodCache[item.id] = item;
    const spice = item.spice_levels?.length ? `<label>Spice<select data-spice="${item.id}"><option value="">No preference</option>${item.spice_levels.map(x => `<option value="${x.id}">${esc(x.name)}</option>`).join("")}</select></label>` : "";
    const addons = item.addons?.length ? `<label>Add-ons</label>${item.addons.map(x => `<label class="row"><input type="checkbox" data-addon="${item.id}" value="${x.id}"><span>${esc(x.name)}</span><span>${money(x.price)}</span></label>`).join("")}` : "";
    return `<article class="food"><div class="grow"><h3>${esc(item.name)}</h3><p class="muted">${esc(item.description || "")}</p><p class="price">${money(item.price)}</p>${spice}${addons}${item.allow_special_instruction ? `<label>Note<textarea data-note="${item.id}" rows="2" placeholder="Optional kitchen note"></textarea></label>` : ""}</div><button data-add="${item.id}">Add to cart</button></article>`;
  }
  async function addToCart(id) {
    const spice = document.querySelector(`[data-spice="${id}"]`)?.value || null;
    const addons = [...document.querySelectorAll(`[data-addon="${id}"]:checked`)].map(x => Number(x.value));
    const note = document.querySelector(`[data-note="${id}"]`)?.value || "";
    const data = await request(`/api/cart/${token}/add/`, {method:"POST", body:JSON.stringify({food_item_id:Number(id), quantity:1, spice_level_id:spice ? Number(spice) : null, addon_ids:addons, special_instruction:note})});
    cart = data.cart; renderCart(); toast("Added to cart");
  }
  async function loadCart() { const data = await request(`/api/cart/${token}/`); cart = data.cart; renderCart(); }
  function renderCart() {
    const node = document.getElementById("cart"); if (!node) return;
    if (!cart?.items?.length) { node.innerHTML = `<h2>Your cart</h2><p class="empty">Your cart is empty.</p>`; return; }
    node.innerHTML = `<h2>Your cart</h2>${cart.items.map(item => `<div class="item-line"><div class="row"><strong>${esc(item.food_name)}</strong><span>${money(item.subtotal)}</span></div><small class="muted">${item.quantity} × ${money(item.unit_total)}${item.spice_name ? ` · ${esc(item.spice_name)}` : ""}</small><button class="secondary" data-remove="${item.id}">Remove</button></div>`).join("")}<div class="total"><span>Total</span><span>${money(cart.subtotal)}</span></div><button id="submit-order">Submit order</button>`;
    node.querySelectorAll("[data-remove]").forEach(b => b.onclick = async () => { try { const data = await request(`/api/cart/${token}/item/${b.dataset.remove}/remove/`, {method:"DELETE"}); cart=data.cart; renderCart(); } catch (error) { fail(error); } });
    node.querySelector("#submit-order").onclick = () => submitOrder().catch(fail);
  }
  async function submitOrder() { const data = await request(`/api/cart/${token}/submit/`, {method:"POST", body:"{}"}); renderOrder(data.order); }
  function renderOrder(order) { root.innerHTML = `<section class="hero"><div><p class="muted">Order confirmed</p><h1>${esc(order.order_number)}</h1><p class="muted">Table ${order.table_number} · ${esc(order.status_display)}</p></div><button id="track">Refresh status</button></section><div class="panel"><h2>We have your order</h2>${order.items.map(item => `<div class="item-line"><strong>${esc(item.food_name)}</strong> × ${item.quantity}<span class="price">${money(item.subtotal)}</span></div>`).join("")}<div class="total"><span>Total</span><span>${money(order.total_amount)}</span></div><p id="status" class="badge">${esc(order.status_display)}</p></div>`; document.getElementById("track").onclick = async () => { const data = await request(`/api/cart/${token}/order/${order.order_number}/`); document.getElementById("status").textContent=data.order.status_display; }; }

  function loginPrompt(kind) {
    root.innerHTML = `<section class="panel" style="max-width:440px;margin:40px auto"><h1>${kind} dashboard</h1><p class="muted">Use a staff account to continue.</p><label>Username<input id="username" autocomplete="username"></label><label>Password<input id="password" type="password" autocomplete="current-password"></label><button id="login">Sign in</button></section>`;
    document.getElementById("login").onclick = async () => { auth = btoa(`${document.getElementById("username").value}:${document.getElementById("password").value}`); await loadStaff(kind); };
  }
  async function loadStaff(kind, selectedStatus = "PENDING") { setContext(`${kind} workspace`); const endpoint = kind === "Kitchen" ? "/api/cart/kitchen/" : `/api/cart/reception/?status=${selectedStatus}`; const data = await request(endpoint); renderStaff(kind, data.orders || [], selectedStatus); }
  function renderStaff(kind, orders, selectedStatus) { root.innerHTML = `<section class="hero"><div><p class="muted">Operations</p><h1>${kind} dashboard</h1><p class="muted">${orders.length} order${orders.length === 1 ? "" : "s"}</p></div><div class="row">${kind === "Reception" ? '<select id="status-filter"><option value="PENDING">Pending</option><option value="RECEPTION_ACCEPTED">Accepted</option><option value="READY">Ready</option><option value="COMPLETED">Completed</option><option value="REJECTED">Rejected</option></select><button id="reports">Reports</button>' : '<span class="badge">Live preparation queue</span>'}<button id="reload">Refresh</button></div></section><div id="report" class="panel" hidden></div><div id="orders" class="grid">${orders.length ? orders.map(order => orderCard(kind, order)).join("") : `<div class="panel empty">No orders waiting.</div>`}</div>`; document.getElementById("status-filter")?.addEventListener("change", (event) => loadStaff(kind, event.target.value)); if (kind === "Reception") document.getElementById("status-filter").value=selectedStatus; document.getElementById("reload").onclick = () => loadStaff(kind, selectedStatus); document.getElementById("reports")?.addEventListener("click", showReports); bindStaff(kind); }
  function orderCard(kind, order) { const items = order.items.map(item => `<li><strong>${item.quantity} × ${esc(item.food_name)}</strong>${item.spice_name ? ` <span class="muted">· ${esc(item.spice_name)}</span>` : ""}${item.special_instruction ? ` <em class="muted">· ${esc(item.special_instruction)}</em>` : ""}</li>`).join(""); const actions = kind === "Reception" ? `<button data-action="accept" data-order="${order.order_number}">Accept order</button><button class="danger" data-action="reject" data-order="${order.order_number}">Reject</button><button class="secondary" data-action="discount" data-order="${order.order_number}">Discount</button><button class="secondary" data-action="pay" data-order="${order.order_number}">Cash paid</button><button class="secondary" data-action="release" data-order="${order.order_number}" data-table="${order.table}">Release table</button><a class="button secondary" target="_blank" href="/api/cart/reception/${order.order_number}/receipt/">Receipt</a>` : `<label>Prep minutes<select data-minutes="${order.order_number}"><option>15</option><option>20</option><option>25</option><option>30</option><option>35</option><option value="custom">Custom</option></select></label><input data-custom="${order.order_number}" type="number" min="1" placeholder="Custom minutes"><button data-action="start" data-order="${order.order_number}">Start preparation</button><button data-action="ready" data-order="${order.order_number}">Mark order ready</button>`; return `<article class="order"><div class="order-head"><div><div class="order-number">Order ${esc(order.order_number)}</div><h2>Table ${order.table_number}</h2></div><span class="badge">${esc(order.status_display)}</span></div><div class="order-meta"><span>● ${new Date(order.created_at).toLocaleString()}</span><span>${order.items.length} line item${order.items.length === 1 ? "" : "s"}</span></div><ul class="order-items">${items}</ul><div class="order-total"><span>Order total</span><span>${money(order.total_amount)}</span></div><div class="order-actions">${actions}</div></article>`; }
  async function showReports() { const data = await request("/api/cart/reports/"); const node=document.getElementById("report"); node.hidden=false; node.innerHTML=`<h2>Reports</h2><div class="grid"><div class="stat"><strong>Orders</strong><br>${data.orders.count}</div><div class="stat"><strong>Ordered total</strong><br>${money(data.sales.ordered_total)}</div><div class="stat"><strong>Collected</strong><br>${money(data.sales.collected_total)}</div><div class="stat"><strong>Popular item</strong><br>${esc(data.popular_items[0]?.food_name || "No sales yet")}</div></div>`; }
  function bindStaff(kind) { document.querySelectorAll("[data-action]").forEach(button => button.onclick = async () => { try { const action=button.dataset.action, number=button.dataset.order; let body={}; if (action === "reject") { const reason=prompt("Reason for rejection:"); if (!reason) return; body.reason=reason; } if (action === "discount") { const percentage=prompt("Discount percentage (0-100):","0"); if (percentage === null) return; await request(`/api/cart/reception/${number}/discount/`, {method:"POST",body:JSON.stringify({percentage})}); toast("Discount applied"); return loadStaff(kind); } if (action === "pay") { await request(`/api/cart/reception/${number}/payment/`, {method:"POST",body:JSON.stringify({method:"CASH"})}); toast("Cash payment recorded"); return loadStaff(kind, "READY"); } if (action === "release") { await request(`/api/cart/reception/table/${button.dataset.table}/release/`, {method:"POST",body:"{}"}); toast("Table released"); return loadStaff(kind); } if (action === "start") { const selected=document.querySelector(`[data-minutes="${number}"]`).value; body.preparation_minutes=selected === "custom" ? document.querySelector(`[data-custom="${number}"]`).value : selected; } await request(`${kind === "Reception" ? "/api/cart/reception/" : "/api/cart/kitchen/"}${number}/${action}/`, {method:"POST",body:JSON.stringify(body)}); toast("Updated"); loadStaff(kind); } catch (error) { toast(error.message || "Action failed"); } }); }

  if (mode === "customer") startCustomer().catch(fail);
  else loginPrompt(mode === "kitchen" ? "Kitchen" : "Reception");
})();
