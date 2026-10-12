/* ======================================================
   AICopilot — GeoMeasure Studio AI Geospatial Copilot
   Interactive panel for natural language geospatial intelligence,
   parcel rankings, geometry validation, and map highlights.
   ====================================================== */

import { useState, useEffect, useRef } from 'react';
import type { UploadedFile, AIAssistantResponse, AIAssistantStatus } from '../../types';
import { analyzeWithCopilot, getAssistantStatus } from '../../api/client';
import { useAuth } from '../../context/AuthContext';

interface AICopilotProps {
  activeFile: UploadedFile | null;
  onHighlightFeatures?: (indices: number[]) => void;
  highlightedIndices?: number[];
}

interface MessageItem {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  response?: AIAssistantResponse;
  isError?: boolean;
}

const QUICK_PROMPTS = [
  { label: 'Rank 5 Largest Parcels', prompt: 'Calculate all parcel areas and rank the five largest.' },
  { label: 'Validate Geometries', prompt: 'Find overlapping or invalid polygons.' },
  { label: 'Explain CRS', prompt: 'Explain the CRS used for measurement.' },
  { label: 'Dataset Summary', prompt: 'Summarize feature counts and geometry types.' },
  { label: 'Export to CSV', prompt: 'Export validated results to CSV.' },
];

let messageSeq = 0;
function nextMsgId(prefix: string): string {
  messageSeq += 1;
  return `${prefix}_${messageSeq}_${Math.floor(Math.random() * 1000)}`;
}

function getFormattedTime(): string {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
}

