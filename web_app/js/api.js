async function api(method,path,body=null,extraHeaders={}){
 const headers={"Authorization":idToken,...extraHeaders};
 if(body!==null)headers["Content-Type"]="application/json";
 const r=await fetch(CONFIG.apiBase+path,{method,headers,body:body===null?undefined:JSON.stringify(body),cache:"no-store"});
 let data={}; try{data=await r.json();}catch{}
 if(!r.ok)throw new Error(data.message||data.error||`Request failed (${r.status})`);
 return data;
}
const getOrders=()=>api("GET","/orders");
const createOrder=(o)=>api("POST","/orders",o,{"Idempotency-Key":crypto.randomUUID()});
const getUsers=()=>api("GET","/admin/users");
const createUser=(o)=>api("POST","/admin/users",o);
const patchUser=(u,o)=>api("PATCH","/admin/users/"+encodeURIComponent(u),o);
const deleteUser=(u)=>api("DELETE","/admin/users/"+encodeURIComponent(u));
const patchAdminOrder=(id,status)=>api("PATCH","/admin/orders/"+encodeURIComponent(id),{status});
const deleteAdminOrder=(id)=>api("DELETE","/admin/orders/"+encodeURIComponent(id));
const getDeletedOrders=()=>api("GET","/admin/orders/deleted");
const restoreAdminOrder=(id)=>api("PATCH","/admin/orders/"+encodeURIComponent(id)+"/restore");

