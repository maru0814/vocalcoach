import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const { getVoiceTypeStats } = vi.hoisted(() => ({ getVoiceTypeStats: vi.fn() }));
vi.mock("@/lib/api", () => ({ getVoiceTypeStats }));

import { VoiceTypeStats } from "./VoiceTypeStats";

beforeEach(() => getVoiceTypeStats.mockReset());

describe("VoiceTypeStats", () => {
  it("件数が閾値(15)未満なら何も表示しない", async () => {
    getVoiceTypeStats.mockResolvedValue({ total: 10, distribution: [], top: null });
    const { container } = render(<VoiceTypeStats />);
    await waitFor(() => expect(getVoiceTypeStats).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });

  it("十分な件数なら累計と人気タイプを表示する", async () => {
    getVoiceTypeStats.mockResolvedValue({
      total: 1234,
      distribution: [],
      top: { id: "rock", name: "Rock Voice", count: 500 },
    });
    render(<VoiceTypeStats />);
    expect(await screen.findByText("1,234")).toBeInTheDocument();   // toLocaleString
    expect(screen.getByText("Rock Voice")).toBeInTheDocument();
  });

  it("top が無くても累計だけは表示する", async () => {
    getVoiceTypeStats.mockResolvedValue({ total: 100, distribution: [], top: null });
    render(<VoiceTypeStats />);
    expect(await screen.findByText("100")).toBeInTheDocument();
    expect(screen.queryByText(/いま人気は/)).not.toBeInTheDocument();
  });
});
