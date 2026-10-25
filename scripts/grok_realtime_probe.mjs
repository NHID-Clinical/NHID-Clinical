#!/usr/bin/env node
// Observe a console-published Grok agent from the payer representative's seat.
//
// This is the console's own WebSocket example, extended: it connects to the
// agent, plays the PAYER REPRESENTATIVE (the party who RECEIVES the call in the
// canonical scenario), and prints what the agent says and every tool call it
// makes. It changes nothing and enforces nothing; it exists so a person can
// watch whether the published agent discloses before it asks for data, and
// whether it calls the NHID gate tool first. The enforcing component is
// src/grok_realtime_bridge.py.
//
//   npm install ws
//   XAI_API_KEY=... node scripts/grok_realtime_probe.mjs agent_J8dltSjOm783cTrx \
//       "Claims department, this is Dana. How can I help you?" \
//       "Sure, which member?"
//
// The key is read from the environment and never printed. No audio is played;
// binary frames are dropped. Transcript lines are printed to stdout only.
import WebSocket from 'ws';

const [agentId, ...lines] = process.argv.slice(2);
if (!agentId || !process.env.XAI_API_KEY) {
  console.error('usage: XAI_API_KEY=... node scripts/grok_realtime_probe.mjs <agent_id> "<rep line>" ["<rep line>" ...]');
  process.exit(2);
}
const repLines = lines.length ? lines : ['Claims department, this is Dana. How can I help you?'];

const ws = new WebSocket(`wss://api.x.ai/v1/realtime?agent_id=${encodeURIComponent(agentId)}`, {
  headers: { Authorization: `Bearer ${process.env.XAI_API_KEY}` },
});

let turn = 0;
function say(text) {
  console.log(`\n[rep]   ${text}`);
  ws.send(JSON.stringify({
    type: 'conversation.item.create',
    item: { type: 'message', role: 'user', content: [{ type: 'input_text', text }] },
  }));
  ws.send(JSON.stringify({ type: 'response.create' }));
}

ws.on('open', () => { console.log(`connected to ${agentId}`); say(repLines[turn++]); });

let agentLine = '';
ws.on('message', (raw, isBinary) => {
  if (isBinary) return;
  let event; try { event = JSON.parse(raw.toString()); } catch { return; }
  switch (event.type) {
    case 'response.output_audio_transcript.delta':
      agentLine += event.delta || ''; break;
    case 'response.output_audio_transcript.done':
      console.log(`[agent] ${agentLine || event.transcript || ''}`); agentLine = ''; break;
    case 'response.function_call_arguments.done':
      console.log(`[tool]  ${event.name}(${event.arguments})  call_id=${event.call_id}`);
      // A probe does not run tools and does not answer for the gate. It tells
      // the model the call was observed and not executed, so the transcript
      // shows what the agent does when a tool does not answer.
      ws.send(JSON.stringify({ type: 'conversation.item.create', item: {
        type: 'function_call_output', call_id: event.call_id,
        output: JSON.stringify({ status: 'not_executed', note: 'probe only; see src/grok_realtime_bridge.py' }) } }));
      ws.send(JSON.stringify({ type: 'response.create' }));
      break;
    case 'response.done':
      if (turn < repLines.length) setTimeout(() => say(repLines[turn++]), 400);
      else setTimeout(() => { console.log('\nprobe done'); ws.close(); }, 800);
      break;
    case 'error':
      console.error('[error]', JSON.stringify(event.error || event)); break;
    default: break;
  }
});
ws.on('close', () => process.exit(0));
ws.on('error', (e) => { console.error('socket error:', e.message); process.exit(1); });
