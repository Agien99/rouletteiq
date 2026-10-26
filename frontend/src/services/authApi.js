import apiConfig from '../config/api';
const base=apiConfig.baseUrl;
const csrf=()=>decodeURIComponent(document.cookie.split(';').map(s=>s.trim()).find(s=>s.startsWith('rouletteiq_csrf='))?.split('=')[1]||'');
export async function authRequest(path,method='GET',body) {
 const headers={'Content-Type':'application/json'};
 if(method!=='GET'&&csrf())headers['x-csrf-token']=csrf();
 const response=await fetch(`${base}/auth${path}`,{method,credentials:'include',headers,...(body===undefined?{}:{body:JSON.stringify(body)})});
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:`Request failed (${response.status}).`);
 return data;
}
export const getCurrentUser=()=>authRequest('/me');
export const login=(email,password)=>authRequest('/login','POST',{email,password});
export const register=(token,email,full_name,password)=>authRequest('/register','POST',{token,email,full_name,password});
export const logout=()=>authRequest('/logout','POST');
export const invite=(email,expiry_hours=48)=>authRequest('/invitations','POST',{email,expiry_hours});
export const resetPassword=(token,password)=>authRequest('/reset-password','POST',{token,password});
export const requestPasswordReset=email=>authRequest('/request-password-reset','POST',{email});
export const requestVerification=email=>authRequest('/request-verification','POST',{email});
export const verifyEmail=token=>authRequest('/verify-email','POST',{token});
