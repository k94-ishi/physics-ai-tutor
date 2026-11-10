"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

/** List state kept in the URL; pass `defaults` as a module constant, values equal to them are omitted. */
export function useQueryState<T extends Record<string, string>>(
    defaults: T
) {
    const router = useRouter();
    const pathname = usePathname();
    const searchParams = useSearchParams();

    const state = useMemo(() => {
        const result = { ...defaults };
        for (const key of Object.keys(defaults) as (keyof T)[]) {
            const value = searchParams.get(key as string);
            if (value !== null) {
                result[key] = value as T[keyof T];
            }
        }
        return result;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [searchParams]);

    const setState = useCallback(
        (patch: Partial<T>) => {
            const params = new URLSearchParams(searchParams.toString());
            for (const key of Object.keys(patch) as (keyof T)[]) {
                const value = patch[key];
                if (value === undefined || value === defaults[key]) {
                    params.delete(key as string);
                } else {
                    params.set(key as string, value);
                }
            }
            const query = params.toString();
            router.replace(query ? `${pathname}?${query}` : pathname, {
                scroll: false,
            });
        },
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [router, pathname, searchParams]
    );

    return [state, setState] as const;
}
