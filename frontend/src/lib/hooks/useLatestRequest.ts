import { useMemo, useRef } from "react";

export type LatestRequest = {
    /** Start a request; the returned check is true until a newer one starts. */
    begin: () => () => boolean;
    /** Make every request started so far stale. */
    cancel: () => void;
};

/**
 * Drop responses that arrive after a newer request started ([63]).
 *
 * Replaces the hand-copied `++ref.current` / `id === ref.current` guard;
 * the returned object is stable across renders.
 */
export function useLatestRequest(): LatestRequest {
    const latest = useRef(0);

    return useMemo(
        () => ({
            begin: () => {
                const id = ++latest.current;
                return () => id === latest.current;
            },
            cancel: () => {
                latest.current += 1;
            },
        }),
        []
    );
}
