const $=s=>document.querySelector(s);
let orders=[];
let deletedOrders=[];
function msg(el,text,ok=false){el.textContent=text;el.className="message "+(ok?"ok":"error");}
function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function normalizeOrders(d){return Array.isArray(d)?d:(d.orders||d.items||[]);}
function money(v){return Number(v||0).toFixed(2);}
function table(rows,actions=""){
 if(!rows.length)return '<p class="muted">No records found.</p>';

 return `<table>
 <thead>
  <tr>
   <th>Order</th>
   <th>Customer</th>
   <th>Email</th>
   <th>Total</th>
   <th>Status</th>
   <th>Actions</th>
  </tr>
 </thead>
 <tbody>`+
 rows.map(o=>{
   const id=esc(o.order_id);

   const viewButton=
     `<button class="small" onclick="viewOrderDetails('${id}')">View Details</button>`;

   const extraActions=actions
     ? actions.replaceAll("{id}",id)
     : "";

   return `<tr>
    <td>${id}</td>
    <td>${esc(o.customer_name)}</td>
    <td>${esc(o.customer_email)}</td>
    <td>R ${money(o.total)}</td>
    <td><span class="badge">${esc(o.status)}</span></td>
    <td>
      <div class="actions">
        ${viewButton}
        ${extraActions}
      </div>
    </td>
   </tr>`;
 }).join("")+
 "</tbody></table>";
}
async function refreshOrders(){
 try{orders=normalizeOrders(await getOrders()); renderOrders();}
 catch(e){console.error(e);}
}
function renderOrders(){
 $("#totalCount").textContent=orders.length;
 $("#queuedCount").textContent=orders.filter(o=>o.status==="QUEUED").length;
 $("#acceptedCount").textContent=orders.filter(o=>o.status==="ACCEPTED").length;
 $("#completedCount").textContent=orders.filter(o=>o.status==="COMPLETED").length;
 $("#recentOrders").innerHTML=table(orders.slice(0,8));
 renderFilteredOrders();
 setupOrderFilters();
 setupOrderDetailsModal();
 if(isAdmin()){
  $("#pendingTable").innerHTML=table(orders.filter(o=>o.status==="QUEUED"),'<div class="actions"><button class="small primary" onclick="statusOrder(\'{id}\',\'ACCEPTED\')">Accept</button><button class="small danger" onclick="removeOrder(\'{id}\')">Delete</button></div>');
  $("#acceptedTable").innerHTML=table(orders.filter(o=>o.status==="ACCEPTED"),'<div class="actions"><button class="small primary" onclick="statusOrder(\'{id}\',\'COMPLETED\')">Mark Complete</button><button class="small danger" onclick="removeOrder(\'{id}\')">Delete</button></div>');
  $("#completedTable").innerHTML=table(orders.filter(o=>o.status==="COMPLETED"),'<div class="actions"><button class="small danger" onclick="removeOrder(\'{id}\')">Delete</button></div>');
 }
}

let orderCurrentPage = 1;
const orderPageSize = 10;

function getFilteredOrders(){
 const searchEl=$("#orderSearch");
 const statusEl=$("#orderStatusFilter");

 const search=(searchEl?.value||"").trim().toLowerCase();
 const status=(statusEl?.value||"ALL").toUpperCase();

 return orders.filter(o=>{
   const orderStatus=String(o.status||"").trim().toUpperCase();

   const searchable=[
     o.order_id,
     o.customer_name,
     o.customer_email
   ].map(v=>String(v||"").toLowerCase()).join(" ");

   const matchesSearch=!search || searchable.includes(search);
   const matchesStatus=status==="ALL" || orderStatus===status;

   return matchesSearch && matchesStatus;
 });
}

