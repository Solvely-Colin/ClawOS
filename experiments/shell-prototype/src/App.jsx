import { useEffect, useMemo, useRef, useState } from "react";
import { ArchiveIcon, ArrowLeftIcon, BellIcon, ChatBubbleIcon, CheckCircledIcon, ChevronDownIcon, ClockIcon, Cross2Icon, DotsHorizontalIcon, EnvelopeClosedIcon, FileTextIcon, GearIcon, MagnifyingGlassIcon, PaperPlaneIcon, PlusIcon, ReloadIcon, RocketIcon, SpeakerLoudIcon, TrashIcon } from "@radix-ui/react-icons";

const messages = [
  { sender: "Alex Anderson", subject: "Project Orion · Design Review Follow-up", preview: "Thanks again for leading the design review yesterday. The feedback from the team was incredibly valuable.", time: "10:42 AM", unread: true },
  { sender: "Notion", subject: "Your workspace digest", preview: "Weekly digest for Acme Labs — 5 pages updated.", time: "10:21 AM", unread: true },
  { sender: "Alan Cook", subject: "Design review feedback", preview: "Hey Hannah, thanks for the mockups! A few thoughts…", time: "9:08 AM", unread: true },
  { sender: "Sarah Johnson", subject: "Q3 planning", preview: "Let’s sync next week to align on priorities.", time: "8:47 AM", unread: true },
  { sender: "GitHub", subject: "Pull request review", preview: "acme/web-app#1287 was reviewed.", time: "7:15 AM" },
  { sender: "Stripe", subject: "Your invoice is available", preview: "Invoice #9F2A1 for $1,250.00 is ready to view.", time: "Aug 26" },
];

function StatusDot({ tone = "ready" }) { return <span className={`status-dot ${tone}`} aria-hidden="true" />; }

