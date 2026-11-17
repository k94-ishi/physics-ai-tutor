// The API client, one module per feature ([64]).
//
// Import from "@/lib/api" only: tests mock this module with vi.mock, and a
// direct import of a feature file would bypass the mock.

export { ApiError } from "@/lib/api/client";
export * from "@/lib/api/admin";
export * from "@/lib/api/ai";
export * from "@/lib/api/auth";
export * from "@/lib/api/concepts";
export * from "@/lib/api/questions";
export * from "@/lib/api/users";