function renderFilteredOrders(){
 const tableEl=$("#ordersTable");
 const summaryEl=$("#orderFilterSummary");
 const pageInfo=$("#orderPageInfo");
 const prevBtn=$("#prevOrderPage");
 const nextBtn=$("#nextOrderPage");

 if(!tableEl)return;

 const filtered=getFilteredOrders();

 const totalPages=Math.max(
   1,
   Math.ceil(filtered.length/orderPageSize)
 );

 if(orderCurrentPage>totalPages){
   orderCurrentPage=totalPages;
 }

 if(orderCurrentPage<1){
   orderCurrentPage=1;
 }

 const start=(orderCurrentPage-1)*orderPageSize;
 const end=start+orderPageSize;

 const pageOrders=filtered.slice(start,end);

 tableEl.innerHTML=table(pageOrders);

 if(summaryEl){
   if(filtered.length===0){
     summaryEl.textContent=`Showing 0 of ${orders.length} orders`;
   }
   else{
     const first=start+1;
     const last=Math.min(end,filtered.length);

     summaryEl.textContent=
       `Showing ${first}-${last} of ${filtered.length} matching order${filtered.length===1?"":"s"} (${orders.length} total)`;
   }
 }

 if(pageInfo){
   pageInfo.textContent=`Page ${orderCurrentPage} of ${totalPages}`;
 }

 if(prevBtn){
   prevBtn.disabled=orderCurrentPage<=1;
 }

 if(nextBtn){
   nextBtn.disabled=orderCurrentPage>=totalPages;
 }
}

function setupOrderFilters(){
 const searchEl=$("#orderSearch");
 const statusEl=$("#orderStatusFilter");
 const clearBtn=$("#clearOrderFilters");
 const prevBtn=$("#prevOrderPage");
 const nextBtn=$("#nextOrderPage");

 if(searchEl && !searchEl.dataset.filterReady){
   searchEl.addEventListener("input",()=>{
     orderCurrentPage=1;
     renderFilteredOrders();
   });

   searchEl.dataset.filterReady="true";
 }

 if(statusEl && !statusEl.dataset.filterReady){
   statusEl.addEventListener("change",()=>{
     orderCurrentPage=1;
     renderFilteredOrders();
   });

   statusEl.dataset.filterReady="true";
 }

 if(clearBtn && !clearBtn.dataset.filterReady){
   clearBtn.addEventListener("click",()=>{
     if(searchEl) searchEl.value="";
     if(statusEl) statusEl.value="ALL";

     orderCurrentPage=1;
     renderFilteredOrders();
   });

   clearBtn.dataset.filterReady="true";
 }

 if(prevBtn && !prevBtn.dataset.pageReady){
   prevBtn.addEventListener("click",()=>{
     if(orderCurrentPage>1){
       orderCurrentPage--;
       renderFilteredOrders();
     }
   });

   prevBtn.dataset.pageReady="true";
 }

 if(nextBtn && !nextBtn.dataset.pageReady){
   nextBtn.addEventListener("click",()=>{
     const filtered=getFilteredOrders();

     const totalPages=Math.max(
       1,
       Math.ceil(filtered.length/orderPageSize)
     );

     if(orderCurrentPage<totalPages){
       orderCurrentPage++;
       renderFilteredOrders();
     }
   });

   nextBtn.dataset.pageReady="true";
 }
}
function formatOrderDate(value){
 if(!value)return "—";

 const d=new Date(value);

 if(Number.isNaN(d.getTime())){
   return esc(value);
 }

 return d.toLocaleString();
}

function orderItemsHtml(items){
 if(!Array.isArray(items) || !items.length){
   return '<p class="muted">No item information available.</p>';
 }

 return `
 <div class="order-items-wrap">
  <table class="order-items-table">
   <thead>
    <tr>
     <th>Product</th>
     <th>Qty</th>
     <th>Unit Price</th>
     <th>Subtotal</th>
    </tr>
   </thead>

   <tbody>
    ${items.map(item=>{
      const product=item.product || item.name || "";
      const quantity=Number(item.quantity ?? item.qty ?? 0);
      const price=Number(item.price ?? 0);
      const subtotal=quantity*price;

      return `
       <tr>
        <td>${esc(product)}</td>
        <td>${quantity}</td>
        <td>R ${money(price)}</td>
        <td>R ${money(subtotal)}</td>
       </tr>`;
    }).join("")}
   </tbody>
  </table>
 </div>`;
}

