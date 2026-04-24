import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { assignSource, getPresets, pair } from "../client";
import { ApiError } from "../types";

describe("API client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function mockFetch(status: number, body: unknown) {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  describe("pair(code)", () => {
    it("sends POST to /api/v1/pair with code in body and returns token", async () => {
      const fetchMock = mockFetch(200, { token: "tok-xyz" });
      const result = await pair("123456");

      expect(fetchMock).toHaveBeenCalledOnce();
      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe("/api/v1/pair");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body as string)).toEqual({ code: "123456" });
      expect(result).toBe("tok-xyz");
    });

    it("does not attach Authorization header", async () => {
      const fetchMock = mockFetch(200, { token: "tok-xyz" });
      await pair("123456");
      const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      const headers = init.headers as Record<string, string>;
      expect(headers["Authorization"]).toBeUndefined();
    });
  });

  describe("assignSource(cellIndex, sourceId)", () => {
    it("sends PUT with cell index in URL, source_id in body, and Authorization header", async () => {
      const cellState = {
        index: 1,
        source_id: "src-1",
        status: "running",
        pid: 1234,
      };
      const fetchMock = mockFetch(200, cellState);
      await assignSource(1, "src-1", "tok-abc");

      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toContain("/api/v1/cells/1/source");
      expect(init.method).toBe("PUT");
      expect(JSON.parse(init.body as string)).toEqual({ source_id: "src-1" });
      const headers = init.headers as Record<string, string>;
      expect(headers["Authorization"]).toBe("Bearer tok-abc");
    });
  });

  describe("getPresets()", () => {
    it("sends GET to /api/v1/presets with Authorization header and returns preset array", async () => {
      const presets = [
        {
          id: "p1",
          name: "P1",
          layout_id: "single",
          cell_assignments: {},
          active_audio_cell: null,
        },
      ];
      const fetchMock = mockFetch(200, presets);
      const result = await getPresets("tok-abc");

      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toBe("/api/v1/presets");
      expect(init.method).toBeUndefined(); // GET — no explicit method
      const headers = init.headers as Record<string, string>;
      expect(headers["Authorization"]).toBe("Bearer tok-abc");
      expect(result).toEqual(presets);
    });
  });

  describe("error handling", () => {
    it("throws ApiError with parsed code when server returns non-2xx with error envelope", async () => {
      mockFetch(401, {
        error: { code: "INVALID_PAIRING_CODE", message: "Invalid code", details: {} },
      });

      await expect(pair("bad")).rejects.toSatisfy(
        (e: unknown) =>
          e instanceof ApiError && e.code === "INVALID_PAIRING_CODE"
      );
    });

    it("ApiError message contains server message", async () => {
      mockFetch(401, {
        error: {
          code: "INVALID_PAIRING_CODE",
          message: "Invalid or expired",
          details: {},
        },
      });

      let caught: ApiError | null = null;
      try {
        await pair("bad");
      } catch (e) {
        caught = e as ApiError;
      }
      expect(caught?.message).toBe("Invalid or expired");
    });
  });
});
