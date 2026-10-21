import React, { useState, useEffect } from 'react';
import { getApiBase } from '@/lib/api-config';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Clock, X, Play, Pause, AlertCircle } from 'lucide-react';

export interface QueuedString {
  id: string;
  tldString: string;
  useCase: string;
  queuedAt: string;
}

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

interface QueuedStringsProps {
  queuedStrings: QueuedString[];
  onRemoveFromQueue: (id: string) => void;
  onSubmitString: (queuedString: QueuedString) => Promise<void>;
  autoSubmit: boolean;
  onToggleAutoSubmit: () => void;
  onClearQueue?: () => void;
}

export const QueuedStrings: React.FC<QueuedStringsProps> = ({
  queuedStrings,
  onRemoveFromQueue,
  onSubmitString,
  autoSubmit,
  onToggleAutoSubmit,
  onClearQueue
}) => {
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastSubmissionError, setLastSubmissionError] = useState<string | null>(null);

  const fetchServerStatus = async () => {
    try {
      const response = await fetch(`${getApiBase()}/api/server-status`);
      const status = await response.json();
      setServerStatus(status);
    } catch (error) {
      console.error('Failed to fetch server status:', error);
      setServerStatus(null);
    }
  };

  useEffect(() => {
    fetchServerStatus();
    
    // Poll server status if we have queued strings or something is running
    const hasActivity = queuedStrings.length > 0 || (serverStatus?.running_count || 0) > 0;
    
    let interval: NodeJS.Timeout | null = null;
    if (hasActivity) {
      interval = setInterval(fetchServerStatus, 3000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [queuedStrings.length, serverStatus?.running_count]);

  // Auto-submit when server becomes available
  // Only react to server availability changes — NOT queue content changes
  // (prevents firing immediately when a string is added with stale serverStatus)
  useEffect(() => {
    if (autoSubmit &&
        serverStatus?.available &&
        queuedStrings.length > 0 &&
        !isSubmitting) {

      const nextString = queuedStrings[0];
      console.log('🚀 Auto-submitting next queued string:', nextString.tldString);
      handleSubmitNext(nextString);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSubmit, serverStatus?.available, isSubmitting]);

  const handleSubmitNext = async (queuedString: QueuedString) => {
    setIsSubmitting(true);
    setLastSubmissionError(null);
    
    try {
      await onSubmitString(queuedString);
      console.log('✅ Successfully submitted:', queuedString.tldString);
    } catch (error) {
      console.error('❌ Failed to submit:', error);
      setLastSubmissionError(`Failed to submit .${queuedString.tldString}: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const currentlyRunning = serverStatus?.currently_running || [];

  // Don't show component when nothing is queued or running
  if (queuedStrings.length === 0 && currentlyRunning.length === 0) {
    return null;
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Evaluation Queue
            {currentlyRunning.length > 0 && (
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                Processing ({currentlyRunning.length})
              </Badge>
            )}
            {queuedStrings.length > 0 && (
              <Badge variant="secondary">
                {queuedStrings.length} waiting
              </Badge>
            )}
          </CardTitle>
          
          {queuedStrings.length > 0 && (
            <div className="flex items-center gap-2">
              <Button
                variant={autoSubmit ? "default" : "outline"}
                size="sm"
                onClick={onToggleAutoSubmit}
                className="flex items-center gap-1"
              >
                {autoSubmit ? (
                  <>
                    <Pause className="w-3 h-3" />
                    Auto-Submit ON
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3" />
                    Auto-Submit OFF
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
        
        {lastSubmissionError && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 mt-2">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-600" />
              <p className="text-red-800 text-sm">{lastSubmissionError}</p>
            </div>
          </div>
        )}
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Currently Running */}
        {currentlyRunning.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-green-700">
                Currently Evaluating ({currentlyRunning.length})
              </span>
            </div>
            {currentlyRunning.map((running, index) => (
              <div key={`${running.tld_string}-${index}`} className="border-l-4 border-green-500 pl-4 bg-green-50 rounded-r-lg p-3 mb-2">
                <div className="text-sm text-gray-700">
                  <span className="font-mono bg-white px-2 py-1 rounded border">.{running.tld_string}</span>
                  {running.use_case && (
                    <span className="text-gray-500 ml-2">({running.use_case})</span>
                  )}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Started: {new Date(running.started_at).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Queued Strings */}
        {queuedStrings.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-700">
                Waiting in Queue ({queuedStrings.length})
              </h4>
              <div className="flex items-center gap-2">
                {onClearQueue && queuedStrings.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onClearQueue}
                    className="h-8 text-red-600 hover:text-red-800 hover:border-red-300"
                  >
                    <X className="w-3 h-3 mr-1" />
                    Clear Queue
                  </Button>
                )}
                {!autoSubmit && queuedStrings.length > 0 && serverStatus?.available && (
                  <Button
                    size="sm"
                    onClick={() => handleSubmitNext(queuedStrings[0])}
                    disabled={isSubmitting}
                    className="h-8"
                  >
                    {isSubmitting ? (
                      <>
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-1"></div>
                        Submitting...
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3 mr-1" />
                        Submit Next
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
            
            <div className="space-y-2">
              {queuedStrings.map((queuedString, index) => (
                <div 
                  key={queuedString.id} 
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    index === 0 ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Badge variant={index === 0 ? "default" : "secondary"} className="text-xs">
                      #{index + 1}
                    </Badge>
                    <div>
                      <div className="font-mono text-sm">
                        .{queuedString.tldString}
                      </div>
                      {queuedString.useCase && (
                        <div className="text-xs text-gray-500">
                          {queuedString.useCase}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {index === 0 && serverStatus?.available ? 'Ready to submit' : 
                       index === 0 ? 'Waiting for server' : 
                       `Position ${index + 1}`}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onRemoveFromQueue(queuedString.id)}
                      className="h-6 w-6 p-0 text-gray-400 hover:text-red-600"
                    >
                      <X className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Status Footer */}
        <div className="text-xs text-gray-500 pt-2 border-t">
          {currentlyRunning.length > 0 ? (
            <>
              ⏳ Server is busy - new submissions will wait for <span className="font-mono">.{currentlyRunning[0].tld_string}</span> to complete
            </>
          ) : queuedStrings.length > 0 && serverStatus?.available ? (
            <>
              ✅ Server is ready - {autoSubmit ? 'auto-submitting next string' : 'click "Submit Next" to proceed'}
            </>
          ) : queuedStrings.length > 0 ? (
            <>
              🔄 Checking server availability...
            </>
          ) : (
            <>
              🚀 Ready for new evaluations
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
};