function viewOrderDetails(orderId){
 const order=
   orders.find(
     o=>String(o.order_id)===String(orderId)
   ) ||
   deletedOrders.find(
     o=>String(o.order_id)===String(orderId)
   );

 if(!order){
   alert("Order details could not be found.");
   return;
 }

 const modal=$("#orderDetailsModal");
 const content=$("#orderDetailsContent");
 const orderIdEl=$("#detailOrderId");

 if(!modal || !content)return;

 if(orderIdEl){
   orderIdEl.textContent=order.order_id || "";
 }

 const status=String(order.status||"").toUpperCase();

 content.innerHTML=`
  <div class="order-detail-status">
   <span class="badge">${esc(status)}</span>
  </div>

  <div class="order-detail-grid">

   <div class="order-detail-box">
    <span>Customer</span>
    <strong>${esc(order.customer_name || "—")}</strong>
   </div>

   <div class="order-detail-box">
    <span>Email</span>
    <strong>${esc(order.customer_email || "—")}</strong>
   </div>

   <div class="order-detail-box">
    <span>Status</span>
    <strong>${esc(status || "—")}</strong>
   </div>

   <div class="order-detail-box">
    <span>Order Total</span>
    <strong>R ${money(order.total || 0)}</strong>
   </div>

  </div>

  <div class="order-detail-section">
   <h4>Items</h4>
   ${orderItemsHtml(order.items)}
  </div>

  <div class="order-detail-section">
   <h4>Timeline</h4>

   <div class="order-timeline">

    <div>
     <span>Created</span>
     <strong>${formatOrderDate(order.created_at)}</strong>
    </div>

    <div>
     <span>Queued</span>
     <strong>${formatOrderDate(order.queued_at)}</strong>
    </div>

    <div>
     <span>Accepted</span>
     <strong>${formatOrderDate(order.accepted_at)}</strong>
     <small>By: ${esc(order.accepted_by || "—")}</small>
    </div>

    <div>
     <span>Completed / Processed</span>
     <strong>${formatOrderDate(
       order.completed_at ||
       order.processed_at
     )}</strong>
     <small>By: ${esc(order.completed_by || "—")}</small>
    </div>
     ${order.deleted_at ? `
     <div>
      <span>Deleted</span>
      <strong>${formatOrderDate(order.deleted_at)}</strong>
      <small>By: ${esc(order.deleted_by || "—")}</small>
     </div>` : ""}

     ${order.restored_at ? `
     <div>
      <span>Restored</span>
      <strong>${formatOrderDate(order.restored_at)}</strong>
      <small>By: ${esc(order.restored_by || "—")}</small>
     </div>` : ""}

   </div>
  </div>
 `;

 modal.classList.remove("hidden");
}

function closeOrderDetailsModal(){
 const modal=$("#orderDetailsModal");

 if(modal){
   modal.classList.add("hidden");
 }
}

function setupOrderDetailsModal(){
 const modal=$("#orderDetailsModal");
 const closeBtn=$("#closeOrderDetails");
 const closeX=$("#closeOrderDetailsX");

 if(closeBtn && !closeBtn.dataset.ready){
   closeBtn.addEventListener(
     "click",
     closeOrderDetailsModal
   );

   closeBtn.dataset.ready="true";
 }

 if(closeX && !closeX.dataset.ready){
   closeX.addEventListener(
     "click",
     closeOrderDetailsModal
   );

   closeX.dataset.ready="true";
 }

 if(modal && !modal.dataset.ready){
   modal.addEventListener("click",e=>{
     if(e.target===modal){
       closeOrderDetailsModal();
     }
   });

   modal.dataset.ready="true";
 }

 if(!document.body.dataset.orderEscapeReady){
   document.addEventListener("keydown",e=>{
     if(e.key==="Escape"){
       closeOrderDetailsModal();
     }
   });

   document.body.dataset.orderEscapeReady="true";
 }
}
async function statusOrder(id,status){if(!confirm(`Change ${id} to ${status}?`))return;try{await patchAdminOrder(id,status);await refreshOrders();}catch(e){alert(e.message);}}
async function removeOrder(id){
 if(!confirm(`Move ${id} to Deleted Orders? You can restore it later.`))return;

 try{
  await deleteAdminOrder(id);
  await refreshOrders();

  if(isAdmin()){
   await refreshDeletedOrders();
  }
 }catch(e){
  alert(e.message);
 }
}

