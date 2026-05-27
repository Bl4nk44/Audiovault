import { describe, it, expect, vi, beforeEach } from "vitest";
import { playlistsApi } from "./playlists";
import api from "../services/api";

vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("playlistsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getById", () => {
    it("should fetch playlist from deezer endpoint by default", async () => {
      const mockPlaylist = {
        id: "pl-1",
        title: "Test Playlist",
        tracks: [],
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockPlaylist });

      const result = await playlistsApi.getById("pl-1");

      expect(api.get).toHaveBeenCalledWith("/browse/playlist/deezer/pl-1");
      expect(result).toEqual(mockPlaylist);
    });

    it("should fetch playlist from spotify when source is spotify", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: {} });

      await playlistsApi.getById("pl-1", "spotify");

      expect(api.get).toHaveBeenCalledWith("/browse/playlist/spotify/pl-1");
    });

    it("should fetch playlist from youtube when source is youtube", async () => {
      vi.mocked(api.get).mockResolvedValue({ data: {} });

      await playlistsApi.getById("yt-pl-123", "youtube");

      expect(api.get).toHaveBeenCalledWith("/youtube/playlist/yt-pl-123");
    });
  });

  describe("CRUD operations", () => {
    it("should create a playlist", async () => {
      const data = { name: "New Playlist", description: "Desc" };
      vi.mocked(api.post).mockResolvedValue({ data: { id: "1", ...data } });

      const result = await playlistsApi.create(data as any);

      expect(api.post).toHaveBeenCalledWith("/playlists/", data);
      expect(result.id).toBe("1");
    });

    it("should get all playlists and map name to title", async () => {
      const mockPlaylists = [{ id: "1", name: "My List" }];
      vi.mocked(api.get).mockResolvedValue({ data: mockPlaylists });

      const result = await playlistsApi.getAll();

      expect(api.get).toHaveBeenCalledWith("/playlists/");
      expect(result[0].title).toBe("My List");
      expect(result[0].source).toBe("local");
    });

    it("should delete a playlist", async () => {
      vi.mocked(api.delete).mockResolvedValue({});
      await playlistsApi.delete("1");
      expect(api.delete).toHaveBeenCalledWith("/playlists/1");
    });
  });

  describe("Track management", () => {
    it("should add tracks to a playlist", async () => {
      const trackIds = ["t1", "t2"];
      vi.mocked(api.post).mockResolvedValue({ data: { added_count: 2 } });

      const result = await playlistsApi.addTracks("pl-1", trackIds);

      expect(api.post).toHaveBeenCalledWith("/playlists/pl-1/tracks", { track_ids: trackIds });
      expect(result.added_count).toBe(2);
    });

    it("should remove tracks from a playlist", async () => {
      const trackIds = ["t1"];
      vi.mocked(api.delete).mockResolvedValue({ data: { removed: 1 } });

      await playlistsApi.removeTracks("pl-1", trackIds);

      expect(api.delete).toHaveBeenCalledWith("/playlists/pl-1/tracks", { data: { track_ids: trackIds } });
    });
  });

  describe("exportAsJson", () => {
    it("should trigger a file download", async () => {
      const mockBlob = new Blob(['{"test": true}'], { type: "application/json" });
      vi.mocked(api.get).mockResolvedValue({ data: mockBlob });

      // Mock DOM methods
      const mockLink = {
        href: "",
        download: "",
        click: vi.fn(),
        remove: vi.fn(),
      };
      const createElementSpy = vi.spyOn(document, "createElement").mockReturnValue(mockLink as any);
      const appendChildSpy = vi.spyOn(document.body, "appendChild").mockImplementation(() => mockLink as any);
      vi.stubGlobal("URL", {
        createObjectURL: vi.fn(() => "blob:url"),
        revokeObjectURL: vi.fn(),
      });

      await playlistsApi.exportAsJson("pl-1", "My Playlist!");

      expect(api.get).toHaveBeenCalledWith("/playlists/pl-1/export", { responseType: "blob" });
      expect(mockLink.download).toBe("My Playlist_export.json");
      expect(mockLink.click).toHaveBeenCalled();

      createElementSpy.mockRestore();
      appendChildSpy.mockRestore();
    });
  });
});
