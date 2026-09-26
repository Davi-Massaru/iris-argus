const prefix = window.location.pathname.replace(/\/$/, "");
const $ = id => document.getElementById(id);
let token = "", agents = [], catalog = [], editing = null, permissions = [], detailId = null;
const states = {QUEUED:"Queued",RUNNING:"Running",SUCCEEDED:"Succeeded",PARTIAL:"Partial",FAILED:"Failed",CANCELLED:"Cancelled"};
function notify(message, error=false) { $("notice").textContent=message; $("notice").className=error?"error":""; }
async function api(path, method="GET", data) {
  const response=await fetch(prefix+path,{method,credentials:"same-origin",headers:{"Content-Type":"application/json","X-Agentic-CSRF":token},body:data===undefined?undefined:JSON.stringify(data)});
  const body=await response.json();
  if(!response.ok) throw new Error(body.error?.message || "HTTP error "+response.status);
  return body;
}
function node(tag, text, cls) { const n=document.createElement(tag); n.textContent=text; if(cls)n.className=cls; return n; }
function button(label, action, disabled=false) { const b=node("button",label,"secondary"); b.type="button"; b.disabled=disabled; b.addEventListener("click",()=>Promise.resolve().then(action).catch(e=>notify(e.message,true))); return b; }
function canDesign(){ return permissions.some(r=>["AgentDesigner","PlatformAdministrator"].includes(r)); }
function canRun(){ return permissions.some(r=>["Operator","AgentDesigner","PlatformAdministrator"].includes(r)); }
function updateToolPicker(){
  const rows=[...$("tool-picker").children],query=$("tool-search").value.trim().toLowerCase();let visible=0,selected=0;
  for(const row of rows){const match=!query||row.dataset.search.includes(query);row.hidden=!match;if(match)visible++;if(row.querySelector('input[type="checkbox"]').checked)selected++;}
  $("tool-result-count").textContent=query?`${visible} of ${rows.length} approved queries`:`${rows.length} approved queries`;
  $("tool-selection-count").textContent=`${selected} of 12 selected`;
  $("tool-selection-count").classList.toggle("at-limit",selected===12);
  $("tool-empty").hidden=visible>0;
}
function renderAgents(){
  $("agent-count").textContent=agents.length;
  $("agent-list").replaceChildren();
  if(!agents.length) $("agent-list").append(node("p","No agents registered. Create your first agent with custom instructions and tools."));
  for(const a of agents){
    const card=node("article", "", "agent-card"); card.append(node("h4",a.name),node("p",a.task),node("small",(a.enabled?"Enabled":"Paused")+" · "+(a.interval_seconds?"Every "+a.interval_seconds+"s":"Manual")+" · "+a.tools.length+" tools · "+a.model));
    const actions=node("div","","actions");
    actions.append(button("Edit",()=>openEditor(a),!canDesign()),button(a.active_run?"Run pending":"Run now",async()=>{await api("/api/mvp/agents/"+a.id+"/runs","POST",{});notify("Run added to the queue.");await refresh();},!canRun()||!a.enabled||!!a.active_run),button(a.enabled?"Pause":"Enable",async()=>{await api("/api/mvp/agents/"+a.id,"PUT",{...a,enabled:!a.enabled});notify("Configuration updated. Runs already in progress may finish.");await refresh();},!canDesign()));
    card.append(actions);$("agent-list").append(card);
  }
}
function openEditor(agent=null){
  editing=agent;$("editor").hidden=false;$("editor-title").textContent=agent?"Edit agent":"Create agent";
  for(const field of ["name","prompt","task"])$(field).value=agent?.[field]||"";
  $("model").value=agent?.model||$("model").dataset.default||"qwen2.5:3b";
  $("interval").value=agent?.interval_seconds||0;$("enabled").checked=agent?.enabled??true;
  $("tool-picker").replaceChildren();$("tool-search").value="";
  for(const tool of catalog.filter(t=>t.allowed)){
    const binding=agent?.tools.find(b=>b.key===tool.key);
    const params=Object.entries(tool.schema.properties);
    const row=node("article","","tool-option");row.dataset.key=tool.key;row.dataset.search=`${tool.method} ${tool.path} ${tool.description||""} ${params.map(([key,value])=>`${key} ${value.description||""}`).join(" ")}`.toLowerCase();
    const main=node("div","","tool-main"),heading=node("div","","tool-option-heading");
    const label=node("label","","tool-select"),check=document.createElement("input");check.type="checkbox";check.checked=!!binding;
    label.append(check,node("span",tool.path,"tool-path"));heading.append(label,node("span",tool.method,"method-badge get"));
    main.append(heading,node("p",tool.description||"No summary is available in the source specification.","tool-description"));
    if(params.length){
      const parameterList=node("div","","tool-parameters");
      for(const [key,value] of params){
        const parameter=node("div","","tool-parameter"),details=node("div","","tool-parameter-details");
        details.append(node("div",key,"tool-parameter-name"),node("small",value.description||"No parameter description is available.","tool-parameter-description"));
        parameter.append(details,node("span",`${value.type||"value"} · ${tool.schema.required.includes(key)?"required unless fixed":"optional"}`,tool.schema.required.includes(key)?"parameter-type required":"parameter-type"));parameterList.append(parameter);
      }
      main.append(parameterList);
    }else main.append(node("small","This query has no configurable parameters.","tool-parameter-description"));
    const fixedField=node("div","","tool-fixed-field");
    if(params.length){
      const fixedLabel=node("label","Fixed parameters (optional JSON)","tool-fixed-label"),fixed=document.createElement("textarea");fixed.rows=2;fixed.value=JSON.stringify(binding?.fixed||{});fixed.placeholder="{}";fixed.setAttribute("aria-label",`Fixed parameters for ${tool.path}`);fixed.className="fixed-params";fixedLabel.append(fixed);fixedField.append(fixedLabel,node("small",'Leave as {} for no fixed values. The agent cannot change pinned values; conflicting requests are rejected. Example: {"maxRows":100} when maxRows is listed above.'));
    }
    row.append(main,fixedField);$("tool-picker").append(row);
  }
  updateToolPicker();
  $("editor").scrollIntoView({behavior:"smooth"});$("name").focus();
}
$("tool-search").addEventListener("input",updateToolPicker);
$("tool-picker").addEventListener("change",event=>{
  if(!event.target.matches('input[type="checkbox"]'))return;
  const selected=$("tool-picker").querySelectorAll('input[type="checkbox"]:checked').length;
  if(event.target.checked&&selected>12){event.target.checked=false;notify("Select up to 12 approved queries.",true);}
  updateToolPicker();
});
$("agent-form").addEventListener("submit",async event=>{
  event.preventDefault();$("save-agent").disabled=true;
  try{
    const tools=[...$("tool-picker").children].filter(r=>r.querySelector('input[type="checkbox"]').checked).map(r=>({key:r.dataset.key,fixed:JSON.parse(r.querySelector("textarea")?.value||"{}")}));
    if(tools.length<1||tools.length>12)throw new Error("Select between 1 and 12 approved queries.");
    const config={name:$("name").value,prompt:$("prompt").value,task:$("task").value,model:$("model").value,provider:"ollama",interval_seconds:Number($("interval").value),enabled:$("enabled").checked,tools,revision:editing?.revision};
    await api("/api/mvp/agents"+(editing?"/"+editing.id:""),editing?"PUT":"POST",config);
    $("editor").hidden=true;notify("Agent saved to IRIS.");await refresh();
  }catch(e){notify(e.message,true);}finally{$("save-agent").disabled=false;}
});
async function showRun(id){
  detailId=id;const r=await api("/api/mvp/runs/"+id);$("run-detail").hidden=false;
  const body=$("report-body");body.replaceChildren(node("p",(states[r.state]||r.state)+" · "+r.snapshot.name+" · revision "+r.snapshot.revision));
  if(r.error)body.append(node("p","Error: "+r.error,"error"));
  body.append(node("pre",r.report||"No report available yet."));
  const instructions=document.createElement("details");instructions.append(node("summary","Instructions used"),node("pre",r.snapshot.prompt+"\n\n"+r.snapshot.task));body.append(instructions);
  for(const call of r.calls){const d=document.createElement("details");d.append(node("summary",call.tool+" · "+call.outcome+" · "+call.id),node("pre",JSON.stringify({arguments:call.arguments,result:call.result},null,2)));body.append(d);}
}
async function refresh(){
  const [a,r]=await Promise.all([api("/api/mvp/agents"),api("/api/mvp/runs")]);agents=a.items;renderAgents();$("run-list").replaceChildren();
  if(!r.items.length){const row=node("tr","");const cell=node("td","No runs recorded.");cell.colSpan=4;row.append(cell);$("run-list").append(row);}
  for(const run of r.items){const row=node("tr","");row.append(node("td",run.agent_name),node("td",new Date(run.created_at).toLocaleString("en-US")),node("td",states[run.state]||run.state));const cell=node("td","");cell.append(button("View report",()=>showRun(run.id)));row.append(cell);$("run-list").append(row);}
  if(detailId)await showRun(detailId);
}
$("new-agent").addEventListener("click",()=>openEditor());$("close-editor").addEventListener("click",()=>$("editor").hidden=true);$("close-detail").addEventListener("click",()=>{$("run-detail").hidden=true;detailId=null;});$("refresh").addEventListener("click",()=>refresh().catch(e=>notify(e.message,true)));
async function init(){
  const session=await api("/api/v1/session");token=session.csrf_token;permissions=session.roles;$("new-agent").disabled=!canDesign();
  const data=await api("/api/mvp/catalog");catalog=data.items;$("model").dataset.default=data.default_model;$("catalog-count").textContent=catalog.length;
  for(const t of catalog){const row=node("tr","");row.append(node("td",t.method),node("td",t.path),node("td",t.allowed?"Read available":"Blocked"));$("catalog-list").append(row);}
  await refresh();setInterval(()=>refresh().catch(e=>notify(e.message,true)),5000);
}
init().catch(e=>notify(e.message,true));
