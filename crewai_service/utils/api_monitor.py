"""
API Usage Monitoring for CrewAI Service
Tracks API calls, performance, and quality metrics
"""
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class APIMonitor:
    """Monitor API usage patterns and performance"""
    
    def __init__(self):
        self.call_counts = {}
        self.performance_data = {}
        self.quality_scores = {}
        self.alerts = []
        self.session_start = datetime.utcnow()
    
    def track_api_call(self, task_id: str, agent_name: str, call_type: str = "llm"):
        """Track an API call"""
        key = f"{task_id}:{agent_name}"
        
        if key not in self.call_counts:
            self.call_counts[key] = {
                'llm_calls': 0,
                'tool_calls': 0,
                'total_calls': 0,
                'start_time': datetime.utcnow()
            }
        
        self.call_counts[key][f'{call_type}_calls'] += 1
        self.call_counts[key]['total_calls'] += 1
        
        # Check for excessive calls
        if self.call_counts[key]['total_calls'] > 50:
            self._alert_excessive_calls(task_id, agent_name, self.call_counts[key]['total_calls'])
    
    def track_task_performance(self, task_id: str, duration: float, success: bool):
        """Track task execution performance"""
        self.performance_data[task_id] = {
            'duration': duration,
            'success': success,
            'timestamp': datetime.utcnow(),
            'calls_made': self.get_task_call_count(task_id)
        }
    
    def track_quality_score(self, task_id: str, score: float, metrics: Dict[str, Any]):
        """Track output quality metrics"""
        self.quality_scores[task_id] = {
            'score': score,
            'metrics': metrics,
            'timestamp': datetime.utcnow()
        }
    
    def get_task_call_count(self, task_id: str) -> int:
        """Get total API calls for a task"""
        total = 0
        for key, data in self.call_counts.items():
            if key.startswith(f"{task_id}:"):
                total += data['total_calls']
        return total
    
    def _alert_excessive_calls(self, task_id: str, agent_name: str, call_count: int):
        """Alert on excessive API calls"""
        alert = {
            'type': 'excessive_calls',
            'task_id': task_id,
            'agent_name': agent_name,
            'call_count': call_count,
            'timestamp': datetime.utcnow(),
            'message': f"⚠️ Agent {agent_name} made {call_count} API calls for task {task_id}"
        }
        self.alerts.append(alert)
        logger.warning(alert['message'])
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current monitoring session"""
        total_calls = sum(data['total_calls'] for data in self.call_counts.values())
        avg_quality = sum(data['score'] for data in self.quality_scores.values()) / len(self.quality_scores) if self.quality_scores else 0
        
        return {
            'session_duration': (datetime.utcnow() - self.session_start).total_seconds(),
            'total_api_calls': total_calls,
            'tasks_monitored': len(set(key.split(':')[0] for key in self.call_counts.keys())),
            'average_quality_score': round(avg_quality, 2),
            'alerts_generated': len(self.alerts),
            'performance_data': len(self.performance_data),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def export_metrics(self, filepath: str):
        """Export monitoring data to file"""
        data = {
            'summary': self.get_session_summary(),
            'call_counts': self.call_counts,
            'performance_data': self.performance_data,
            'quality_scores': self.quality_scores,
            'alerts': self.alerts
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"📊 Monitoring metrics exported to {filepath}")

# Global monitor instance
monitor = APIMonitor()
