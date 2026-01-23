import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useConfirmDialog } from "./useConfirmDialog";

describe("useConfirmDialog", () => {
  it("should initialize with default state", () => {
    const { result } = renderHook(() => useConfirmDialog());

    expect(result.current.isOpen).toBe(false);
    expect(result.current.dialogProps.isOpen).toBe(false);
  });

  it("should open dialog and resolve true on confirm", async () => {
    const { result } = renderHook(() => useConfirmDialog());

    let confirmPromise: Promise<boolean>;

    // Step 1: Trigger confirm
    act(() => {
      confirmPromise = result.current.confirm({
        title: "Test Title",
        message: "Test Message",
      });
    });

    // Verify state updated
    expect(result.current.isOpen).toBe(true);
    expect(result.current.dialogProps.title).toBe("Test Title");
    expect(result.current.dialogProps.message).toBe("Test Message");

    // Step 2: Simulate User Confirm
    await act(async () => {
      result.current.dialogProps.onConfirm();
    });

    // Verify Promise resolved to true
    // @ts-expect-error Typescript doesn't know confirmPromise is definitely assigned
    await expect(confirmPromise).resolves.toBe(true);

    // Verify dialog closed
    expect(result.current.isOpen).toBe(false);
  });

  it("should open dialog and resolve false on close/cancel", async () => {
    const { result } = renderHook(() => useConfirmDialog());

    let confirmPromise: Promise<boolean>;

    // Step 1: Trigger confirm
    act(() => {
      confirmPromise = result.current.confirm({
        title: "Delete",
        message: "Sure?",
      });
    });

    expect(result.current.isOpen).toBe(true);

    // Step 2: Simulate User Close/Cancel
    await act(async () => {
      result.current.dialogProps.onClose();
    });

    // Verify Promise resolved to false
    // @ts-expect-error Typescript doesn't know confirmPromise is definitely assigned
    await expect(confirmPromise).resolves.toBe(false);

    // Verify dialog closed
    expect(result.current.isOpen).toBe(false);
  });

  it("should reset state after confirm", async () => {
    const { result } = renderHook(() => useConfirmDialog());

    act(() => {
      result.current.confirm({
        title: "Test",
        message: "Message",
      });
    });

    await act(async () => {
      result.current.dialogProps.onConfirm();
    });

    expect(result.current.dialogProps.title).toBe("");
    expect(result.current.dialogProps.message).toBe("");
  });
});
