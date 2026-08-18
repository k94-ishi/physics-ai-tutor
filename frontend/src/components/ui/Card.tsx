import { HTMLAttributes } from "react";

type CardProps = HTMLAttributes<HTMLDivElement>;

export default function Card({ className = "", ...props }: CardProps) {
    return (
        <div
            className={`rounded-lg border border-gray-200 bg-white p-4 shadow-sm ${className}`}
            {...props}
        />
    );
}
