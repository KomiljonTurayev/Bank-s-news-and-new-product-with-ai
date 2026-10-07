import { Component, type ComponentType, type ErrorInfo, type ReactNode } from "react";

import { ErrorFallback as DefaultFallback } from "@/shared/ui/error-fallback";

type FallbackProps = { error: unknown; reset: () => void };

type Props = {
  children: ReactNode;
  fallback?: ComponentType<FallbackProps>;
  onError?: (error: unknown, info: ErrorInfo) => void;
};

type State = { hasError: boolean; error: unknown };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: unknown): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    console.error("React render error:", error, info);
    this.props.onError?.(error, info);
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      const Fallback = this.props.fallback ?? DefaultFallback;
      return <Fallback error={this.state.error} reset={this.reset} />;
    }
    return this.props.children;
  }
}