export default function AICopilot({
  activeFile,
  onHighlightFeatures,
  highlightedIndices = [],
}: AICopilotProps) {
  const { session } = useAuth();
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputTask, setInputTask] = useState('');
  const [loading, setLoading] = useState(false);
  const [privacyMode, setPrivacyMode] = useState<'standard' | 'local_only'>('standard');
  const [status, setStatus] = useState<AIAssistantStatus | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load assistant provider status
  useEffect(() => {
    let mounted = true;
    getAssistantStatus()
      .then((data) => {
        if (mounted) setStatus(data);
      })
      .catch(() => {
        // Safe fallback
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Scroll to bottom of message list on updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (taskText: string) => {
    const trimmed = taskText.trim();
    if (!trimmed || loading) return;

    const userMsg: MessageItem = {
      id: nextMsgId('usr'),
      sender: 'user',
      text: trimmed,
      timestamp: getFormattedTime(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputTask('');
    setLoading(true);

    try {
      const resp = await analyzeWithCopilot(
        trimmed,
        activeFile?.id,
        undefined,
        privacyMode,
        session?.access_token
      );

      const assistantMsg: MessageItem = {
        id: nextMsgId('ast'),
        sender: 'assistant',
        text: resp.explanation,
        timestamp: getFormattedTime(),
        response: resp,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // If response flagged feature indices, automatically highlight them on the map preview
      if (resp.highlighted_indices && resp.highlighted_indices.length > 0 && onHighlightFeatures) {
        onHighlightFeatures(resp.highlighted_indices);
      }
    } catch (err: unknown) {
      let errMsg = 'Failed to analyze geospatial query. Please verify provider connectivity.';
      if (err && typeof err === 'object' && 'response' in err) {
        const axErr = err as { response?: { data?: { detail?: string } } };
        if (axErr.response?.data?.detail) {
          errMsg = axErr.response.data.detail;
        }
      } else if (err instanceof Error) {
        errMsg = err.message;
      }

      const errorMsg: MessageItem = {
        id: nextMsgId('err'),
        sender: 'assistant',
        text: errMsg,
        timestamp: getFormattedTime(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    if (onHighlightFeatures) onHighlightFeatures([]);
  };

  return (
    <div
      className="bg-surface-900/80 backdrop-blur-xl border border-surface-700/60 rounded-2xl flex flex-col shadow-2xl overflow-hidden h-[620px]"
      id="ai-copilot-panel"
    >
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-surface-800/80 bg-surface-950/40 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 via-teal-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <svg className="w-4 h-4 text-surface-950" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-semibold text-surface-100">AI Copilot</h3>
              <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                v2 Phase 4
              </span>
            </div>
            <p className="text-[11px] text-surface-400 truncate max-w-[220px]">
              {activeFile ? `Active: ${activeFile.original_filename}` : 'No dataset selected'}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Privacy Toggle */}
          <button
            type="button"
            onClick={() => setPrivacyMode(privacyMode === 'standard' ? 'local_only' : 'standard')}
            title={
              privacyMode === 'local_only'
                ? 'Local-Only Mode: Zero telemetry or geometry is sent to cloud inference providers.'
                : 'Standard Hybrid: Low-latency local or hosted fallback inference permitted.'
            }
            className={`text-xs px-2.5 py-1 rounded-lg border transition-all flex items-center space-x-1.5 ${
              privacyMode === 'local_only'
                ? 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                : 'bg-surface-800/60 border-surface-700/50 text-surface-400 hover:text-surface-200'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${privacyMode === 'local_only' ? 'bg-amber-400' : 'bg-surface-500'}`} />
            <span>{privacyMode === 'local_only' ? 'Local-Only' : 'Hybrid AI'}</span>
          </button>

          {/* Clear history */}
          {messages.length > 0 && (
            <button
              type="button"
              onClick={clearChat}
              title="Clear conversation"
              className="text-surface-500 hover:text-surface-300 text-xs p-1.5 rounded-lg hover:bg-surface-800/50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Provider Info Banner */}
      <div className="px-5 py-2 bg-surface-950/30 border-b border-surface-800/40 flex items-center justify-between text-[11px] text-surface-400">
        <div className="flex items-center space-x-2 truncate">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-surface-300 font-mono font-medium truncate">
            {status?.provider_mode === 'hosted_only'
              ? `Groq Hosted (${status.groq_model})`
              : status?.provider_mode === 'local_only'
              ? `Ollama Local (${status.ollama_model})`
              : `Hybrid: Local Ollama (${status?.ollama_model || 'qwen3.5:2b'}) / Hosted Fallback`}
          </span>
        </div>
        <span className="text-surface-500 text-[10px] hidden sm:inline">Sub-50ms GIS Fast-Path</span>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4 text-surface-400">
            <div className="w-12 h-12 rounded-2xl bg-surface-800/40 border border-surface-700/30 flex items-center justify-center text-surface-300">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <h4 className="text-sm font-medium text-surface-200">Ask GeoMeasure Copilot</h4>
              <p className="text-xs text-surface-400 mt-1 max-w-xs leading-relaxed">
                Query parcel metric areas, detect topological self-intersections, review CRS reprojected rationale, or export calculations.
              </p>
            </div>

            {/* Quick Prompt Chips */}
            <div className="w-full max-w-sm pt-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-surface-500 mb-2">
                Suggested GIS Operations
              </p>
              <div className="flex flex-wrap gap-1.5 justify-center">
                {QUICK_PROMPTS.map((qp, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSend(qp.prompt)}
                    className="text-xs bg-surface-800/50 hover:bg-emerald-500/10 hover:text-emerald-300 hover:border-emerald-500/30 text-surface-300 px-2.5 py-1.5 rounded-lg border border-surface-700/40 transition-all text-left"
                  >
                    {qp.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'} space-y-1.5`}
            >
              <div className="flex items-center space-x-1.5 text-[10px] text-surface-500 px-1">
                <span>{msg.sender === 'user' ? 'You' : 'Copilot'}</span>
                <span>•</span>
                <span>{msg.timestamp}</span>
              </div>

              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-900/20'
                    : msg.isError
                    ? 'bg-rose-950/30 border border-rose-800/40 text-rose-300'
                    : 'bg-surface-800/60 border border-surface-700/50 text-surface-200 shadow-md'
                }`}
              >
                {/* Text Explanation */}
                <p className="whitespace-pre-line">{msg.text}</p>

                {/* Assistant GIS Result Metadata */}
                {msg.response && (
                  <div className="mt-3 pt-3 border-t border-surface-700/40 space-y-2.5 text-[11px]">
                    {/* Tool Badges & Latency */}
                    <div className="flex flex-wrap items-center gap-1.5">
                      {msg.response.actions_executed.map((act) => (
                        <span
                          key={act}
                          className="px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-mono text-[10px]"
                        >
                          ⚙️ {act}
                        </span>
                      ))}

                      <span className="px-2 py-0.5 rounded bg-surface-900/60 border border-surface-700/40 text-surface-400 font-mono text-[10px]">
                        ⚡ {msg.response.latency_breakdown.total_ms}ms (
                        {msg.response.provider_metadata.provider === 'deterministic_engine'
                          ? 'deterministic engine'
                          : `${msg.response.provider_metadata.provider} / ${msg.response.provider_metadata.model}`}
                        )
                      </span>
                    </div>

                    {/* Top Features Table */}
                    {msg.response.top_features && msg.response.top_features.length > 0 && (
                      <div className="bg-surface-950/40 rounded-xl p-2.5 border border-surface-800/60 overflow-x-auto">
                        <table className="w-full text-left font-mono text-[10px]">
                          <thead>
                            <tr className="text-surface-500 border-b border-surface-800/80">
                              <th className="pb-1">#</th>
                              <th className="pb-1">Feature</th>
                              <th className="pb-1">Area (m²)</th>
                              <th className="pb-1">Hectares</th>
                              <th className="pb-1">CRS</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-surface-800/40 text-surface-300">
                            {msg.response.top_features.map((f, i) => (
                              <tr key={i} className="hover:bg-surface-800/20">
                                <td className="py-1 text-surface-500">{i + 1}</td>
                                <td className="py-1 text-emerald-400 font-medium">{f.feature_id || `Index ${f.feature_index}`}</td>
                                <td className="py-1">{f.area_sq_meters?.toLocaleString() ?? '—'}</td>
                                <td className="py-1">{f.area_hectares ? f.area_hectares.toFixed(4) : '—'}</td>
                                <td className="py-1 text-surface-400">{f.measurement_crs || 'Local UTM'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Highlight Button */}
                    {msg.response.highlighted_indices && msg.response.highlighted_indices.length > 0 && onHighlightFeatures && (
                      <div className="flex items-center space-x-2 pt-1">
                        <button
                          type="button"
                          onClick={() => onHighlightFeatures(msg.response?.highlighted_indices || [])}
                          className="px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-medium flex items-center space-x-1 transition-colors"
                        >
                          <span>🗺️ Highlight {msg.response.highlighted_indices.length} Features on Map</span>
                        </button>
                      </div>
                    )}

                    {/* Export Artifact Link */}
                    {msg.response.export_artifact && (
                      <div className="bg-emerald-950/20 border border-emerald-500/20 rounded-xl p-2.5 flex items-center justify-between">
                        <div>
                          <p className="font-semibold text-emerald-300">
                            Artifact: {msg.response.export_artifact.filename}
                          </p>
                          <p className="text-[10px] text-surface-400">
                            {msg.response.export_artifact.record_count} features ready for export
                          </p>
                        </div>
                        {msg.response.export_artifact.download_url && (
                          <a
                            href={msg.response.export_artifact.download_url}
                            download
                            className="px-2.5 py-1 rounded bg-emerald-500 text-surface-950 font-semibold text-[10px] hover:bg-emerald-400 transition-colors"
                          >
                            Download
                          </a>
                        )}
                      </div>
                    )}

                    {/* Validation Warnings */}
                    {msg.response.validation_warnings && msg.response.validation_warnings.length > 0 && (
                      <div className="bg-amber-950/20 border border-amber-500/20 rounded-xl p-2.5 space-y-1">
                        <p className="font-semibold text-amber-400 text-[10px]">Validation Warnings:</p>
                        {msg.response.validation_warnings.map((w, idx) => (
                          <p key={idx} className="text-amber-200 text-[10px]">
                            • {w}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center space-x-2 text-surface-400 text-xs px-2 py-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="animate-pulse">GeoMeasure AI analyzing geospatial features...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Highlighted Status Notice */}
      {highlightedIndices.length > 0 && (
        <div className="px-5 py-1.5 bg-amber-500/10 border-t border-amber-500/20 flex items-center justify-between text-[11px] text-amber-300 flex-shrink-0">
          <span>Highlighting {highlightedIndices.length} feature(s) on map canvas</span>
          <button
            type="button"
            onClick={() => onHighlightFeatures && onHighlightFeatures([])}
            className="text-[10px] underline hover:text-amber-100"
          >
            Clear Highlight
          </button>
        </div>
      )}

      {/* Input Area */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(inputTask);
        }}
        className="p-3 bg-surface-950/50 border-t border-surface-800/80 flex items-center space-x-2 flex-shrink-0"
      >
        <input
          type="text"
          value={inputTask}
          onChange={(e) => setInputTask(e.target.value)}
          placeholder={activeFile ? `Ask about ${activeFile.original_filename}...` : 'Ask a GIS question or select a dataset...'}
          disabled={loading}
          className="flex-1 bg-surface-900/90 border border-surface-700/60 rounded-xl px-3.5 py-2.5 text-xs text-surface-100 placeholder-surface-500 focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30 transition-all disabled:opacity-50"
        />

        <button
          type="submit"
          disabled={loading || !inputTask.trim()}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600 text-surface-950 font-semibold p-2.5 rounded-xl transition-all flex items-center justify-center shadow-lg shadow-emerald-600/20"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </form>
    </div>
  );
}
