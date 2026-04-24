import type { Layout, Preset, ServerStatus, Source } from "../api/types";

// Re-export server types for convenience
export type { CellStatus, ServerStatus, Source, Layout, Preset } from "../api/types";

// ---------------------------------------------------------------------------
// App state
// ---------------------------------------------------------------------------

export type PairPhase = "unpaired" | "pairing" | "paired";

export interface AppState {
  serverUrl: string | null;
  token: string | null;
  status: ServerStatus | null;
  sources: Source[] | null;
  layouts: Layout[] | null;
  presets: Preset[] | null;
  wsConnected: boolean;
  interactiveCell: number | null;
  pairPhase: PairPhase;
}

export const initialState: AppState = {
  serverUrl: null,
  token: null,
  status: null,
  sources: null,
  layouts: null,
  presets: null,
  wsConnected: false,
  interactiveCell: null,
  pairPhase: "unpaired",
};

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export type Action =
  | { type: "SET_SERVER"; payload: { serverUrl: string; token: string } }
  | { type: "CLEAR_SERVER" }
  | { type: "SET_STATUS"; payload: ServerStatus }
  | { type: "SET_SOURCES"; payload: Source[] }
  | { type: "SET_LAYOUTS"; payload: Layout[] }
  | { type: "SET_PRESETS"; payload: Preset[] }
  | { type: "SET_WS_CONNECTED"; payload: boolean }
  | { type: "SET_INTERACTIVE"; payload: number }
  | { type: "CLEAR_INTERACTIVE" };
