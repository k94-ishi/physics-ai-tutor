import { SelectHTMLAttributes } from "react";

type Option = {
    value: string;
    label: string;
};

type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
    label: string;
    id: string;
    error?: string;
    options: Option[];
};

export default function SelectField({
    label,
    id,
    error,
    required,
    className = "",
    options,
    ...props
}: SelectFieldProps) {
    return (
        <div className="flex flex-col gap-1.5">
            <label htmlFor={id} className="text-sm font-medium text-gray-700">
                {label}
                {required && (
                    <span className="ml-1 text-red-600" aria-hidden="true">
                        *
                    </span>
                )}
            </label>

            <select
                id={id}
                required={required}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? `${id}-error` : undefined}
                className={`rounded-md border bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-1 ${
                    error
                        ? "border-red-400 focus:border-red-500 focus:ring-red-500"
                        : "border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                } ${className}`}
                {...props}
            >
                {options.map((option) => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>

            {error && (
                <p id={`${id}-error`} className="text-sm text-red-600">
                    {error}
                </p>
            )}
        </div>
    );
}
