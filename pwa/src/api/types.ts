/** Typed shapes returned by the HomeView server API. */

export interface PairCodeResponse {
  code: string;
  expires_at: string;
}

export interface CellStatus {
  index: number;
  source_id: string | null;
  status: string;
  pid: number | null;
}

export interface AudioStatus {
  active_cell: number | null;
}

export interface ServerStatus {
  layout_id: string;
  cells: CellStatus[];
  audio: AudioStatus;
}

export interface Source {
  id: string;
  name: string;
  type: string;
  url: string;
  icon_url: string | null;
  requires_widevine: boolean;
  notes: string | null;
}

export interface LayoutCell {
  index: number;
  role: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Layout {
  id: string;
  name: string;
  gap_px: number;
  cells: LayoutCell[];
}

export interface Preset {
  id: string;
  name: string;
  layout_id: string;
  cell_assignments: Record<string, string | null>;
  active_audio_cell: number | null;
}

/** Parsed server error envelope. */
export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}
