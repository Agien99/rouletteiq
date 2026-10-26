import apiConfig from "../config/api";

const base = apiConfig.baseUrl;
const cookies = () => Object.fromEntries(document.cookie.split(";").map(s=>s.trim().split("=")));
export async function authRequest(path, method="GET", body=undefined) {
  const headers = { "Content-Type":"application/json" };
  if (method !== "GET") {
    const csrf = cookies().rouletteiq_csrf;
    if (csrf) headers["x-csrf-token"] = decodeURIComponent(csrf);
  }
  const response = await fetch(`${base}/auth${path}`, {
    method, credentials:"include", headers,
    ...(body === undefined ? {} : {body:JSON.stringify(body)})
  });
  const data = await response.json().catch(()=>({}));
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${response.status}).`);
  return data;
}
export const getCurrentUser = () => authRequest("/me");
export const login = (email,password) => authRequest("/login","POST",{email,password});
export const register = (token,email,full_name,password) => authRequest("/register","POST",{token,email,full_name,password});
export const logout = () => authRequest("/logout","POST");
export const invite = (email,expiry_hours=48) => authRequest("/invitations","POST",{email,expiry_hours});
export const resetPassword = (token,password) => authRequest("/reset-password","POST",{token,password});
