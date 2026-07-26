"use client";

import { useState } from "react";
import { MessageCircle, RotateCcw, Send, X } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { interpretTripCommand } from "@/lib/chatCommands";

interface Message { role: "user" | "assistant"; text: string; changed?: boolean }

export function ChatPanel() {
  const { state, dispatch, undo } = useTrip();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([{ role: "assistant", text: "Ciao. Ask me to change a leg, move a boat day, adjust nights, or explain the budget." }]);
  const submit = (value = input) => {
    if (!value.trim()) return;
    const result = interpretTripCommand(value, state);
    result.actions.forEach(dispatch);
    setMessages((current) => [...current, { role: "user", text: value }, { role: "assistant", text: result.reply, changed: result.actions.length > 0 }]);
    setInput("");
  };
  return (
    <>
      <button onClick={() => setOpen(true)} className="no-print fixed bottom-5 right-5 z-[1800] flex items-center gap-2 rounded-full bg-[var(--ink)] px-5 py-3 text-sm text-[var(--paper)] shadow-2xl" aria-label="Open trip chat"><MessageCircle size={18} />Ask the trip</button>
      {open && <aside className="no-print fixed inset-x-3 bottom-3 top-20 z-[1900] flex flex-col border border-[var(--line)] bg-[var(--paper)] shadow-2xl md:inset-auto md:bottom-5 md:right-5 md:top-auto md:h-[620px] md:w-[410px]" aria-label="Trip assistant">
        <header className="flex items-center justify-between border-b border-[var(--line)] p-4"><div><p className="font-serif text-2xl">Ask the trip</p><p className="text-[10px] uppercase tracking-wider text-[var(--olive)]">Edits this itinerary directly</p></div><Button size="icon" variant="quiet" onClick={() => setOpen(false)}><X size={17} /></Button></header>
        <div className="flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">{messages.map((message, index) => <div key={index} className={message.role === "user" ? "ml-10 rounded-2xl rounded-br-sm bg-[var(--ink)] p-3 text-sm text-[var(--paper)]" : "mr-8 rounded-2xl rounded-bl-sm bg-[var(--surface)] p-3 text-sm leading-6"}>{message.text}{message.changed && <button onClick={undo} className="mt-2 flex items-center gap-1 text-xs underline"><RotateCcw size={12} />Undo this change</button>}</div>)}</div>
        <div className="flex gap-2 overflow-x-auto border-t border-[var(--line)] px-3 pt-3">{["Make Amalfi cheaper", "What is our total?", "Move Capri boat to weather day"].map((suggestion) => <button key={suggestion} onClick={() => submit(suggestion)} className="shrink-0 rounded-full border border-[var(--line)] px-3 py-1.5 text-[10px]">{suggestion}</button>)}</div>
        <form onSubmit={(event) => { event.preventDefault(); submit(); }} className="flex gap-2 p-3"><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Make Tuscany 5 nights…" aria-label="Message the trip assistant" className="min-w-0 flex-1 rounded-full border border-[var(--line)] bg-transparent px-4 py-3 text-sm outline-none focus:border-[var(--olive)]" /><Button size="icon" type="submit" aria-label="Send message"><Send size={16} /></Button></form>
      </aside>}
    </>
  );
}
