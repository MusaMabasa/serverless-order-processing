const pool = new AmazonCognitoIdentity.CognitoUserPool({UserPoolId:CONFIG.userPoolId,ClientId:CONFIG.clientId});
let currentUser=null,idToken=null;

function jwtPayload(token){try{return JSON.parse(atob(token.split(".")[1].replace(/-/g,"+").replace(/_/g,"/")));}catch{return {};}}
function isAdmin(){const g=jwtPayload(idToken)["cognito:groups"]||[];return Array.isArray(g)?g.includes("Admins"):String(g).includes("Admins");}
function signIn(username,password){
 return new Promise((resolve,reject)=>{
  const user=new AmazonCognitoIdentity.CognitoUser({Username:username,Pool:pool});
  user.authenticateUser(new AmazonCognitoIdentity.AuthenticationDetails({Username:username,Password:password}),{
   onSuccess:r=>{currentUser=user;idToken=r.getIdToken().getJwtToken();startInactivityMonitor();resolve(r);},
   onFailure:reject,
   newPasswordRequired:(attrs,required)=>{
    const np=prompt("A new password is required for this account:");
    if(!np)return reject(new Error("New password is required."));
    delete attrs.email_verified; delete attrs.email;
    user.completeNewPasswordChallenge(np,attrs,{
      onSuccess:r=>{currentUser=user;idToken=r.getIdToken().getJwtToken();startInactivityMonitor();resolve(r);},
      onFailure:reject
    });
   }
  });
 });
}
function restoreSession(){
 return new Promise(resolve=>{
  const user=pool.getCurrentUser(); if(!user)return resolve(false);
  user.getSession((e,s)=>{if(e||!s?.isValid())return resolve(false);currentUser=user;idToken=s.getIdToken().getJwtToken();startInactivityMonitor();resolve(true);});
 });
}

// ============================================================
// BlueIT inactivity security
// ============================================================

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000;

let inactivityTimer = null;
let lastActivityReset = 0;
let inactivityListenersInstalled = false;

function performInactivityLogout(){
 if(!currentUser && !idToken){
   return;
 }

 signOut();

 try{
   sessionStorage.setItem(
     "blueitLogoutReason",
     "inactive"
   );
 }catch{}

 location.reload();
}

function resetInactivityTimer(){
 if(!currentUser || !idToken){
   return;
 }

 const now=Date.now();

 // Prevent mousemove/scroll from continuously rebuilding
 // the timeout many times per second.
 if(now-lastActivityReset < 1000){
   return;
 }

 lastActivityReset=now;

 if(inactivityTimer){
   clearTimeout(inactivityTimer);
 }

 inactivityTimer=setTimeout(
   performInactivityLogout,
   INACTIVITY_TIMEOUT_MS
 );
}

function startInactivityMonitor(){
 if(inactivityTimer){
   clearTimeout(inactivityTimer);
 }

 lastActivityReset=0;
 resetInactivityTimer();

 if(inactivityListenersInstalled){
   return;
 }

 [
   "mousedown",
   "keydown",
   "touchstart",
   "scroll",
   "mousemove"
 ].forEach(eventName=>{
   window.addEventListener(
     eventName,
     resetInactivityTimer,
     {passive:true}
   );
 });

 inactivityListenersInstalled=true;
}

function stopInactivityMonitor(){
 if(inactivityTimer){
   clearTimeout(inactivityTimer);
   inactivityTimer=null;
 }

 lastActivityReset=0;
}

function showLogoutReason(){
 let reason=null;

 try{
   reason=sessionStorage.getItem(
     "blueitLogoutReason"
   );

   sessionStorage.removeItem(
     "blueitLogoutReason"
   );
 }catch{}

 if(reason==="inactive"){
   const loginMessage=
     document.getElementById("loginMessage");

   if(loginMessage){
     loginMessage.textContent=
       "Your session ended after 30 minutes of inactivity.";

     loginMessage.classList.remove("success");
     loginMessage.classList.add("error");
   }
 }
}

window.addEventListener(
 "DOMContentLoaded",
 showLogoutReason
);
function signOut(){
 stopInactivityMonitor();

 if(currentUser){
   currentUser.signOut();
 }

 currentUser=null;
 idToken=null;
}
