import { Action, AppState, initialState } from "./types";

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_SERVER":
      return {
        ...state,
        serverUrl: action.payload.serverUrl,
        token: action.payload.token,
        pairPhase: "paired",
      };

    case "CLEAR_SERVER":
      return { ...initialState };

    case "SET_STATUS":
      return { ...state, status: action.payload };

    case "SET_SOURCES":
      return { ...state, sources: action.payload };

    case "SET_LAYOUTS":
      return { ...state, layouts: action.payload };

    case "SET_PRESETS":
      return { ...state, presets: action.payload };

    case "SET_WS_CONNECTED":
      return { ...state, wsConnected: action.payload };

    case "SET_INTERACTIVE":
      return { ...state, interactiveCell: action.payload };

    case "CLEAR_INTERACTIVE":
      return { ...state, interactiveCell: null };

    default:
      return state;
  }
}
