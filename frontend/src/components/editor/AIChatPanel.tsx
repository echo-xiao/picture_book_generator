import { ChevronRight, MessageCircle, Send } from "lucide-react";

interface AIChatPanelProps {
  chatOpen: boolean;
  chatMessages: Array<{ role: string; content: string }>;
  chatInput: string;
  chatLoading: boolean;
  onToggle: () => void;
  onInputChange: (value: string) => void;
  onSend: () => void;
}

export default function AIChatPanel({
  chatOpen,
  chatMessages,
  chatInput,
  chatLoading,
  onToggle,
  onInputChange,
  onSend,
}: AIChatPanelProps) {
  return (
    <div className="card !p-3">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between"
      >
        <h3 className="font-display font-bold text-gray-700 text-xs flex items-center gap-1">
          <MessageCircle size={12} /> AI Assistant
        </h3>
        <ChevronRight size={14} className={`text-gray-400 transition-transform ${chatOpen ? "rotate-90" : ""}`} />
      </button>

      {chatOpen && (
        <div className="mt-2">
          {/* Chat Messages */}
          <div className="bg-cream/50 rounded-lg p-2 mb-2 max-h-48 overflow-y-auto space-y-2">
            {chatMessages.length === 0 && (
              <p className="text-[10px] text-gray-400 text-center py-2">
                Describe the illustration you want, or ask to adjust fields.
              </p>
            )}
            {chatMessages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-lg px-2.5 py-1.5 text-[11px] !leading-[1.26] ${
                  msg.role === "user"
                    ? "bg-coral/20 text-gray-800"
                    : "bg-white text-gray-700 border border-peach/30"
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-white border border-peach/30 rounded-lg px-2.5 py-1.5 text-[11px] text-gray-400">
                  Thinking...
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="flex gap-1.5">
            <input
              value={chatInput}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); } }}
              className="flex-1 rounded-lg border border-peach/50 px-2.5 py-1.5 text-xs focus:ring-2 focus:ring-coral/30 focus:border-coral outline-none"
              placeholder="e.g. Make the scene a rainy night..."
              disabled={chatLoading}
            />
            <button
              onClick={onSend}
              disabled={chatLoading || !chatInput.trim()}
              className="bg-coral text-white px-2.5 py-1.5 rounded-lg hover:bg-coral/80 transition-colors disabled:opacity-50"
            >
              <Send size={12} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
