import { useEffect, useState } from "react";
import { getCurrentUser, login, logout, register, invite, resetPassword } from "../../services/authApi";
import "../../styles/auth.css";

export default function AuthGate({children}) {
  const [user,setUser]=useState(null);
  const [loading,setLoading]=useState(true);
  const [mode,setMode]=useState(new URLSearchParams(location.search).has("invite") ? "register" : "login");
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [working,setWorking]=useState(false);
  const [inviteToken,setInviteToken]=useState(new URLSearchParams(location.search).get("invite")||"");
  const [name,setName]=useState("");
  const [email,setEmail]=useState("");
  const [password,setPassword]=useState("");
  const [invitation,setInvitation]=useState(null);
  const [inviteEmail,setInviteEmail]=useState("");
  useEffect(()=>{getCurrentUser().then(setUser).catch(()=>{}).finally(()=>setLoading(false));},[]);
  async function submit(event){
    event.preventDefault();setError("");setNotice("");setWorking(true);
    try {
      if(mode==="login") setUser(await login(email,password));
      if(mode==="register") {await register(inviteToken,email,name,password);setNotice("Account created. Email verification must be completed before login is allowed.");setMode("login");}
      if(mode==="reset") {await resetPassword(inviteToken,password);setNotice("Password updated. You may sign in.");setMode("login");}
    } catch(err){setError(err.message);} finally{setWorking(false);}
  }
  async function signout(){setError("");try{await logout();setUser(null);}catch(err){setError(err.message);}}
  async function makeInvitation(e){e.preventDefault();setWorking(true);setError("");try{setInvitation(await invite(inviteEmail));}catch(err){setError(err.message);}finally{setWorking(false);}}
  if(loading) return <div className="auth-loading" role="status">Checking your session…</div>;
  if(user) return <><div className="auth-userbar"><span>Signed in as <b>{user.full_name}</b></span>{user.role==="admin"&&<button onClick={()=>setMode(mode==="invite"?"login":"invite")}>Invite user</button>}<button onClick={signout}>Sign out</button></div>{error&&<p className="auth-floating-error" role="alert">{error}</p>}{mode==="invite"&&user.role==="admin"&&<div className="auth-admin"><form onSubmit={makeInvitation}><label>Invite email<input type="email" required value={inviteEmail} onChange={e=>setInviteEmail(e.target.value)}/></label><button disabled={working}>Generate invitation</button></form>{invitation&&<div><p>Share this single-use link securely:</p><code>{`${location.origin}/?invite=${encodeURIComponent(invitation.token)}`}</code><p className="auth-hint">This token is shown once. Do not publish it.</p></div>}</div>}{children}</>;
  return <div className="auth-screen"><aside className="auth-hero"><div className="auth-brand"><span className="auth-mark">◉</span> Roulette<span>IQ</span></div><div className="auth-hero-copy"><p className="auth-eyebrow">PRIVATE ANALYTICS WORKSPACE</p><h1>Every spin.<br/><em>A clearer picture.</em></h1><p>Explore your roulette sessions and analytics from a private, account-based workspace.</p><div className="auth-tags"><span>Session tracking</span><span>Analytics</span><span>Private access</span></div></div><p className="auth-foot">RouletteIQ · Development build</p></aside><main className="auth-panel"><div className="auth-form-wrap"><div className="auth-mobile-brand">◉ Roulette<span>IQ</span></div><div className="auth-pill">SECURE ACCESS</div><h2>{mode==="register"?"Accept your invitation":mode==="reset"?"Set a new password":"Welcome back"}</h2><p className="auth-subtitle">{mode==="register"?"Registration is available by invitation only.":mode==="reset"?"Use the reset token from your secure link.":"Sign in to your RouletteIQ workspace."}</p>{error&&<div className="auth-alert" role="alert">{error}</div>}{notice&&<div className="auth-success" role="status">{notice}</div>}<form onSubmit={submit}>{mode!=="login"&&<label>{mode==="register"?"Invitation token":"Reset token"}<input required value={inviteToken} onChange={e=>setInviteToken(e.target.value)}/></label>}{mode==="register"&&<label>Full name<input required maxLength={150} autoComplete="name" value={name} onChange={e=>setName(e.target.value)}/></label>}{mode!=="reset"&&<label>Email address<input type="email" required autoComplete="email" placeholder="you@example.com" value={email} onChange={e=>setEmail(e.target.value)}/></label>}<label>Password<input type="password" required minLength={mode==="login"?1:12} autoComplete={mode==="login"?"current-password":"new-password"} placeholder="Enter your password" value={password} onChange={e=>setPassword(e.target.value)}/></label><button className="auth-submit" disabled={working}>{working?"Please wait…":mode==="register"?"Create account":mode==="reset"?"Update password":"Sign in"}</button></form><div className="auth-switch">{mode!=="login"?<button onClick={()=>{setMode("login");setError("");}}>Back to sign in</button>:<p>Need access? Ask your administrator for an invitation.</p>}</div><p className="auth-hint">Secure HttpOnly sessions · Mobile-ready</p></div></main></div>;
}
