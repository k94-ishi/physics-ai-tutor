import { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "danger";
export type ButtonSize = "sm" | "md";

const variantClasses: Record<ButtonVariant, string> = {
    primary:
        "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300",
    secondary:
        "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50",
    danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300",
};

const sizeClasses: Record<ButtonSize, string> = {
    md: "px-4 py-2 text-sm",
    sm: "px-2 py-1 text-sm",
};

export function buttonClassName(
    variant: ButtonVariant = "primary",
    className = "",
    size: ButtonSize = "md"
): string {
    return `inline-flex items-center justify-center rounded-md ${sizeClasses[size]} font-medium transition-colors disabled:cursor-not-allowed ${variantClasses[variant]} ${className}`;
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant;
    size?: ButtonSize;
};

export default function Button({
    variant = "primary",
    size = "md",
    className = "",
    ...props
}: ButtonProps) {
    return (
        <button
            className={buttonClassName(variant, className, size)}
            {...props}
        />
    );
}
