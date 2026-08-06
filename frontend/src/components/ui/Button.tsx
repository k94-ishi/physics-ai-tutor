import { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "danger";

const variantClasses: Record<ButtonVariant, string> = {
    primary:
        "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300",
    secondary:
        "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50",
    danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300",
};

export function buttonClassName(
    variant: ButtonVariant = "primary",
    className = ""
): string {
    return `inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${variantClasses[variant]} ${className}`;
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: ButtonVariant;
};

export default function Button({
    variant = "primary",
    className = "",
    ...props
}: ButtonProps) {
    return (
        <button className={buttonClassName(variant, className)} {...props} />
    );
}
