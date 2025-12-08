import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
    children: ReactNode
}

interface State {
    hasError: boolean
    error: Error | null
    errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
        errorInfo: null
    }

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null }
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Uncaught error:", error, errorInfo)
        this.setState({ error, errorInfo })
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-red-900 text-white p-8">
                    <div className="max-w-2xl w-full bg-black/50 p-8 rounded-xl border border-red-500">
                        <h1 className="text-3xl font-bold mb-4">Something went wrong</h1>
                        <div className="bg-black p-4 rounded overflow-auto max-h-96 font-mono text-sm">
                            <p className="text-red-400 font-bold mb-2">{this.state.error?.toString()}</p>
                            <pre className="text-gray-400">{this.state.errorInfo?.componentStack}</pre>
                        </div>
                        <button
                            onClick={() => window.location.reload()}
                            className="mt-6 px-6 py-2 bg-white text-black rounded hover:bg-gray-200 transition-colors"
                        >
                            Reload Page
                        </button>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}
