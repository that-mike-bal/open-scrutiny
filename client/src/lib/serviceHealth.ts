/**
 * Service Health Check Utilities
 *
 * Validates that all required services are running before allowing
 * critical operations that could cost $200k+ if they fail.
 */

import { getApiBase } from './api-config'

export interface ServiceStatus {
  name: string
  url: string
  status: 'healthy' | 'unhealthy' | 'unknown'
  responseTime?: number
  error?: string
}

export interface HealthCheckResult {
  allHealthy: boolean
  services: ServiceStatus[]
  criticalFailures: string[]
  recommendations: string[]
}

const REQUIRED_SERVICES = [
  {
    name: 'CrewAI Service',
    url: `${getApiBase()}/health`,
    critical: true
  },
  {
    name: 'IANA TLD API',
    url: `${getApiBase()}/api/iana-tlds`,
    critical: true
  },
  {
    name: 'Blocked Names API',
    url: `${getApiBase()}/api/blocked-names`,
    critical: true
  },
  {
    name: 'Queue Status API',
    url: `${getApiBase()}/api/queue/status`,
    critical: false
  }
]

/**
 * Check if a single service is healthy
 */
async function checkService(name: string, url: string, timeoutMs: number = 5000): Promise<ServiceStatus> {
  const startTime = Date.now()
  
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
    
    const response = await fetch(url, {
      method: 'GET',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    clearTimeout(timeoutId)
    const responseTime = Date.now() - startTime
    
    if (response.ok) {
      return {
        name,
        url,
        status: 'healthy',
        responseTime
      }
    } else {
      return {
        name,
        url, 
        status: 'unhealthy',
        responseTime,
        error: `HTTP ${response.status}: ${response.statusText}`
      }
    }
    
  } catch (error) {
    const responseTime = Date.now() - startTime
    
    let errorMessage = 'Unknown error'
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        errorMessage = `Timeout after ${timeoutMs}ms`
      } else if (error.message.includes('ECONNREFUSED')) {
        errorMessage = 'Service not running'
      } else {
        errorMessage = error.message
      }
    }
    
    return {
      name,
      url,
      status: 'unhealthy',
      responseTime,
      error: errorMessage
    }
  }
}

/**
 * Check health of all required services
 */
export async function checkServiceHealth(): Promise<HealthCheckResult> {
  const servicePromises = REQUIRED_SERVICES.map(service => 
    checkService(service.name, service.url)
  )
  
  const services = await Promise.all(servicePromises)
  
  const criticalFailures: string[] = []
  const recommendations: string[] = []
  
  services.forEach((service, index) => {
    const serviceConfig = REQUIRED_SERVICES[index]
    
    if (service.status !== 'healthy') {
      if (serviceConfig.critical) {
        criticalFailures.push(`${service.name}: ${service.error}`)
      }
      
      // Add specific recommendations
      if (service.name === 'CrewAI Service') {
        recommendations.push('Start CrewAI service: python -m uvicorn crewai_service.app:app --host 0.0.0.0 --port 8000')
      } else if (service.error?.includes('Timeout')) {
        recommendations.push(`${service.name} is responding slowly - check server load`)
      }
    }
  })
  
  const allHealthy = criticalFailures.length === 0
  
  if (!allHealthy) {
    recommendations.unshift('🚨 CRITICAL: Contact Support Team immediately')
    recommendations.push('Do not allow TLD submissions until all critical services are healthy')
  }
  
  return {
    allHealthy,
    services,
    criticalFailures,
    recommendations
  }
}

/**
 * Quick health check - just check if CrewAI service is responding
 */
export async function quickHealthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${getApiBase()}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000) // 3 second timeout
    })
    return response.ok
  } catch {
    return false
  }
}

/**
 * Block user operation if services are unhealthy
 */
export async function requireHealthyServices(operationName: string): Promise<void> {
  const health = await checkServiceHealth()
  
  if (!health.allHealthy) {
    const errorMessage = [
      `🚨 Cannot ${operationName} - Critical services unavailable:`,
      ...health.criticalFailures,
      '',
      'Recommendations:',
      ...health.recommendations
    ].join('\n')
    
    throw new Error(errorMessage)
  }
}