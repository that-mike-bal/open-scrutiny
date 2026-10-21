import React from 'react';
import { MessageSquare } from 'lucide-react';
import { Button } from './ui/button';

interface ChatToggleProps {
  isOpen: boolean;
  onClick: () => void;
  hasUnread?: boolean;
}

const ChatToggle: React.FC<ChatToggleProps> = ({ isOpen, onClick, hasUnread = false }) => {
  if (isOpen) return null;

  return (
    <Button
      onClick={onClick}
      className="fixed bottom-4 right-4 h-12 w-12 rounded-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg z-40 transition-all duration-300 hover:scale-105"
      size="sm"
    >
      <div className="relative">
        <MessageSquare className="h-6 w-6" />
        {hasUnread && (
          <div className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full animate-pulse" />
        )}
      </div>
    </Button>
  );
};

export default ChatToggle;