async function refreshDeletedOrders(){
 if(!isAdmin())return;

 const tableEl=$("#deletedOrdersTable");
 if(!tableEl)return;

 try{
  const data=await getDeletedOrders();
  deletedOrders=normalizeOrders(data);
  renderDeletedOrders();
 }catch(e){
  console.error(e);
  tableEl.innerHTML=
   `<p class="message error">${esc(e.message)}</p>`;
 }
}

function renderDeletedOrders(){
 const tableEl=$("#deletedOrdersTable");
 if(!tableEl)return;

 if(!deletedOrders.length){
  tableEl.innerHTML=
   '<p class="muted">Recycle Bin is empty.</p>';
  return;
 }

 tableEl.innerHTML=`
  <table>
   <thead>
    <tr>
     <th>Order</th>
     <th>Customer</th>
     <th>Email</th>
     <th>Original Status</th>
     <th>Deleted At</th>
     <th>Deleted By</th>
     <th>Actions</th>
    </tr>
   </thead>
   <tbody>
    ${deletedOrders.map(order=>{
      const id=esc(order.order_id);

      return `
       <tr>
        <td>${id}</td>
        <td>${esc(order.customer_name || "—")}</td>
        <td>${esc(order.customer_email || "—")}</td>
        <td>
         <span class="badge">
          ${esc(order.previous_status || "—")}
         </span>
        </td>
        <td>${formatOrderDate(order.deleted_at)}</td>
        <td>${esc(order.deleted_by || "—")}</td>
        <td>
         <div class="actions">
          <button
           class="small"
           onclick="viewOrderDetails('${id}')">
           View Details
          </button>

          <button
           class="small primary"
           onclick="restoreDeletedOrder('${id}')">
           Restore
          </button>
         </div>
        </td>
       </tr>`;
    }).join("")}
   </tbody>
  </table>`;
}

