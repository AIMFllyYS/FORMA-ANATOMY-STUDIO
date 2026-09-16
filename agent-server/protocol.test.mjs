import test from 'node:test';
import assert from 'node:assert/strict';
import {toModelMessages,toChatCompletion,toSseCompletion} from './protocol.mjs';
test('preserves real tool results and links tool names',()=>{
 const input=[{role:'system',content:'Study only.'},{role:'user',content:'Locate humerus.'},{role:'assistant',content:null,tool_calls:[{id:'c1',function:{name:'search_structures',arguments:'{"query":"humerus"}'}}]},{role:'tool',tool_call_id:'c1',content:'{"matches":[{"id":2}]}'}];
 const out=toModelMessages(input);assert.equal(out[2].content[0].type,'tool-call');assert.deepEqual(out[3].content[0].output,{type:'json',value:{matches:[{id:2}]}});
});
test('rejects orphan results and arbitrary tools',()=>{
 assert.throws(()=>toModelMessages([{role:'tool',tool_call_id:'x',content:'ok'}]));
 assert.throws(()=>toModelMessages([{role:'assistant',tool_calls:[{id:'x',function:{name:'eval',arguments:'{}'}}]}]));
});
test('normalizes result to OpenAI-compatible choices',()=>{
 const out=toChatCompletion({text:'',toolCalls:[{toolCallId:'f1',toolName:'focus_structures',input:{ids:[2]}}]},'test');
 assert.equal(out.choices[0].message.tool_calls[0].function.arguments,'{"ids":[2]}');assert.equal(out.choices[0].finish_reason,'tool_calls');
});
test('sse payload includes reasoning and done marker',()=>{
 const raw=toSseCompletion({text:'**肱骨**',reasoning:'先定位',toolCalls:[]},'test');
 assert.match(raw,/reasoning_content/);assert.match(raw,/肱骨/);assert.match(raw,/\[DONE\]/);
});
test('refuses unsupported multimodal uploads',()=>{assert.throws(()=>toModelMessages([{role:'user',content:[{type:'image',image:'private'}]}]));});
