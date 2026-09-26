const prefix = window.location.pathname.replace(/\/$/, "");
const $ = id => document.getElementById(id);
let token = "", agents = [], catalog = [], editing = null, permissions = [], detailId = null;
const states = {QUEUED:"Na fila",RUNNING:"Em execução",SUCCEEDED:"Concluída",PARTIAL:"Parcial",FAILED:"Falhou",CANCELLED:"Cancelada"};
function notify(message, error=false) { $("notice").textContent=message; $("notice").className=error?"error":""; }
async function api(path, method="GET", data) {
  const response=await fetch(prefix+path,{method,credentials:"same-origin",headers:{"Content-Type":"application/json","X-Agentic-CSRF":token},body:data===undefined?undefined:JSON.stringify(data)});
  const body=await response.json();
  if(!response.ok) throw new Error(body.error?.message || "Falha HTTP "+response.status);
  return body;
}
function node(tag, text, cls) { const n=document.createElement(tag); n.textContent=text; if(cls)n.className=cls; return n; }
function button(label, action, disabled=false) { const b=node("button",label,"secondary"); b.type="button"; b.disabled=disabled; b.addEventListener("click",()=>Promise.resolve().then(action).catch(e=>notify(e.message,true))); return b; }
function canDesign(){ return permissions.some(r=>["AgentDesigner","PlatformAdministrator"].includes(r)); }
function canRun(){ return permissions.some(r=>["Operator","AgentDesigner","PlatformAdministrator"].includes(r)); }
function renderAgents(){
  $("agent-count").textContent=agents.length;
  $("agent-list").replaceChildren();
  if(!agents.length) $("agent-list").append(node("p","Nenhum agente cadastrado. Crie o primeiro com suas instruções e ferramentas."));
  for(const a of agents){
    const card=node("article", "", "agent-card"); card.append(node("h4",a.name),node("p",a.task),node("small",(a.enabled?"Ativo":"Pausado")+" · "+(a.interval_seconds?"A cada "+a.interval_seconds+"s":"Manual")+" · "+a.tools.length+" ferramentas · "+a.model));
    const actions=node("div","","actions");
    actions.append(button("Editar",()=>openEditor(a),!canDesign()),button(a.active_run?"Execução pendente":"Executar agora",async()=>{await api("/api/mvp/agents/"+a.id+"/runs","POST",{});notify("Execução adicionada à fila.");await refresh();},!canRun()||!a.enabled||!!a.active_run),button(a.enabled?"Pausar":"Ativar",async()=>{await api("/api/mvp/agents/"+a.id,"PUT",{...a,enabled:!a.enabled});notify("Configuração atualizada. Execuções já iniciadas podem terminar.");await refresh();},!canDesign()));
    card.append(actions);$("agent-list").append(card);
  }
}
function openEditor(agent=null){
  editing=agent;$("editor").hidden=false;$("editor-title").textContent=agent?"Editar agente":"Criar agente";
  for(const field of ["name","prompt","task"])$(field).value=agent?.[field]||"";
  $("model").value=agent?.model||$("model").dataset.default||"qwen2.5:3b";
  $("interval").value=agent?.interval_seconds||0;$("enabled").checked=agent?.enabled??true;
  $("tool-picker").replaceChildren();
  for(const tool of catalog.filter(t=>t.allowed)){
    const binding=agent?.tools.find(b=>b.key===tool.key);
    const row=node("div","","tool-option"); row.dataset.key=tool.key;
    const label=node("label","","check"), check=document.createElement("input");check.type="checkbox";check.checked=!!binding;
    label.append(check,node("span",tool.path));row.append(label,node("small",tool.description));
    const params=Object.entries(tool.schema.properties);
    if(params.length)row.append(node("small",params.map(([k,v])=>k+": "+v.type+(tool.schema.required.includes(k)?" (obrigatório na chamada)":"")).join(" · ")));
    const fixedLabel=node("label","Parâmetros fixos (JSON)"); const fixed=document.createElement("textarea");fixed.rows=1;fixed.value=JSON.stringify(binding?.fixed||{});fixed.className="fixed-params";fixedLabel.append(fixed);row.append(fixedLabel);$("tool-picker").append(row);
  }
  $("editor").scrollIntoView({behavior:"smooth"});$("name").focus();
}
$("agent-form").addEventListener("submit",async event=>{
  event.preventDefault();$("save-agent").disabled=true;
  try{
    const tools=[...$("tool-picker").children].filter(r=>r.querySelector("input").checked).map(r=>({key:r.dataset.key,fixed:JSON.parse(r.querySelector("textarea").value||"{}")}));
    const config={name:$("name").value,prompt:$("prompt").value,task:$("task").value,model:$("model").value,provider:"ollama",interval_seconds:Number($("interval").value),enabled:$("enabled").checked,tools,revision:editing?.revision};
    await api("/api/mvp/agents"+(editing?"/"+editing.id:""),editing?"PUT":"POST",config);
    $("editor").hidden=true;notify("Agente salvo no IRIS.");await refresh();
  }catch(e){notify(e.message,true);}finally{$("save-agent").disabled=false;}
});
async function showRun(id){
  detailId=id;const r=await api("/api/mvp/runs/"+id);$("run-detail").hidden=false;
  const body=$("report-body");body.replaceChildren(node("p",(states[r.state]||r.state)+" · "+r.snapshot.name+" · revisão "+r.snapshot.revision));
  if(r.error)body.append(node("p","Erro: "+r.error,"error"));
  body.append(node("pre",r.report||"Ainda não há relatório."));
  const instructions=document.createElement("details");instructions.append(node("summary","Instruções utilizadas"),node("pre",r.snapshot.prompt+"\n\n"+r.snapshot.task));body.append(instructions);
  for(const call of r.calls){const d=document.createElement("details");d.append(node("summary",call.tool+" · "+call.outcome+" · "+call.id),node("pre",JSON.stringify({arguments:call.arguments,result:call.result},null,2)));body.append(d);}
}
async function refresh(){
  const [a,r]=await Promise.all([api("/api/mvp/agents"),api("/api/mvp/runs")]);agents=a.items;renderAgents();$("run-list").replaceChildren();
  if(!r.items.length){const row=node("tr","");const cell=node("td","Nenhuma execução registrada.");cell.colSpan=4;row.append(cell);$("run-list").append(row);}
  for(const run of r.items){const row=node("tr","");row.append(node("td",run.agent_name),node("td",new Date(run.created_at).toLocaleString("pt-BR")),node("td",states[run.state]||run.state));const cell=node("td","");cell.append(button("Ver relatório",()=>showRun(run.id)));row.append(cell);$("run-list").append(row);}
  if(detailId)await showRun(detailId);
}
$("new-agent").addEventListener("click",()=>openEditor());$("close-editor").addEventListener("click",()=>$("editor").hidden=true);$("close-detail").addEventListener("click",()=>{$("run-detail").hidden=true;detailId=null;});$("refresh").addEventListener("click",()=>refresh().catch(e=>notify(e.message,true)));
async function init(){
  const session=await api("/api/v1/session");token=session.csrf_token;permissions=session.roles;$("new-agent").disabled=!canDesign();
  const data=await api("/api/mvp/catalog");catalog=data.items;$("model").dataset.default=data.default_model;$("catalog-count").textContent=catalog.length;
  for(const t of catalog){const row=node("tr","");row.append(node("td",t.method),node("td",t.path),node("td",t.allowed?"Leitura disponível":"Bloqueada"));$("catalog-list").append(row);}
  await refresh();setInterval(()=>refresh().catch(e=>notify(e.message,true)),5000);
}
init().catch(e=>notify(e.message,true));
