type LoadingStateProps = {
    label?: string;
};

export default function LoadingState({
    label = "読み込み中...",
}: LoadingStateProps) {
    return (
        <div
            role="status"
            className="flex items-center gap-2 py-8 text-sm text-gray-500"
        >
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
            {label}
        </div>
    );
}
