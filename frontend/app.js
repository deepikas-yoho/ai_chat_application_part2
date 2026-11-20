const API = "http://127.0.0.1:8000";
const $ = id => document.getElementById(id);
let currentSession = null, abortController = null, busy = false;

$("apiKey").value = localStorage.getItem("appApiKey") || "local-demo-key";
$("saveKey").onclick = () => {
  localStorage.setItem("appApiKey", $("apiKey").value.trim());
  notice("API key saved in this browser.");
  loadSessions();
};
function notice(text=""){ $("notice").textContent = text; }
function setBusy(value){ busy=value; $("sendButton").disabled=value; $("stopButton").disabled=!value; $("status").textContent=value?"Generating…":"Ready"; }
function headers(){ return {"Content-Type":"application/json","X-API-Key":$("apiKey").value.trim()}; }
async function request(path, options={}) {
  const response = await fetch(API+path,{...options,headers:{...headers(),...(options.headers||{})}});
  if(!response.ok){let detail=`Request failed (${response.status})`;try{detail=(await response.json()).detail||detail}catch{};throw new Error(detail)}
  return response;
}
function addMessage(role,content){
  const empty=$("messages").querySelector(".welcome");if(empty)empty.remove();
  const div=document.createElement("div");div.className=`message ${role}`;div.textContent=content;
  $("messages").appendChild(div);$("messages").scrollTop=$("messages").scrollHeight;return div;
}
async function loadSessions(){
  try{
    const data=await (await request("/api/sessions")).json();$("sessions").innerHTML="";
    data.forEach(s=>{const el=document.createElement("div");el.className="session"+(s.id===currentSession?" active":"");el.textContent=s.title;el.onclick=()=>openSession(s.id);$("sessions").appendChild(el)});
  }catch(e){notice(e.message)}
}
async function newSession(){
  try{const s=await (await request("/api/sessions",{method:"POST",body:JSON.stringify({title:"New chat"})})).json();currentSession=s.id;$("messages").innerHTML="";await loadSessions();$("messageInput").focus()}
  catch(e){notice(e.message)}
}
async function openSession(id){
  try{currentSession=id;const messages=await (await request(`/api/sessions/${id}/messages`)).json();$("messages").innerHTML="";
    messages.forEach(m=>addMessage(m.role,m.content));await loadSessions();notice("");
  }catch(e){notice(e.message)}
}
$("newChat").onclick=newSession;
$("chatForm").onsubmit=async e=>{
  e.preventDefault();const message=$("messageInput").value.trim();if(!message||busy)return;
  if(!currentSession)await newSession();if(!currentSession)return;
  $("messageInput").value="";addMessage("user",message);const output=addMessage("assistant","");
  setBusy(true);notice("");abortController=new AbortController();
  try{
    const response=await request(`/api/sessions/${currentSession}/stream`,{method:"POST",body:JSON.stringify({message}),signal:abortController.signal});
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer="";
    while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});
      const events=buffer.split("\n\n");buffer=events.pop();
      for(const event of events){if(event.startsWith("event: done"))continue;
        for(const line of event.split("\n"))if(line.startsWith("data: "))output.textContent+=line.slice(6);
      }
      $("messages").scrollTop=$("messages").scrollHeight;
    }
    await loadSessions();
  }catch(e){if(e.name==="AbortError")notice("Generation stopped.");else notice(e.message)}
  finally{abortController=null;setBusy(false)}
};
$("stopButton").onclick=()=>{if(abortController)abortController.abort()};
loadSessions();
