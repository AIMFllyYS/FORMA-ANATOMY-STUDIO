/* Wire conversion with no SDK dependency; testable independently. MIT. */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import {createRequire} from 'node:module';
import Ajv from 'ajv';
const HERE=dirname(fileURLToPath(import.meta.url));
const require=createRequire(import.meta.url);
// 浏览器端默认限额是工具调用数的单一事实源（纯 CJS/UMD 模块，可被 require）。
const {LIMIT_SPECS}=require('../web/agent-config.js');
const manifest=JSON.parse(readFileSync(resolve(HERE,'../web/agent-tools.json'),'utf8'));
export const MAX_MESSAGES = 120;
// 服务端只接受当前清单中的工具；浏览器循环的默认单轮上限来自共享配置。
export const MAX_TOOL_CALLS = LIMIT_SPECS.maxToolCallsPerTurn.def;
export const ALLOWED_NAMES = new Set(manifest.tools.map(t=>t.name));
const ajv=new Ajv({allErrors:true,strict:false});
const validators=new Map();
for(const t of manifest.tools){
 validators.set(t.name,ajv.compile(t.parameters));
}
export function validateToolInput(name,input){
 if(!ALLOWED_NAMES.has(name))throw new Error('Unknown tool: '+name);
 const v=validators.get(name);
 if(!v(input))throw new Error('Invalid tool input for '+name+': '+v.errors.map(e=>e.instancePath+' '+e.message).join('; '));
 return true;
}
export function toModelMessages(messages) {
  if (!Array.isArray(messages) || !messages.length || messages.length > MAX_MESSAGES) throw new Error('Invalid message count');
  const out = [], callNames = new Map();
  for (const m of messages) {
    if (!m || typeof m !== 'object') throw new Error('Invalid message');
    // 安全边界：浏览器永远不能提供 system 角色；系统指令只来自服务端 ToolLoopAgent instructions。
    if (m.role==='system') continue;
    if (m.role==='user') {
      if (typeof m.content !== 'string' || m.content.length > 100000) throw new Error('Only bounded text messages are supported');
      out.push({role:'user',content:m.content});
    } else if (m.role === 'assistant') {
      const content = [];
      if (typeof m.content === 'string' && m.content) content.push({type:'text',text:m.content});
      if (m.tool_calls) {
        if (!Array.isArray(m.tool_calls) || m.tool_calls.length > MAX_TOOL_CALLS) throw new Error('Too many tool calls');
        for (const c of m.tool_calls) {
          if (!c.id || !ALLOWED_NAMES.has(c.function?.name)) throw new Error('Unknown tool');
          let input;
          try {input = JSON.parse(c.function.arguments || '{}');}
          catch {throw new Error('Tool arguments are not valid JSON');}
          validateToolInput(c.function.name,input);
          callNames.set(c.id,c.function.name);
          content.push({type:'tool-call',toolCallId:c.id,toolName:c.function.name,input});
        }
      }
      if (content.length) out.push({role:'assistant',content});
    } else if (m.role === 'tool') {
      const name = callNames.get(m.tool_call_id);
      if (!name) throw new Error('Tool result has no matching call');
      let value;try {value = JSON.parse(m.content);} catch {value = {text:String(m.content).slice(0,100000)};}
      out.push({role:'tool',content:[{type:'tool-result',toolCallId:m.tool_call_id,toolName:name,output:{type:'json',value}}]});
    } else throw new Error('Unsupported message role');
  }
  return out;
}
export function toChatCompletion(result, model) {
  const calls=(result.toolCalls||[]).filter(c=>ALLOWED_NAMES.has(c.toolName)).map(c=>({id:c.toolCallId,type:'function',function:{name:c.toolName,arguments:JSON.stringify(c.input||{})}}));
  const reasoning=result.reasoningText||result.reasoning||'';
  return {id:'forma-'+Date.now().toString(36),object:'chat.completion',model,choices:[{index:0,message:{role:'assistant',content:result.text||null,...(reasoning?{reasoning_content:String(reasoning)}:{}),...(calls.length?{tool_calls:calls}:{})},finish_reason:calls.length?'tool_calls':'stop'}],usage:{prompt_tokens:result.totalUsage?.inputTokens||0,completion_tokens:result.totalUsage?.outputTokens||0}};
}
export function toSseCompletion(result, model) {
  const payload=toChatCompletion(result,model);
  const msg=payload.choices[0].message;
  const sse=obj=>'data: '+JSON.stringify(obj)+'\n\n';
  let out='';
  if(msg.reasoning_content)out+=sse({choices:[{index:0,delta:{reasoning_content:msg.reasoning_content}}]});
  if(msg.content)out+=sse({choices:[{index:0,delta:{role:'assistant',content:msg.content}}]});
  if(msg.tool_calls?.length)out+=sse({choices:[{index:0,delta:{tool_calls:msg.tool_calls.map((c,i)=>({index:i,id:c.id,type:c.type,function:c.function}))}}]});
  out+=sse({choices:[{index:0,delta:{},finish_reason:payload.choices[0].finish_reason}]});
  return out+'data: [DONE]\n\n';
}
