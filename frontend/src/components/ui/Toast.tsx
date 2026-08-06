"use client";

import { useEffect, useState } from "react";

type ToastType = "success" | "error";

type ToastItem = {
    id: number;
    message: string;
    type: ToastType;
};

type Listener = (toasts: ToastItem[]) => void;

let toasts: ToastItem[] = [];
let listeners: Listener[] = [];
let nextId = 0;

function emit() {
    listeners.forEach((listener) => listener(toasts));
}

export function showToast(message: string, type: ToastType = "success") {
    const id = nextId++;
    toasts = [...toasts, { id, message, type }];
    emit();

    setTimeout(() => {
        toasts = toasts.filter((toast) => toast.id !== id);
        emit();
    }, 4000);
}

export default function Toaster() {
    const [items, setItems] = useState<ToastItem[]>([]);

    useEffect(() => {
        listeners.push(setItems);
        return () => {
            listeners = listeners.filter((listener) => listener !== setItems);
        };
    }, []);

    if (items.length === 0) {
        return null;
    }

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
            {items.map((item) => (
                <div
                    key={item.id}
                    role="status"
                    className={`rounded-md px-4 py-3 text-sm text-white shadow-lg ${
                        item.type === "error" ? "bg-red-600" : "bg-gray-900"
                    }`}
                >
                    {item.message}
                </div>
            ))}
        </div>
    );
}
