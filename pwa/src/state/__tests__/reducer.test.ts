import { describe, expect, it } from "vitest";
import { reducer } from "../reducer";
import { initialState } from "../types";

describe("reducer", () => {
  it("SET_SERVER stores serverUrl, token, sets pairPhase to paired", () => {
    const next = reducer(initialState, {
      type: "SET_SERVER",
      payload: { serverUrl: "localhost:8000", token: "tok-abc" },
    });
    expect(next.serverUrl).toBe("localhost:8000");
    expect(next.token).toBe("tok-abc");
    expect(next.pairPhase).toBe("paired");
  });

  it("CLEAR_SERVER resets all fields to initial values", () => {
    const modified = reducer(initialState, {
      type: "SET_SERVER",
      payload: { serverUrl: "localhost:8000", token: "tok-abc" },
    });
    const next = reducer(modified, { type: "CLEAR_SERVER" });
    expect(next).toEqual(initialState);
  });

  it("SET_STATUS replaces status without wiping other fields", () => {
    const withSources = { ...initialState, sources: [] };
    const status = {
      layout_id: "single",
      cells: [],
      audio: { active_cell: null },
    };
    const next = reducer(withSources, { type: "SET_STATUS", payload: status });
    expect(next.status).toEqual(status);
    expect(next.sources).toEqual([]);
  });

  it("SET_SOURCES stores provided source list", () => {
    const sources = [
      {
        id: "s1",
        name: "S1",
        type: "url",
        url: "https://example.com",
        icon_url: null,
        requires_widevine: false,
        notes: null,
      },
    ];
    const next = reducer(initialState, { type: "SET_SOURCES", payload: sources });
    expect(next.sources).toEqual(sources);
  });

  it("SET_LAYOUTS stores provided layout list", () => {
    const layouts = [{ id: "single", name: "Single", gap_px: 4, cells: [] }];
    const next = reducer(initialState, { type: "SET_LAYOUTS", payload: layouts });
    expect(next.layouts).toEqual(layouts);
  });

  it("SET_PRESETS stores provided preset list", () => {
    const presets = [
      {
        id: "p1",
        name: "P1",
        layout_id: "single",
        cell_assignments: {},
        active_audio_cell: null,
      },
    ];
    const next = reducer(initialState, { type: "SET_PRESETS", payload: presets });
    expect(next.presets).toEqual(presets);
  });

  it("SET_WS_CONNECTED sets wsConnected to true", () => {
    const next = reducer(initialState, { type: "SET_WS_CONNECTED", payload: true });
    expect(next.wsConnected).toBe(true);
  });

  it("SET_WS_CONNECTED sets wsConnected to false", () => {
    const connected = { ...initialState, wsConnected: true };
    const next = reducer(connected, { type: "SET_WS_CONNECTED", payload: false });
    expect(next.wsConnected).toBe(false);
  });

  it("SET_INTERACTIVE sets interactiveCell to provided value", () => {
    const next = reducer(initialState, { type: "SET_INTERACTIVE", payload: 2 });
    expect(next.interactiveCell).toBe(2);
  });

  it("CLEAR_INTERACTIVE sets interactiveCell to null", () => {
    const withInteractive = { ...initialState, interactiveCell: 2 };
    const next = reducer(withInteractive, { type: "CLEAR_INTERACTIVE" });
    expect(next.interactiveCell).toBeNull();
  });

  it("returns input state unchanged for unrecognized action type", () => {
    // @ts-expect-error intentional unknown action
    const next = reducer(initialState, { type: "UNKNOWN_ACTION" });
    expect(next).toBe(initialState);
  });

  it("never mutates input state", () => {
    const before = { ...initialState };
    reducer(initialState, { type: "SET_WS_CONNECTED", payload: true });
    expect(initialState).toEqual(before);
  });
});
