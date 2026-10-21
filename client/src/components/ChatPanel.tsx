import React, { useState, useRef, useEffect } from 'react';
import { getApiBase } from '@/lib/api-config';
import { X, Send, MessageSquare, Minimize2, ExternalLink, Book, HelpCircle, FileText } from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: ChatSource[];
  metadata?: {
    query_type?: string;
    confidence?: number;
    sources_count?: number;
  };
}

interface ChatSource {
  id: string;
  type: 'guidebook' | 'question' | 'resource';
  title: string;
  similarity_score: number;
  url?: string;
  section?: string;
  excerpt: string;
}

interface ChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
  isMinimized?: boolean;
  onMinimizedChange?: (minimized: boolean) => void;
  context?: {
    tld_string?: string;
    current_question?: string;
    application_id?: string;
    page_type?: string;
  };
}

const ChatPanel: React.FC<ChatPanelProps> = ({ 
  isOpen, 
  onClose, 
  isMinimized: externalMinimized = false,
  onMinimizedChange,
  context 
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // Use external minimized state if provided, otherwise use internal state
  const isMinimized = externalMinimized;
  const setIsMinimized = (minimized: boolean) => {
    if (onMinimizedChange) {
      onMinimizedChange(minimized);
    }
  };
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && !isMinimized) {
      inputRef.current?.focus();
    }
  }, [isOpen, isMinimized]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch(`${getApiBase()}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputMessage.trim(),
          context: context,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Chat API error:', response.status, errorText);
        throw new Error(`API Error ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      
      // Check if the response indicates an error
      if (!data.success && data.error) {
        console.error('Chat service error:', data.error);
        throw new Error(data.error);
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: data.response || 'I received your message but couldn\'t generate a response.',
        timestamp: new Date(),
        sources: data.sources || [],
        metadata: data.metadata,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `I apologize, but I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'guidebook':
        return <Book className="h-3 w-3" />;
      case 'question':
        return <HelpCircle className="h-3 w-3" />;
      case 'resource':
        return <FileText className="h-3 w-3" />;
      default:
        return <ExternalLink className="h-3 w-3" />;
    }
  };

  const getSourceColor = (type: string) => {
    switch (type) {
      case 'guidebook':
        return 'bg-blue-100 text-blue-800';
      case 'question':
        return 'bg-green-100 text-green-800';
      case 'resource':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (!isOpen) return null;

  return (
    <div className={`fixed right-0 top-0 h-full bg-white border-l border-gray-200 shadow-xl z-50 transition-all duration-300 ${
      isMinimized ? 'w-12' : 'w-96'
    } flex flex-col`}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        {!isMinimized ? (
          <>
            <div className="flex items-center space-x-2">
              <MessageSquare className="h-5 w-5 text-blue-600" />
              <span className="font-semibold text-sm">TLD Assistant</span>
              {context?.tld_string && (
                <Badge variant="outline" className="text-xs">
                  .{context.tld_string}
                </Badge>
              )}
            </div>
            <div className="flex items-center space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsMinimized(true)}
                className="h-6 w-6 p-0"
                title="Minimize panel"
              >
                <Minimize2 className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="h-6 w-6 p-0"
                title="Close chat"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center space-y-2 w-full">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMinimized(false)}
              className="h-8 w-8 p-0"
              title="Expand chat panel"
            >
              <MessageSquare className="h-4 w-4 text-blue-600" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-6 w-6 p-0"
              title="Close chat"
            >
              <X className="h-3 w-3 text-gray-400" />
            </Button>
          </div>
        )}
      </div>

      {!isMinimized && (
        <>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 text-sm mt-8">
                <MessageSquare className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                <p>Ask me about TLD strings and gTLD applications!</p>
                <div className="mt-4 space-y-1 text-xs">
                  <p>• String similarity and evaluation criteria</p>
                  <p>• Application process timeline and requirements</p>
                  <p>• Financial, technical, and operational guidance</p>
                  <p>• Community consultation and engagement</p>
                  <p>• Database insights from existing evaluations</p>
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    message.type === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                  
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-3 space-y-2">
                      <div className="text-xs font-medium text-gray-600">Sources:</div>
                      {message.sources.map((source, index) => (
                        <Card key={index} className="p-2 bg-white border border-gray-200">
                          <CardContent className="p-0">
                            <div className="flex items-start justify-between space-x-2">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center space-x-2 mb-1">
                                  <Badge className={`text-xs ${getSourceColor(source.type)}`}>
                                    <span className="flex items-center space-x-1">
                                      {getSourceIcon(source.type)}
                                      <span>{source.type.toUpperCase()}</span>
                                    </span>
                                  </Badge>
                                  <span className="text-xs text-gray-500">
                                    {Math.round(source.similarity_score * 100)}% match
                                  </span>
                                </div>
                                <div className="text-xs font-medium text-gray-900 mb-1">
                                  {source.title}
                                </div>
                                <div className="text-xs text-gray-600">
                                  {source.excerpt}
                                </div>
                                {source.section && (
                                  <div className="text-xs text-gray-500 mt-1">
                                    Section: {source.section}
                                  </div>
                                )}
                              </div>
                              {source.url && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => window.open(source.url, '_blank')}
                                  className="h-6 w-6 p-0 flex-shrink-0"
                                >
                                  <ExternalLink className="h-3 w-3" />
                                </Button>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                  
                  <div className="text-xs opacity-70 mt-2">
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg p-3">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span className="text-sm text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-gray-200 flex-shrink-0">
            <div className="flex space-x-2">
              <Input
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about TLD strings or applications..."
                className="flex-1 text-sm"
                disabled={isLoading}
              />
              <Button
                onClick={sendMessage}
                disabled={isLoading || !inputMessage.trim()}
                size="sm"
                className="px-3"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ChatPanel;