async function restoreDeletedOrder(id){
 const order=deletedOrders.find(
  o=>String(o.order_id)===String(id)
 );

 const previousStatus=
  order?.previous_status || "previous status";

 if(
  !confirm(
   `Restore ${id} to ${previousStatus}?`
  )
 ){
  return;
 }

 try{
  await restoreAdminOrder(id);
  await refreshDeletedOrders();
  await refreshOrders();
 }catch(e){
  alert(e.message);
 }
}
async function refreshUsers(){
 if(!isAdmin())return;

 try{
  const d=await getUsers();
  const users=Array.isArray(d)?d:(d.users||[]);

  $("#usersTable").innerHTML=users.length
   ? `<table>
       <thead>
        <tr>
         <th>Name</th>
         <th>Surname</th>
         <th>Email</th>
         <th>Status</th>
         <th>Role</th>
         <th>Actions</th>
        </tr>
       </thead>
       <tbody>`+

       users.map(u=>{
        const username=u.username||u.Username||"";
        const givenName=u.given_name||u.GivenName||"";
        const familyName=u.family_name||u.FamilyName||"";
        const email=u.email||u.Email||"";
        const enabled=u.enabled??u.Enabled;
        const admin=u.is_admin??u.admin??u.IsAdmin??false;

        return `<tr>
         <td>${esc(givenName||"—")}</td>
         <td>${esc(familyName||"—")}</td>
         <td>${esc(email)}</td>
         <td>${enabled?"Enabled":"Disabled"}</td>
         <td>${admin?"Administrator":"User"}</td>
         <td class="actions">
          <button
           class="small"
           onclick="toggleUser('${esc(username)}',${!enabled})">
           ${enabled?"Disable":"Enable"}
          </button>

          <button
           class="small"
           onclick="toggleAdmin('${esc(username)}',${!admin})">
           ${admin?"Revoke Admin":"Grant Admin"}
          </button>

          <button
           class="small danger"
           onclick="removeUser('${esc(username)}')">
           Delete
          </button>
         </td>
        </tr>`;
       }).join("")+

       "</tbody></table>"

   : '<p class="muted">No users found.</p>';

 }catch(e){
  $("#usersTable").innerHTML=
   `<p class="message error">${esc(e.message)}</p>`;
 }
}
async function toggleUser(u,enable){try{await patchUser(u,{action:enable?"enable":"disable"});await refreshUsers();}catch(e){alert(e.message);}}
async function toggleAdmin(u,grant){try{await patchUser(u,{action:grant?"grant_admin":"revoke_admin"});await refreshUsers();}catch(e){alert(e.message);}}
async function removeUser(u){if(!confirm(`Delete user ${u}?`))return;try{await deleteUser(u);await refreshUsers();}catch(e){alert(e.message);}}
function addItem(){
 const d=document.createElement("div");d.className="item-row";d.innerHTML='<div><label>Product</label><input class="product" required></div><div><label>Qty</label><input class="qty" type="number" min="1" value="1" required></div><div><label>Price</label><input class="price" type="number" min="0" step="0.01" value="0" required></div><button type="button" onclick="this.parentElement.remove();calcTotal()">Remove</button>';
 $("#items").appendChild(d);d.querySelectorAll("input").forEach(i=>i.addEventListener("input",calcTotal));calcTotal();
}
function calcTotal(){let t=0;document.querySelectorAll(".item-row").forEach(r=>t+=(+r.querySelector(".qty").value||0)*(+r.querySelector(".price").value||0));$("#orderTotal").textContent=money(t);}
function showPage(name){
 document.querySelectorAll(".page").forEach(p=>p.classList.add("hidden"));$("#"+name+"Page").classList.remove("hidden");
 document.querySelectorAll(".nav[data-page]").forEach(b=>b.classList.toggle("active",b.dataset.page===name));
 $("#pageTitle").textContent={dashboard:"Dashboard",create:"Create Order",orders:"Orders",admin:"Admin Console"}[name];
 if(name==="admin"){
  refreshUsers();
  refreshOrders();
  refreshDeletedOrders();
 }else if(name!=="create"){
  refreshOrders();
 }
}
async function enterApp(){
 $("#loginView").classList.add("hidden");$("#appView").classList.remove("hidden");
 const p=jwtPayload(idToken);
 const fullName=[
   p.given_name||"",
   p.family_name||""
 ].filter(Boolean).join(" ").trim();

 $("#signedInUser").textContent=
   fullName ||
   p.email ||
   p["cognito:username"] ||
   "Signed in";
 $("#adminNav").classList.toggle("hidden",!isAdmin());await refreshOrders();
}
$("#loginForm").addEventListener("submit",async e=>{e.preventDefault();msg($("#loginMessage"),"Signing in...",true);try{await signIn($("#username").value.trim(),$("#password").value);$("#loginMessage").textContent="";await enterApp();}catch(x){msg($("#loginMessage"),x.message||String(x));}});
$("#logoutBtn").onclick=()=>{signOut();location.reload();};
document.querySelectorAll(".nav[data-page]").forEach(b=>b.onclick=()=>showPage(b.dataset.page));
$("#refreshBtn").onclick=async()=>{
 const btn=$("#refreshBtn");
 const originalText=btn.textContent;
 try{
   btn.disabled=true;
   btn.textContent="Refreshing...";
   await refreshOrders();
   if(!$("#adminPage").classList.contains("hidden")){
     await refreshUsers();
     await refreshDeletedOrders();
   }
   btn.textContent="✓ Refreshed";
   setTimeout(()=>{btn.textContent=originalText;btn.disabled=false;},1200);
 }catch(e){
   console.error(e);
   btn.textContent="Refresh failed";
   setTimeout(()=>{btn.textContent=originalText;btn.disabled=false;},2000);
 }
};
$("#addItemBtn").onclick=addItem;
$("#orderForm").addEventListener("submit",async e=>{e.preventDefault();const items=[...document.querySelectorAll(".item-row")].map(r=>({product:r.querySelector(".product").value.trim(),quantity:+r.querySelector(".qty").value,price:+r.querySelector(".price").value}));if(!items.length)return msg($("#orderMessage"),"Add at least one item.");try{const d=await createOrder({customer_name:$("#customerName").value.trim(),customer_email:$("#customerEmail").value.trim(),items});msg($("#orderMessage"),`Order ${d.order_id||""} accepted for processing.`,true);e.target.reset();$("#items").innerHTML="";addItem();await refreshOrders();}catch(x){msg($("#orderMessage"),x.message);}});
document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>{
 document.querySelectorAll(".tab").forEach(
  x=>x.classList.remove("active")
 );

 b.classList.add("active");

 document.querySelectorAll(".tabview").forEach(
  x=>x.classList.add("hidden")
 );

 $("#"+b.dataset.tab+"Tab").classList.remove("hidden");

 if(b.dataset.tab==="users"){
  refreshUsers();
 }
 else if(b.dataset.tab==="deleted"){
  refreshDeletedOrders();
 }
 else{
  refreshOrders();
 }
});
const refreshDeletedBtn=$("#refreshDeletedOrders");

