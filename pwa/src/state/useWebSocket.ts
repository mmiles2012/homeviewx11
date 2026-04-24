import { useCallback, useEffect, useRef } from "react";
import { getStatus } from "../api/client";
import { Action } from "./types";

const BACKOFF_INITIAL = 1000;
const BACKOFF_MULTIPLIER = 2;
const BACKOFF_MAX = 30_000;

export function useWebSocket(
  serverUrl: string | null,
  token: string | null,
  dispatch: React.Dispatch<Action>
): void {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffRef = useRef(BACKOFF_INITIAL);
  const unmountedRef = useRef(false);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const closeWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.onopen = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!serverUrl || !token || unmountedRef.current) return;

    closeWs();

    const wsUrl = `ws://${serverUrl}/ws/control?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = async () => {
      if (unmountedRef.current) return;
      backoffRef.current = BACKOFF_INITIAL;
      dispatch({ type: "SET_WS_CONNECTED", payload: true });
      try {
        const status = await getStatus(token);
        if (!unmountedRef.current) {
          dispatch({ type: "SET_STATUS", payload: status });
        }
      } catch {
        // best-effort — WS will deliver state events anyway
      }
    };

    ws.onmessage = async (event: MessageEvent) => {
      if (unmountedRef.current) return;
      try {
        const msg = JSON.parse(event.data as string) as {
          type: string;
          data: unknown;
        };
        if (msg.type === "state.updated") {
          dispatch({
            type: "SET_STATUS",
            payload: msg.data as Parameters<typeof dispatch>[0] extends {
              type: "SET_STATUS";
              payload: infer P;
            }
              ? P
              : never,
          });
        } else if (msg.type === "cell.health") {
          // Refresh full status on any health event
          try {
            const status = await getStatus(token);
            if (!unmountedRef.current) {
              dispatch({ type: "SET_STATUS", payload: status });
            }
          } catch {
            // best-effort
          }
        }
      } catch {
        // malformed message — ignore
      }
    };

    const scheduleReconnect = () => {
      if (unmountedRef.current) return;
      clearReconnectTimer();
      const delay = backoffRef.current;
      backoffRef.current = Math.min(
        backoffRef.current * BACKOFF_MULTIPLIER,
        BACKOFF_MAX
      );
      reconnectTimerRef.current = setTimeout(() => {
        if (!unmountedRef.current) connect();
      }, delay);
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      dispatch({ type: "SET_WS_CONNECTED", payload: false });
      scheduleReconnect();
    };

    ws.onerror = () => {
      if (unmountedRef.current) return;
      dispatch({ type: "SET_WS_CONNECTED", payload: false });
    };
  }, [serverUrl, token, dispatch, clearReconnectTimer, closeWs]);

  useEffect(() => {
    unmountedRef.current = false;

    if (serverUrl && token) {
      connect();
    }

    return () => {
      unmountedRef.current = true;
      clearReconnectTimer();
      closeWs();
    };
  }, [serverUrl, token, connect, clearReconnectTimer, closeWs]);
}
