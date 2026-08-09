import React, { useState, useEffect, useRef } from 'react';
import { Send, Upload, Cpu, Book, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

function App() {
  const [messages, setMessages] = useState([
    { role: 'aura', text: 'AURA System Online. Ready to retrieve academic units from your notes.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const scrollRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('http://127.0.0.1:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'aura', text: data.answer }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'aura', text: 'Error: Connection lost.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://127.0.0.1:8000/upload', { method: 'POST', body: formData });
      const data = await res.json();
      alert(data.message);
    } catch (err) {
      alert("Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4 md:p-6">
      {/* Header */}
      <nav className="flex items-center justify-between mb-6 p-4 bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-2xl shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-500/10 rounded-lg">
            <Cpu className="text-cyan-400" size={24} />
          </div>
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            AURA <span className="text-xs font-light text-slate-500 ml-2 border-l border-slate-700 pl-2">ACADEMIC RETRIEVAL</span>
          </h1>
        </div>
        
        <label className="flex items-center gap-2 cursor-pointer bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-sm font-medium transition-all border border-slate-700">
          <Upload size={16} />
          {uploading ? "Ingesting..." : "Upload Notes"}
          <input type="file" className="hidden" onChange={handleUpload} accept=".pdf" />
        </label>
      </nav>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-6">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
              msg.role === 'user' ? 'bg-cyan-600' : 'bg-slate-800 border border-slate-700'
            }`}>
              {msg.role === 'user' ? <User size={16} /> : <Book size={16} className="text-cyan-400" />}
            </div>
            <div className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed shadow-sm ${
              msg.role === 'user' 
                ? 'bg-cyan-600/10 border border-cyan-500/20 text-cyan-50' 
                : 'bg-slate-900 border border-slate-800 text-slate-300'
            }`}>
              <div className="prose prose-invert prose-sm max-w-none">
    <ReactMarkdown>
      {msg.text}
    </ReactMarkdown>
  </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-4 animate-pulse">
            <div className="w-8 h-8 bg-slate-800 rounded-lg" />
            <div className="h-10 w-32 bg-slate-800 rounded-2xl" />
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input Area */}
      <div className="mt-6 relative">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask AURA about your notes..."
          className="w-full bg-slate-900 border border-slate-800 rounded-2xl py-4 px-6 pr-14 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 transition-all placeholder:text-slate-600 shadow-2xl"
        />
        <button 
          onClick={handleSend}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl transition-colors"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
}

export default App;