if(refreshDeletedBtn){
 refreshDeletedBtn.onclick=async()=>{
  const originalText=refreshDeletedBtn.textContent;

  try{
   refreshDeletedBtn.disabled=true;
   refreshDeletedBtn.textContent="Refreshing...";
   await refreshDeletedOrders();
   refreshDeletedBtn.textContent="✓ Refreshed";

   setTimeout(()=>{
    refreshDeletedBtn.textContent=originalText;
    refreshDeletedBtn.disabled=false;
   },1200);
  }catch(e){
   refreshDeletedBtn.textContent="Refresh failed";

   setTimeout(()=>{
    refreshDeletedBtn.textContent=originalText;
    refreshDeletedBtn.disabled=false;
   },2000);
  }
 }
}
$("#addUserBtn").onclick=()=>$("#modal").classList.remove("hidden");$("#cancelModal").onclick=()=>$("#modal").classList.add("hidden");
$("#createUserBtn").onclick=async()=>{
 const givenName=$("#newGivenName").value.trim();
 const familyName=$("#newFamilyName").value.trim();
 const email=$("#newEmail").value.trim();
 const temporaryPassword=$("#newPassword").value;

 if(!givenName){
   return msg($("#modalMessage"),"Name is required.");
 }

 if(!familyName){
   return msg($("#modalMessage"),"Surname is required.");
 }

 if(!email){
   return msg($("#modalMessage"),"Email is required.");
 }

 if(!temporaryPassword){
   return msg($("#modalMessage"),"Temporary password is required.");
 }

 try{
   await createUser({
     given_name:givenName,
     family_name:familyName,
     email:email,
     temporary_password:temporaryPassword,
     is_admin:$("#newAdmin").checked
   });

   msg($("#modalMessage"),"User created.",true);

   $("#newGivenName").value="";
   $("#newFamilyName").value="";
   $("#newEmail").value="";
   $("#newPassword").value="";
   $("#newAdmin").checked=false;

   setTimeout(()=>{
     $("#modal").classList.add("hidden");
     $("#modalMessage").textContent="";
     refreshUsers();
   },500);

 }catch(e){
   msg($("#modalMessage"),e.message);
 }
};
addItem();restoreSession().then(ok=>{if(ok)enterApp();});