function TopBar({ clock, onSystem }) {
  return <header className="system-bar"><button className="clawos-wordmark" onClick={onSystem}>Claw<span>OS</span></button><div className="activity-context"><span>Main</span><i>·</i><strong>Gmail</strong></div><div className="system-state"><span><StatusDot />Gateway online</span><button aria-label="Notifications"><BellIcon /></button><button aria-label="System settings"><GearIcon /></button><time>{clock.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time></div></header>;
}

function Gmail({ selected }) {
  const selectedMessage = messages[selected];
  return <section className="gmail-surface" aria-label="Gmail application">
    <header className="gmail-header"><div className="gmail-brand"><img src="https://ssl.gstatic.com/ui/v1/icons/mail/rfr/logo_gmail_lockup_default_1x_r5.png" alt="Gmail" /></div><label className="mail-search"><MagnifyingGlassIcon /><input placeholder="Search mail" /></label><div className="gmail-tools"><button aria-label="Gmail settings"><GearIcon /></button><span className="gmail-avatar">H</span></div></header>
    <aside className="mail-nav"><button className="compose"><PlusIcon />Compose</button><nav><button className="active"><EnvelopeClosedIcon />Inbox <b>5</b></button><button><ArchiveIcon />Starred</button><button><ReloadIcon />Snoozed</button><button><PaperPlaneIcon />Sent</button><button><EnvelopeClosedIcon />Drafts <b>3</b></button></nav><h3>Labels</h3><button className="label"><i className="label-dot work" />Work</button><button className="label"><i className="label-dot personal" />Personal</button><button className="label"><i className="label-dot finance" />Finance</button></aside>
    <main className="mail-main email-open"><div className="mail-toolbar"><div><button aria-label="Back to inbox"><ArrowLeftIcon /></button><button aria-label="Archive"><ArchiveIcon /></button><button aria-label="Snooze"><ClockIcon /></button><button aria-label="Delete"><TrashIcon /></button><button aria-label="More"><DotsHorizontalIcon /></button></div><span>1 of 432</span></div><article className="open-email"><header><h1>{selectedMessage.subject}</h1><span>Inbox ×</span></header><div className="sender-row"><span className="sender-avatar">AA</span><div><strong>{selectedMessage.sender}</strong><small>&lt;alex.anderson@orionteam.io&gt;<br />to me</small></div><time>Aug 28, 2026, 10:42 AM</time></div><div className="email-copy"><p>Hi Harvey,</p><p>Thanks again for leading the design review yesterday. The feedback from the team was incredibly valuable.</p><p>I’ve attached the latest mockups reflecting the changes we discussed, along with a summary of decisions and next steps.</p><p>Please let me know if you have any questions or additional thoughts.</p><p>Best,<br />Alex</p></div><footer className="attachments"><strong>2 Attachments</strong><div><button><FileTextIcon /><span>Orion_Design_Update.pdf</span></button><button><FileTextIcon /><span>Design_Review_Summary.doc</span></button></div></footer></article></main>
  </section>;
}

function AgentShelf({ context, onOpenConversation, onApproval }) {
  const [value, setValue] = useState("");
  const [state, setState] = useState("ready");
  const [notice, setNotice] = useState({ kind: "working", title: "Agent · Drafting a reply from the selected email", detail: "Working in the background · you can keep prompting" });
  const [actionsOpen, setActionsOpen] = useState(false);
  const timer = useRef(null);
  useEffect(() => () => window.clearTimeout(timer.current), []);
  function submit(event) {
    event.preventDefault(); const prompt = value.trim(); if (!prompt || state === "working") return;
    setValue(""); setState("working"); setNotice({ kind: "working", title: `Agent · Working with ${context.sender}`, detail: prompt });
    timer.current = window.setTimeout(() => { setState("ready"); setNotice({ kind: "done", title: "Draft ready from the selected email", detail: "I prepared a concise reply and saved a recovery point before taking any machine action." }); }, 1250);
  }
  return <div className="agent-layer">{notice && <section className={`agent-notice ${notice.kind}`} aria-live="polite"><StatusDot tone={notice.kind === "working" ? "working" : "ready"} /><span><strong>{notice.title}</strong><small>{notice.detail}</small></span>{notice.kind === "done" && <button onClick={onOpenConversation}>Preview</button>}<button className="notice-close" onClick={() => setNotice(null)} aria-label="Dismiss activity"><Cross2Icon /></button></section>}<form className="agent-shelf" onSubmit={submit}><button type="button" className="context-chip"><EnvelopeClosedIcon /><span>Gmail</span><ChevronDownIcon /></button><span className="shelf-state"><StatusDot tone={state === "working" ? "working" : "ready"} />{state === "working" ? "Working" : "Ready"}</span><input aria-label="Ask Agent about Gmail" value={value} onChange={(event) => setValue(event.target.value)} placeholder="Ask Agent about Gmail…" /><button type="button" className="shelf-icon" onClick={() => setActionsOpen((open) => !open)} aria-expanded={actionsOpen} aria-label="Agent actions"><PlusIcon /></button><button type="button" className="shelf-icon voice" aria-label="Voice input"><SpeakerLoudIcon /></button><button className="shelf-send" type="submit" disabled={!value.trim() || state === "working"} aria-label="Send to Agent"><PaperPlaneIcon /></button>{actionsOpen && <div className="shelf-actions"><button type="button" onClick={onOpenConversation}><ChatBubbleIcon /><span><strong>Open conversation</strong><small>Continue in upstream Control UI</small></span></button><button type="button" onClick={onApproval}><CheckCircledIcon /><span><strong>Review approvals</strong><small>Guarded machine actions</small></span></button><button type="button"><RocketIcon /><span><strong>Delegate task</strong><small>Continue in background</small></span></button></div>}</form></div>;
}

function Conversation({ onClose }) {
  const [text, setText] = useState(""); const [turns, setTurns] = useState([{ role: "agent", text: "I’m connected to Gmail and ready to keep working with you here." }]);
  function send(event) { event.preventDefault(); if (!text.trim()) return; setTurns((current) => [...current, { role: "user", text }, { role: "agent", text: "Got it. I’ll continue on the machine and surface any guarded action for approval." }]); setText(""); }
  return <aside className="conversation-panel" aria-label="OpenClaw conversation"><header><div><span className="openclaw-mark">OC</span><span><strong>OpenClaw</strong><small><StatusDot />Main · Ready</small></span></div><button onClick={onClose} aria-label="Close conversation"><Cross2Icon /></button></header><div className="conversation-log">{turns.map((turn, index) => <article className={turn.role} key={index}><span>{turn.role === "agent" ? "Agent" : "You"}</span><p>{turn.text}</p></article>)}</div><form onSubmit={send}><input value={text} onChange={(event) => setText(event.target.value)} placeholder="Continue with Agent…" /><button disabled={!text.trim()}><PaperPlaneIcon /></button></form></aside>;
}

function SystemMenu({ onClose }) { return <div className="menu-scrim" onMouseDown={onClose}><section className="system-menu" onMouseDown={(event) => event.stopPropagation()}><span>CLAWOS SYSTEM</span><button><GearIcon />Settings</button><button><SpeakerLoudIcon />Accessibility</button><button><ReloadIcon />Restart</button><button>Shut down</button></section></div>; }

export function App() {
  const [selected, setSelected] = useState(0); const [conversationOpen, setConversationOpen] = useState(false); const [systemOpen, setSystemOpen] = useState(false); const [clock, setClock] = useState(new Date()); const context = useMemo(() => messages[selected], [selected]);
  useEffect(() => { const id = window.setInterval(() => setClock(new Date()), 1000); return () => window.clearInterval(id); }, []);
  return <main className="clawos-shell"><TopBar clock={clock} onSystem={() => setSystemOpen(true)} /><Gmail selected={selected} onSelect={setSelected} /><AgentShelf context={context} onOpenConversation={() => setConversationOpen(true)} onApproval={() => setConversationOpen(true)} />{conversationOpen && <Conversation onClose={() => setConversationOpen(false)} />}{systemOpen && <SystemMenu onClose={() => setSystemOpen(false)} />}</main>;
}
