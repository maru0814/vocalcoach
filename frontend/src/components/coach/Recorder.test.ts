import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Recorder } from "./Recorder";

/** MediaRecorder と getUserMedia の最小モック。録音内容は固定の Blob を返す。 */
class FakeMediaRecorder {
  static supported: string[] = ["audio/webm;codecs=opus"];
  static isTypeSupported(t: string) {
    return FakeMediaRecorder.supported.includes(t);
  }
  state: "inactive" | "recording" = "inactive";
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  constructor(public stream: unknown, public opts?: { mimeType?: string }) {}
  get mimeType() {
    return this.opts?.mimeType || "audio/webm";
  }
  start() {
    this.state = "recording";
  }
  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["chunk"], { type: "audio/webm" }) });
    this.onstop?.();
  }
}

const stoppedTracks: string[] = [];

function installMocks() {
  stoppedTracks.length = 0;
  vi.stubGlobal("MediaRecorder", FakeMediaRecorder as unknown as typeof MediaRecorder);
  vi.stubGlobal("navigator", {
    mediaDevices: {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{ stop: () => stoppedTracks.push("stopped") }],
      }),
    },
  });
}

beforeEach(installMocks);
afterEach(() => vi.unstubAllGlobals());

describe("Recorder", () => {
  it("start→stop で Blob と ext を返す", async () => {
    const r = new Recorder();
    await r.start();
    const res = await r.stop();
    expect(res.blob).toBeInstanceOf(Blob);
    expect(res.blob.size).toBeGreaterThan(0);
    expect(res.ext).toBe("webm");
  });

  it("stop でマイクのトラックを解放する", async () => {
    const r = new Recorder();
    await r.start();
    await r.stop();
    expect(stoppedTracks).toContain("stopped");
  });

  it("start していない状態で stop すると reject する", async () => {
    const r = new Recorder();
    await expect(r.stop()).rejects.toThrow("not recording");
  });

  it("webm 非対応なら mp4 にフォールバックする", async () => {
    FakeMediaRecorder.supported = ["audio/mp4"];
    const r = new Recorder();
    await r.start();
    const res = await r.stop();
    expect(res.ext).toBe("mp4");
    FakeMediaRecorder.supported = ["audio/webm;codecs=opus"];
  });

  it("cancel はトラックを解放し、録音を破棄する", async () => {
    const r = new Recorder();
    await r.start();
    r.cancel();
    expect(stoppedTracks).toContain("stopped");
  });
});
