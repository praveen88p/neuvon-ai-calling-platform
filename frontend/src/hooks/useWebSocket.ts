import { useEffect, useRef, useState, useCallback } from "react";
import { API_BASE_URL } from "@/utils/api";
import type { LiveCallUpdate } from "@/types/api";

interface UseWebSocketOptions {
  onMessage?: (message: LiveCallUpdate) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket(path: string, options: UseWebSocketOptions = {}) {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<LiveCallUpdate | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    // Convert http(s) to ws(s)
    const wsBase = API_BASE_URL.replace(/^http/, "ws");
    const wsUrl = `${wsBase}${path}?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
        onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const data: LiveCallUpdate = JSON.parse(event.data);
          setLastMessage(data);
          onMessage?.(data);
        } catch {
          console.warn("WebSocket: invalid JSON received");
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        onClose?.();

        // Auto-reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          reconnectTimeout.current = setTimeout(connect, reconnectInterval);
        }
      };

      ws.onerror = (event) => {
        onError?.(event);
      };

      wsRef.current = ws;
    } catch {
      console.error("WebSocket: failed to connect");
    }
  }, [path, onMessage, onOpen, onClose, onError, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    reconnectAttempts.current = maxReconnectAttempts; // Prevent auto-reconnect
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, [maxReconnectAttempts]);

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "ping" }));
    }
  }, []);

  useEffect(() => {
    connect();
    // Send ping every 30s to keep alive
    const pingInterval = setInterval(sendPing, 30_000);

    return () => {
      clearInterval(pingInterval);
      disconnect();
    };
  }, [connect, disconnect, sendPing]);

  return { isConnected, lastMessage, disconnect, sendPing };
}
