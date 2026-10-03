import { useState, useCallback, useEffect } from "react";
import ChatWindow from "./components/chat/ChatWindow.jsx";
import PortfolioPanel from "./components/portfolio/PortfolioPanel.jsx";
import TranscriptLog from "./components/log/TranscriptLog.jsx";
import ErrorState from "./components/common/ErrorState.jsx";
import {
  sendMessage,
  makeUserMessage,
  getPortfolio,
  toClientInfo,
  newConversationId,
  PLACEHOLDER_CLIENT,
} from "./services/chatService.js";

// Top-level layout for the LPL grounded portfolio chatbot.
// Conversation state lives here so every zone (chat / portfolio / log) shares
// one source of truth: the chat renders it, the transcript log mirrors it and
// drives flag-for-confirmation + export.
export default function App() {
  const [conversationId] = useState(newConversationId);
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState(null);
  const [lastQuestion, setLastQuestion] = useState(null);

  // Portfolio panel + header data from /api/portfolio.
  const [portfolio, setPortfolio] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [portfolioError, setPortfolioError] = useState(null);

  const loadPortfolio = useCallback(async () => {
    setPortfolioLoading(true);
    setPortfolioError(null);
    try {
      setPortfolio(await getPortfolio());
    } catch (err) {
      setPortfolioError(err.message || "Could not load your portfolio.");
    } finally {
      setPortfolioLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  const client = portfolio ? toClientInfo(portfolio) : PLACEHOLDER_CLIENT;

  // Send a question: push the user message, show typing, then append the
  // grounded bot reply from the backend. On failure the user message is removed
  // again, so Retry re-sends it without showing the question twice.
  const handleSend = useCallback(
    async (text) => {
      if (isTyping) return;
      setError(null);
      setLastQuestion(text);
      const userMsg = makeUserMessage(text);
      setMessages((prev) => [...prev, userMsg]);
      setIsTyping(true);
      try {
        const botMsg = await sendMessage(text, conversationId);
        setMessages((prev) => [...prev, botMsg]);
      } catch (err) {
        setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
        setError(err.message || "Could not reach the portfolio assistant. Please try again.");
      } finally {
        setIsTyping(false);
      }
    },
    [isTyping, conversationId]
  );

  // Flag a specific answer for advisor confirmation (mocked "sent" state).
  const handleRequestConfirmation = useCallback((messageId) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId ? { ...m, confirmation: "requested" } : m
      )
    );
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Light header with a thin brand-green keyline; brand green is an accent only */}
      <header className="border-b-2 border-brand bg-white shadow-soft">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-1 px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Brand accent mark */}
              <span
                aria-hidden="true"
                className="h-8 w-1.5 rounded-full bg-brand"
              />
              <div>
                <h1 className="text-lg font-semibold text-brand">
                  LPL Portfolio Assistant
                </h1>
                <p className="text-sm text-gray-600">
                  Explore your portfolio: where your money is and how it is invested.
                </p>
              </div>
            </div>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-gray-900">{client.name}</p>
              <p className="text-xs text-gray-500">{client.accountNumber}</p>
            </div>
          </div>
        </div>
        {/* Subtle light compliance band — faint brand tint, dark readable text */}
        <div className="border-t border-brand/10 bg-brand/5 px-4 py-2 text-center text-xs text-gray-700 sm:px-6">
          This tool explains your portfolio using your own account data. It does
          not provide financial advice. For recommendations, contact your advisor.
        </div>
      </header>

      {/* Main 3-zone layout: chat | portfolio | transcript log.
          Panels collapse on smaller screens so chat stays usable on mobile. */}
      <main className="mx-auto flex w-full max-w-[1600px] flex-1 gap-4 overflow-hidden p-2 sm:p-4">
        {/* Zone 1: Chat */}
        <section
          aria-label="Chat"
          className="flex min-w-0 flex-1 flex-col rounded-lg border border-gray-200 bg-white"
        >
          <div className="border-b border-gray-200 px-4 py-3">
            <h2 className="text-sm font-semibold text-gray-700">
              Portfolio Assistant
            </h2>
          </div>
          {error && (
            <div className="px-4 pt-3">
              <ErrorState
                message={error}
                onRetry={lastQuestion ? () => handleSend(lastQuestion) : null}
              />
            </div>
          )}
          <ChatWindow
            messages={messages}
            isTyping={isTyping}
            onSend={handleSend}
            onRequestConfirmation={handleRequestConfirmation}
          />
        </section>

        {/* Zone 2: Portfolio (visible from md so all three show at ~1366px) */}
        <section
          aria-label="Portfolio"
          className="hidden flex-col rounded-lg border border-gray-200 bg-white md:flex md:w-72 xl:w-80"
        >
          <PortfolioPanel
            portfolio={portfolio}
            loading={portfolioLoading}
            error={portfolioError}
            onRetry={loadPortfolio}
          />
        </section>

        {/* Zone 3: Transcript log (visible from lg) */}
        <section
          aria-label="Conversation log"
          className="hidden flex-col rounded-lg border border-gray-200 bg-white lg:flex lg:w-64 xl:w-72"
        >
          <TranscriptLog
            messages={messages}
            client={client}
            onRequestConfirmation={handleRequestConfirmation}
          />
        </section>
      </main>
    </div>
  );
}
