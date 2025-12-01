
import { AuditLog } from '../types';
import { CONFIG } from '../config';

// In-memory store for prototype. In production, this would be an immutable append-only database.
const auditStore: AuditLog[] = [];

export const logInteraction = (
  module: AuditLog['module'],
  action: string,
  latency_ms: number,
  status: 'success' | 'error',
  metadata?: object
) => {
  const log: AuditLog = {
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    user: 'WO Albert Kim', // Hardcoded for prototype context
    module,
    action,
    latency_ms,
    status,
    metadata: metadata ? JSON.stringify(metadata) : undefined
  };
  
  // Prepend to show newest first
  auditStore.unshift(log);
  
  // Keep store size manageable for demo
  if (auditStore.length > 100) auditStore.pop();

  // Send to Backend (Fire and forget)
  fetch(`${CONFIG.RAG.BASE_URL}/audit`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      timestamp: log.timestamp,
      module: log.module,
      action: log.action,
      duration_ms: log.latency_ms,
      status: log.status,
      metadata: metadata || {}
    })
  }).catch(err => console.warn("Failed to persist audit log to backend:", err));
  
  return log;
};

export const getLogs = (): AuditLog[] => {
  return [...auditStore];
};

export const getSystemStats = () => {
  const total = auditStore.length;
  const errors = auditStore.filter(l => l.status === 'error').length;
  const avgLatency = total > 0 
    ? Math.round(auditStore.reduce((acc, curr) => acc + curr.latency_ms, 0) / total) 
    : 0;

  return { total, errors, avgLatency };
};