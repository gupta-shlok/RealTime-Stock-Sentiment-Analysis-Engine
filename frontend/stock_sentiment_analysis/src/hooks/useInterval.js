// useInterval.js
// Custom hook wrapping setInterval with visibility-pause behavior.
// Caller is responsible for in-flight guard (see StockDataContext isRefreshingRef).
import { useEffect, useRef } from 'react';

const useInterval = (callback, delay) => {
    const savedCallback = useRef(callback);
    const intervalRef = useRef(null);

    // Keep savedCallback current on every render to avoid stale closures.
    useEffect(() => {
        savedCallback.current = callback;
    }, [callback]);

    useEffect(() => {
        // null delay means "paused" — do nothing.
        if (delay === null) return;

        const startInterval = () => {
            if (intervalRef.current !== null) return; // already running
            intervalRef.current = setInterval(() => {
                savedCallback.current();
            }, delay);
        };

        const stopInterval = () => {
            if (intervalRef.current !== null) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };

        const handleVisibility = () => {
            if (document.visibilityState === 'hidden') {
                stopInterval();
            } else {
                startInterval();
            }
        };

        document.addEventListener('visibilitychange', handleVisibility);
        startInterval();

        return () => {
            stopInterval();
            document.removeEventListener('visibilitychange', handleVisibility);
        };
    }, [delay]);
};

export default useInterval;
