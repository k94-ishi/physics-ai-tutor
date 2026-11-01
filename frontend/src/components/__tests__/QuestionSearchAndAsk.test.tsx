import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const navigation = {
    params: new URLSearchParams(),
    replace: vi.fn(),
    push: vi.fn(),
};

const stableRouter = {
    push: (...args: unknown[]) => navigation.push(...args),
    replace: (...args: unknown[]) => navigation.replace(...args),
};

vi.mock("next/navigation", () => ({
    // Next's useRouter returns a stable object; the mock must too, or
    // every re-render would re-create callbacks that depend on it.
    useRouter: () => stableRouter,
    usePathname: () => "/",
    useSearchParams: () => navigation.params,
}));

vi.mock("@/lib/api", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@/lib/api")>();
    return {
        ...actual,
        searchQuestions: vi.fn(),
        fetchQuestionByExactText: vi.fn(),
        askAi: vi.fn(),
    };
});

import * as api from "@/lib/api";
import QuestionSearchAndAsk from "@/components/QuestionSearchAndAsk";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";

const mocked = vi.mocked(api);

const RESULT = {
    id: 7,
    question: "斜方投射とは？",
    answer: "斜めに投げ出した物体の運動です。",
    language: "ja" as const,
    distance: 0.2,
};

function renderSearch() {
    render(
        <LanguageProvider>
            <QuestionSearchAndAsk />
        </LanguageProvider>
    );
}

beforeEach(() => {
    navigation.params = new URLSearchParams();
    navigation.replace.mockReset();
    navigation.push.mockReset();
    mocked.searchQuestions.mockReset().mockResolvedValue([RESULT]);
    mocked.fetchQuestionByExactText
        .mockReset()
        .mockRejectedValue(new api.ApiError(404, "not found"));
});

describe("?similar= in the URL", () => {
    it("submitting writes the query to the URL; typing alone does not", async () => {
        const user = userEvent.setup();
        renderSearch();

        const input = screen.getByRole("textbox");
        await user.type(input, "斜方投射の運動について");
        expect(navigation.replace).not.toHaveBeenCalled();

        await user.click(screen.getByRole("button", { name: "検索" }));

        await waitFor(() => expect(mocked.searchQuestions).toHaveBeenCalledTimes(1));
        expect(navigation.replace).toHaveBeenCalledWith(
            `/?similar=${encodeURIComponent("斜方投射の運動について")}`,
            { scroll: false }
        );
    });

    it("restores the search from the URL exactly once, without any click", async () => {
        navigation.params = new URLSearchParams("similar=斜方投射の運動について");
        renderSearch();

        expect(screen.getByRole("textbox")).toHaveValue("斜方投射の運動について");
        await screen.findByText("斜方投射とは？");
        expect(mocked.searchQuestions).toHaveBeenCalledTimes(1);
    });

    it("a restored search never bounces through the exact-match redirect", async () => {
        // Otherwise pressing back after an exact match would immediately
        // push the user forward again - a back-button trap.
        navigation.params = new URLSearchParams("similar=斜方投射の運動について");
        mocked.fetchQuestionByExactText.mockResolvedValue({ id: 7 } as never);
        renderSearch();

        await screen.findByText("斜方投射とは？");
        expect(mocked.fetchQuestionByExactText).not.toHaveBeenCalled();
        expect(navigation.push).not.toHaveBeenCalled();
    });

    it("emptying the box clears the parameter without spending a search", async () => {
        navigation.params = new URLSearchParams("similar=前の検索");
        const user = userEvent.setup();
        renderSearch();

        await screen.findByText("斜方投射とは？");
        await user.clear(screen.getByRole("textbox"));

        expect(navigation.replace).toHaveBeenCalledWith("/", { scroll: false });
        // Clearing is a URL change only; no search is spent on it.
        expect(mocked.searchQuestions).toHaveBeenCalledTimes(1);
    });
});
