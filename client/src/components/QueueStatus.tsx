import React, { useState, useEffect } from 'react';
import { getApiBase } from '@/lib/api-config';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';

interface ServerStatus {
  available: boolean;
  running_count: number;
  currently_running: Array<{
    tld_string: string;
    use_case: string;
    started_at: string;
    status: string;
  }>;
}

interface QueueStatusProps {
  pendingQueue: Array<{ tldString: string; useCase: string }>;
  onClearQueue?: () => void;
}

export const QueueStatus: React.FC<QueueStatusProps> = ({ pendingQueue, onClearQueue }) => {
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [serverDown, setServerDown] = useState(false);
  const failCountRef = React.useRef(0);

  const fetchServerStatus = async () => {
    try {
      const response = await fetch(`${getApiBase()}/api/server-status`);
      const status = await response.json();
      setServerStatus(status);
      setServerDown(false);
      failCountRef.current = 0;
    } catch {
      failCountRef.current += 1;
      setServerDown(true);
      // Only log on first failure, not every poll
      if (failCountRef.current === 1) {
        console.warn('QueueStatus: Backend server unreachable');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchServerStatus();

    // Only poll if there's activity (something running or pending)
    const hasActivity = (serverStatus?.running_count || 0) > 0 || pendingQueue.length > 0;

    let interval: NodeJS.Timeout | null = null;
    if (hasActivity && !serverDown) {
      // Poll every 3 seconds when there's activity and server is up
      interval = setInterval(fetchServerStatus, 3000);
    } else if (serverDown) {
      // Back off to 15 seconds when server is down
      interval = setInterval(fetchServerStatus, 15000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [serverStatus?.running_count, pendingQueue.length, serverDown]);

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Queue Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-500">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  const currentlyRunning = serverStatus?.currently_running || [];
  const hasQueue = currentlyRunning.length > 0 || pendingQueue.length > 0;

  if (!hasQueue) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            Queue Status
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              Ready
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-gray-600">
            ✅ Server is available - ready to process new evaluations
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          Queue Status
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            Processing
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Currently Running */}
        {currentlyRunning.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-blue-700">
                Currently Running ({currentlyRunning.length})
              </span>
            </div>
            {currentlyRunning.map((running, index) => (
              <div key={`${running.tld_string}-${index}`} className="border-l-4 border-blue-500 pl-3 mb-2">
                <div className="text-sm text-gray-700">
                  <span className="font-mono bg-gray-100 px-1 rounded">.{running.tld_string}</span>
                  {running.use_case && (
                    <span className="text-gray-500 ml-2">
                      ({running.use_case.includes('application') || running.use_case.includes('icann') ? 
                        '📄 Application Generation' : 
                        '🔍 String Evaluation'
                      })
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Started: {new Date(running.started_at).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pending Queue */}
        {pendingQueue.length > 0 && (
          <div className="border-l-4 border-yellow-500 pl-3">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
              <span className="text-sm font-medium text-yellow-700">
                Waiting in Queue ({pendingQueue.length})
              </span>
              {onClearQueue && (
                <button
                  onClick={onClearQueue}
                  className="text-xs text-red-600 hover:text-red-800 ml-auto"
                >
                  Clear Queue
                </button>
              )}
            </div>
            <div className="space-y-1">
              {pendingQueue.map((item, index) => (
                <div key={index} className="text-sm text-gray-700 flex items-center gap-2">
                  <span className="text-yellow-600 font-mono text-xs">#{index + 1}</span>
                  <span className="font-mono bg-gray-100 px-1 rounded">.{item.tldString}</span>
                  {item.useCase && (
                    <span className="text-gray-500">({item.useCase})</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Queue Info */}
        <div className="text-xs text-gray-500 pt-2 border-t">
          {currentlyRunning.length > 0 ? (
            <>
              ⏳ New submissions will wait for <span className="font-mono">.{currentlyRunning[0].tld_string}</span> to complete
            </>
          ) : (
            <>
              🚀 Processing queue automatically
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}; 