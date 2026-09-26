const prefix = window.location.pathname.replace(/\/$/, "");
const $ = id => document.getElementById(id) || (id === "editor" ? document.getElementById("editor-modal") : null);
let token = "", agents = [], catalog = [], editing = null, permissions = [], detailId = null, provider = "ollama", agentsExpanded = true, runsExpanded = true, runs = [], runPage = 1, runSort = "created_at", runDirection = "desc";
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
function canManageTools(){ return permissions.some(r=>["DBAApprover","PlatformAdministrator"].includes(r)); }
function effectiveModel(agent){ return agent.provider===provider?agent.model:$("model").dataset.default||agent.model; }
function parameterEntries(schema,prefix=""){
  return Object.entries(schema.properties||{}).flatMap(([name,property])=>{
    const key=prefix?`${prefix}.${name}`:name;
    return [{key,property,required:(schema.required||[]).includes(name)},...parameterEntries(property,key)];
  });
}
function updateToolPicker(){
  const rows=[...$("tool-picker").children],query=$("tool-search").value.trim().toLowerCase();let visible=0,selected=0;
  const available=rows.filter(row=>row.dataset.available==="true").length;
  for(const row of rows){const match=!query||row.dataset.search.includes(query);row.hidden=!match;if(match&&row.dataset.available==="true")visible++;if(row.dataset.available==="true"&&row.querySelector('input[type="checkbox"]').checked)selected++;}
  $("tool-result-count").textContent=query?`${visible} of ${available} available tools`:`${available} available tools`;
  $("tool-selection-count").textContent=`${selected} of 12 selected`;
  $("tool-selection-count").classList.toggle("at-limit",selected===12);
  if(!rows.length)$("tool-empty").textContent="No tools are available. Ask a DBA to enable operations in the catalog.";
  else $("tool-empty").textContent="No available tools match this search.";
  $("tool-empty").hidden=visible>0;
}
function renderToolPicker(agent=null,preserveCurrent=false){
  const previous=new Map(preserveCurrent?[...$("tool-picker").children].map(row=>[row.dataset.key,{selected:row.querySelector('input[type="checkbox"]').checked,fixed:row.querySelector("textarea")?.value}]):[]);
  const boundKeys=new Set((agent?.tools||[]).map(binding=>binding.key));
  $("tool-picker").replaceChildren();
  for(const tool of catalog.filter(item=>item.allowed||boundKeys.has(item.key))){
    const binding=agent?.tools.find(item=>item.key===tool.key),params=parameterEntries(tool.schema);
    const row=node("article","","tool-option");row.dataset.key=tool.key;row.dataset.available=String(tool.allowed);row.dataset.search=`${tool.method} ${tool.path} ${tool.description||""} ${params.map(item=>`${item.key} ${item.property.description||""}`).join(" ")}`.toLowerCase();
    const main=node("div","","tool-main"),heading=node("div","","tool-option-heading");
    const label=node("label","","tool-select"),check=document.createElement("input");check.type="checkbox";check.checked=tool.allowed&&(previous.get(tool.key)?.selected??!!binding);check.disabled=!tool.allowed;
    label.append(check,node("span",tool.path,"tool-path"));heading.append(label,node("span",tool.method,`method-badge ${tool.method.toLowerCase()}`));
    if(!tool.allowed)heading.append(node("span","Blocked by DBA","tool-blocked-badge"));
    main.append(heading,node("p",tool.description||"No summary is available in the source specification.","tool-description"));
    if(params.length){
      const parameterList=node("div","","tool-parameters");
      for(const {key,property,required} of params){
        const parameter=node("div","","tool-parameter"),details=node("div","","tool-parameter-details");
        details.append(node("div",key,"tool-parameter-name"),node("small",property.description||"No parameter description is available.","tool-parameter-description"));
        parameter.append(details,node("span",`${property.type||"value"} · ${required?"required unless fixed":"optional"}`,required?"parameter-type required":"parameter-type"));parameterList.append(parameter);
      }
      main.append(parameterList);
    }else main.append(node("small","This operation has no configurable parameters.","tool-parameter-description"));
    const fixedField=node("div","","tool-fixed-field");
    if(params.length){
      const fixedLabel=node("label","Fixed parameters (optional JSON)","tool-fixed-label"),fixed=document.createElement("textarea");fixed.rows=2;fixed.value=previous.get(tool.key)?.fixed??JSON.stringify(binding?.fixed||{});fixed.placeholder="{}";fixed.setAttribute("aria-label",`Fixed parameters for ${tool.path}`);fixed.className="fixed-params";fixedLabel.append(fixed);fixedField.append(fixedLabel,node("small",'Leave as {} for no fixed values. The agent cannot change pinned values; conflicting requests are rejected. Example: {"maxRows":100} when maxRows is listed above.'));
    }
    row.append(main,fixedField);$("tool-picker").append(row);
  }
  updateToolPicker();
}
function renderCatalog(){
  $("catalog-list").replaceChildren();
  $("catalog-count").textContent=catalog.length;
  $("catalog-available-count").textContent=`${catalog.filter(tool=>tool.available).length} enabled`;
  $("reviewed-read-count").textContent=catalog.filter(tool=>tool.default_read_only).length;
  for(const tool of catalog){
    const row=node("tr","");row.dataset.search=`${tool.method} ${tool.path} ${tool.description||""}`.toLowerCase();
    row.append(node("td",tool.method),node("td",tool.path),node("td",tool.description||"No description in source contract."),node("td",!tool.supported?"Unsupported":tool.available?"Enabled":"Blocked",!tool.supported?"unknown":tool.available?"availability-on":"availability-off"));
    const control=node("td","");
    if(!canManageTools())control.append(node("span","DBA role required","catalog-access-note"));
    else if(!tool.supported)control.append(node("span","Unsupported request shape","catalog-access-note"));
    else{
      const label=node("label","","availability-toggle"),checkbox=document.createElement("input");checkbox.type="checkbox";checkbox.checked=tool.available;checkbox.setAttribute("aria-label",`${tool.available?"Block":"Enable"} ${tool.method} ${tool.path}`);checkbox.addEventListener("change",()=>setToolAvailability(tool,checkbox));
      label.append(checkbox,node("span",tool.available?"Enabled":"Blocked"));control.append(label);
    }
    row.append(control);$("catalog-list").append(row);
  }
  filterCatalog();
}
function filterCatalog(){
  const query=$("catalog-search").value.trim().toLowerCase();
  for(const row of $("catalog-list").children)row.hidden=!!query&&!row.dataset.search.includes(query);
}
async function loadCatalog(){
  const data=await api("/api/mvp/catalog");catalog=data.items;provider=data.provider;$("model").dataset.default=data.default_model;$("provider-note").textContent=`Provider: ${provider==="openai"?"OpenAI":"Ollama"}`;renderCatalog();
  if(!$("editor").hidden)renderToolPicker(editing,true);
}
async function setToolAvailability(tool,checkbox){
  const enabled=checkbox.checked,mutating=["POST","PUT","PATCH","DELETE"].includes(tool.method);
  const warnings=[`${enabled?"Enable":"Block"} ${tool.method} ${tool.path}?`];
  if(enabled)warnings.push("Any assigned agent can invoke an available tool automatically, including scheduled runs.");
  if(mutating)warnings.push(enabled?"This operation may change IRIS state. There is no approval prompt for each run.":"Agents with this assigned tool may fail if they run before you remove it from their configuration.");
  if(["GET","HEAD"].includes(tool.method)&&enabled)warnings.push(`${tool.method} is an HTTP method, not proof that an operation has no side effects.`);
  if(tool.sensitive&&enabled)warnings.push("The schema includes password-, token-, or credential-like fields. Matching sensitive keys are redacted from stored evidence, but values are sent to the model and target.");
  if(!window.confirm(warnings.join("\n\n"))){checkbox.checked=!enabled;return;}
  try{
    await api(`/api/mvp/catalog/${tool.stable_key}/availability`,"PUT",{enabled,acknowledge_auto_execution:mutating,acknowledge_sensitive_data:tool.sensitive,reason:`${enabled?"Enabled":"Blocked"} by DBA in the tool catalog.`});
    await loadCatalog();notify(`${tool.method} ${tool.path} ${enabled?"enabled":"blocked"}.`);
  }catch(error){checkbox.checked=!enabled;notify(error.message,true);}
}
async function applyToolPreset(preset){
  const enableReviewedReads=preset==="reviewed-reads";
  const prompt=enableReviewedReads
    ? `Enable the ${catalog.filter(tool=>tool.default_read_only).length} reviewed read-only operations? They will be available to assigned agents, including scheduled runs.`
    : `Block all ${catalog.length} operations? Agents currently assigned blocked operations will not be able to call them.`;
  if(!window.confirm(prompt))return;
  try{
    const result=await api(`/api/mvp/catalog/presets/${preset}`,"PUT",{});
    await loadCatalog();
    notify(`${result.changed} operations ${enableReviewedReads?"enabled":"blocked"}.`);
  }catch(error){notify(error.message,true);}
}
function renderAgents(){
  $("agent-count").textContent=agents.length;
  $("agent-list").replaceChildren();
  if(!agents.length) $("agent-list").append(node("p","No agents registered. Create your first agent with custom instructions and tools."));
  for(const a of agents){
    const card=node("article", "", "agent-card");
    const top=node("div","","agent-card-top"), title=node("div","","agent-title");
    title.append(node("span",a.enabled?"●":"●",a.enabled?"agent-status active":"agent-status paused"),node("h4",a.name));
    top.append(title,node("span",a.enabled?"Enabled":"Paused",a.enabled?"status-label enabled":"status-label paused"));
    card.append(top,node("p",a.task),node("small",(a.interval_seconds?"⏱ Every "+a.interval_seconds+"s":"⏱ Manual")+"  ·  ◈ "+a.tools.length+" tools  ·  ◉ "+effectiveModel(a)));
    const actions=node("div","","actions");
    actions.append(button("✎  Edit",()=>openEditor(a),!canDesign()),button(a.active_run?"◷  Run pending":"▶  Run now",async()=>{await api("/api/mvp/agents/"+a.id+"/runs","POST",{});notify("Run added to the queue.");await refresh();},!canRun()||!a.enabled||!!a.active_run),button(a.enabled?"Ⅱ  Pause":"▶  Enable",async()=>{await api("/api/mvp/agents/"+a.id,"PUT",{...a,enabled:!a.enabled});notify("Configuration updated. Runs already in progress may finish.");await refresh();},!canDesign()));
    card.append(actions);$("agent-list").append(card);
  }
}
function openEditor(agent=null){
  editing=agent;$("editor-modal").hidden=false;document.body.classList.add("modal-open");$("editor-title").textContent=agent?"Edit agent":"Create agent";
  for(const field of ["name","prompt","task"])$(field).value=agent?.[field]||"";
  $("model").value=agent?effectiveModel(agent):$("model").dataset.default||"qwen2.5:3b";
  $("interval").value=agent?.interval_seconds||0;$("enabled").checked=agent?.enabled??true;
  $("tool-search").value="";renderToolPicker(agent);
  $("editor").scrollIntoView({behavior:"smooth"});$("name").focus();
}
$("tool-search").addEventListener("input",updateToolPicker);
$("catalog-search").addEventListener("input",filterCatalog);
$("enable-reviewed-reads").addEventListener("click",()=>applyToolPreset("reviewed-reads"));
$("block-all-tools").addEventListener("click",()=>applyToolPreset("block-all"));
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
    const config={name:$("name").value,prompt:$("prompt").value,task:$("task").value,model:$("model").value,provider,interval_seconds:Number($("interval").value),enabled:$("enabled").checked,tools,revision:editing?.revision};
    await api("/api/mvp/agents"+(editing?"/"+editing.id:""),editing?"PUT":"POST",config);
    $("editor").hidden=true;notify("Agent saved to IRIS.");await refresh();
  }catch(e){notify(e.message,true);}finally{$("save-agent").disabled=false;}
});
async function showRun(id){
  detailId=id;const r=await api("/api/mvp/runs/"+id);$("report-modal").hidden=false;document.body.classList.add("modal-open");
  const body=$("report-body");body.replaceChildren(node("p",(states[r.state]||r.state)+" · "+r.snapshot.name+" · revision "+r.snapshot.revision));
  if(r.error)body.append(node("p","Error: "+r.error,"error"));
  body.append(node("pre",r.report||"No report available yet."));
  const instructions=document.createElement("details");instructions.append(node("summary","Instructions used"),node("pre",r.snapshot.prompt+"\n\n"+r.snapshot.task));body.append(instructions);
  for(const call of r.calls){const d=document.createElement("details");d.append(node("summary",call.tool+" · "+call.outcome+" · "+call.id),node("pre",JSON.stringify({arguments:call.arguments,result:call.result},null,2)));body.append(d);}
}
function renderRuns(){
  const sorted=[...runs].sort((a,b)=>{let av=a[runSort]||"",bv=b[runSort]||"";if(runSort==="created_at"){av=new Date(av).getTime();bv=new Date(bv).getTime();}else{av=String(av).toLowerCase();bv=String(bv).toLowerCase();}return (av>bv?1:av<bv?-1:0)*(runDirection==="asc"?1:-1);});
  const totalPages=Math.max(1,Math.ceil(sorted.length/10));runPage=Math.min(runPage,totalPages);
  const page=sorted.slice((runPage-1)*10,runPage*10);$("run-list").replaceChildren();
  if(!page.length){const row=node("tr","");const cell=node("td","No runs recorded.");cell.colSpan=4;row.append(cell);$("run-list").append(row);}
  for(const run of page){const row=node("tr","");const status=String(run.state).toLowerCase();const statusIcons={succeeded:"✓",partial:"⚠",failed:"✕"};const statusCell=node("td","","run-status "+status);if(statusIcons[status])statusCell.append(node("span",statusIcons[status],"status-icon"),document.createTextNode(" "));statusCell.append(document.createTextNode(states[run.state]||run.state));row.append(node("td",run.agent_name),node("td",new Date(run.created_at).toLocaleString("en-US")),statusCell,node("td",""));row.lastChild.append(button("View report",()=>showRun(run.id)));$("run-list").append(row);}
  const pagination=$("run-pagination");pagination.replaceChildren();if(totalPages>1){pagination.append(button("‹ Previous",()=>{runPage--;renderRuns();},runPage===1),node("span",`Page ${runPage} of ${totalPages}`),button("Next ›",()=>{runPage++;renderRuns();},runPage===totalPages));}
  document.querySelectorAll(".sort-button").forEach(btn=>{btn.classList.toggle("active",btn.dataset.sort===runSort);btn.querySelector("span").textContent=btn.dataset.sort===runSort?(runDirection==="asc"?"↑":"↓"):"↕";});
}
async function refresh(options={}){
  if(options.background&&(!$('editor-modal').hidden||detailId))return;
  const [a,r]=await Promise.all([api("/api/mvp/agents"),api("/api/mvp/runs")]);agents=a.items;runs=r.items;renderAgents();renderRuns();
  if(detailId&&!options.background)await showRun(detailId);
}
$("new-agent").addEventListener("click",()=>openEditor());$("close-editor").addEventListener("click",()=>$("editor").hidden=true);$("refresh").addEventListener("click",()=>refresh().catch(e=>notify(e.message,true)));
function closeEditor(){ $("editor-modal").hidden=true; document.body.classList.remove("modal-open"); }
$("close-editor").addEventListener("click",closeEditor);
$("editor-modal").addEventListener("click",event=>{if(event.target===$("editor-modal"))closeEditor();});
function closeReport(){ $("report-modal").hidden=true; detailId=null; document.body.classList.remove("modal-open"); }
$("close-detail").addEventListener("click",closeReport);
$("report-modal").addEventListener("click",event=>{if(event.target===$("report-modal"))closeReport();});
document.addEventListener("keydown",event=>{if(event.key==="Escape"&&!$("report-modal").hidden)closeReport();});
$("toggle-agents").addEventListener("click",()=>{agentsExpanded=!agentsExpanded;$("agent-list").hidden=!agentsExpanded;$("toggle-agents").setAttribute("aria-expanded",String(agentsExpanded));$("toggle-agents").innerHTML=agentsExpanded?"<span aria-hidden=\"true\">⌃</span> Collapse":"<span aria-hidden=\"true\">⌄</span> Expand";});
$("toggle-runs").addEventListener("click",()=>{runsExpanded=!runsExpanded;$("runs-content").hidden=!runsExpanded;$("toggle-runs").setAttribute("aria-expanded",String(runsExpanded));$("toggle-runs").innerHTML=runsExpanded?"<span aria-hidden=\"true\">⌃</span> Collapse":"<span aria-hidden=\"true\">⌄</span> Expand";});
document.querySelectorAll(".sort-button").forEach(btn=>btn.addEventListener("click",()=>{if(runSort===btn.dataset.sort)runDirection=runDirection==="asc"?"desc":"asc";else{runSort=btn.dataset.sort;runDirection="asc";}runPage=1;renderRuns();}));
async function init(){
  const session=await api("/api/v1/session");token=session.csrf_token;permissions=session.roles;$("new-agent").disabled=!canDesign();$("catalog-presets").hidden=!canManageTools();
  await loadCatalog();
  await refresh();
  setInterval(()=>refresh({background:true}).catch(e=>notify(e.message,true)),15000);
}
init().catch(e=>notify(e.message,true));
