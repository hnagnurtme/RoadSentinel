import { useEffect, useMemo, useRef, useState } from "react";
import { deleteAlert as deleteAlertApi, listAlerts } from "@/api/alerts";
import { env } from "@/config/env";
import { Alert, AlertApiDto, mapAlertApiDto } from "@/types/alert";

interface UseAlertsFeedOptions {
    limit?: number;
    driverId?: string;
}

interface AlertCreatedEvent {
    event: "alert.created";
    data: AlertApiDto;
}

interface AlertDeletedEvent {
    event: "alert.deleted";
    data: AlertApiDto;
}

interface AlertEnvelopePayload {
    success: boolean;
    data: AlertApiDto;
}

const ALERTS_CACHE_TTL_MS = 5_000;
const ALERTS_FALLBACK_POLL_MS = 12_000;
const NEW_ALERT_HIGHLIGHT_MS = 15_000;
const alertsRequestCache = new Map<string, { expiresAt: number; data: Alert[] }>();
const inflightAlertsRequests = new Map<string, Promise<Alert[]>>();

function alertTimestamp ( alert: Alert ): number {
    if ( !alert.createdAt ) {
        return 0;
    }

    const timestamp = new Date( alert.createdAt ).getTime();
    return Number.isNaN( timestamp ) ? 0 : timestamp;
}

function sortAlertsNewestFirst ( alerts: Alert[] ): Alert[] {
    return [ ...alerts ].sort( ( a, b ) => alertTimestamp( b ) - alertTimestamp( a ) );
}

function queryKey ( limit: number, driverId?: string ): string {
    return `${ limit }:${ driverId ?? "all" }`;
}

async function getAlertsWithCoalescing (
    limit: number,
    driverId?: string,
    options?: { force?: boolean },
): Promise<Alert[]> {
    const key = queryKey( limit, driverId );
    const now = Date.now();
    const cached = alertsRequestCache.get( key );
    const force = options?.force ?? false;

    if ( !force && cached && cached.expiresAt > now ) {
        return cached.data;
    }

    const existingRequest = inflightAlertsRequests.get( key );
    if ( existingRequest ) {
        return existingRequest;
    }

    const request = listAlerts( limit, driverId )
        .then( ( data ) => {
            const sorted = sortAlertsNewestFirst( data ).slice( 0, limit );
            alertsRequestCache.set( key, {
                data: sorted,
                expiresAt: Date.now() + ALERTS_CACHE_TTL_MS,
            } );
            return sorted;
        } )
        .finally( () => {
            inflightAlertsRequests.delete( key );
        } );

    inflightAlertsRequests.set( key, request );
    return request;
}

function mergeLatestAlert ( existing: Alert[], incoming: Alert, limit: number ): Alert[] {
    const deduped = [ incoming, ...existing.filter( ( item ) => item.id !== incoming.id ) ];
    return sortAlertsNewestFirst( deduped ).slice( 0, limit );
}

export function useAlertsFeed ( options: UseAlertsFeedOptions = {} ) {
    const limit = options.limit ?? 20;
    const { driverId } = options;

    const [ alerts, setAlerts ] = useState<Alert[]>( [] );
    const [ newAlertIds, setNewAlertIds ] = useState<Set<string>>( new Set() );
    const [ isLoading, setIsLoading ] = useState( true );
    const [ errorMessage, setErrorMessage ] = useState<string | null>( null );
    const knownAlertIdsRef = useRef<Set<string>>( new Set() );
    const isHydratedRef = useRef( false );
    const newBadgeTimersRef = useRef<Map<string, number>>( new Map() );

    const markAlertAsNew = ( alertId: string ) => {
        setNewAlertIds( ( previous: Set<string> ) => {
            if ( previous.has( alertId ) ) {
                return previous;
            }

            const next = new Set( previous );
            next.add( alertId );
            return next;
        } );

        const existingTimer = newBadgeTimersRef.current.get( alertId );
        if ( existingTimer != null ) {
            window.clearTimeout( existingTimer );
        }

        const timerId = window.setTimeout( () => {
            setNewAlertIds( ( previous: Set<string> ) => {
                if ( !previous.has( alertId ) ) {
                    return previous;
                }

                const next = new Set( previous );
                next.delete( alertId );
                return next;
            } );
            newBadgeTimersRef.current.delete( alertId );
        }, NEW_ALERT_HIGHLIGHT_MS );

        newBadgeTimersRef.current.set( alertId, timerId );
    };

    const removeAlertFromState = ( alertId: string ) => {
        setAlerts( ( current: Alert[] ) => current.filter( ( item ) => item.id !== alertId ) );
        knownAlertIdsRef.current.delete( alertId );
        setNewAlertIds( ( previous: Set<string> ) => {
            if ( !previous.has( alertId ) ) {
                return previous;
            }
            const next = new Set( previous );
            next.delete( alertId );
            return next;
        } );
    };

    const deleteAlert = async ( alertId: string ) => {
        setErrorMessage( null );
        try {
            await deleteAlertApi( alertId );
            removeAlertFromState( alertId );
        } catch ( error ) {
            const message = error instanceof Error ? error.message : "Cannot delete alert";
            setErrorMessage( `Failed to delete alert: ${ message }` );
        }
    };

    const refreshFromApi = async ( force = false ) => {
        const latest = await getAlertsWithCoalescing( limit, driverId, { force } );
        if ( isHydratedRef.current ) {
            for ( const alert of latest ) {
                if ( !knownAlertIdsRef.current.has( alert.id ) ) {
                    knownAlertIdsRef.current.add( alert.id );
                    markAlertAsNew( alert.id );
                }
            }
        }
        setAlerts( latest );
    };

    useEffect( () => {
        let mounted = true;

        async function loadInitialAlerts () {
            setIsLoading( true );
            setErrorMessage( null );

            try {
                const initial = await getAlertsWithCoalescing( limit, driverId, { force: true } );
                if ( mounted ) {
                    setAlerts( initial );
                    knownAlertIdsRef.current = new Set( initial.map( ( alert ) => alert.id ) );
                    setNewAlertIds( new Set() );
                    isHydratedRef.current = true;
                }
            } catch ( error ) {
                if ( !mounted ) {
                    return;
                }

                const message = error instanceof Error ? error.message : "Cannot load alerts";
                setErrorMessage( `Failed to load alerts: ${ message }` );
            } finally {
                if ( mounted ) {
                    setIsLoading( false );
                }
            }
        }

        loadInitialAlerts();

        return () => {
            mounted = false;
            isHydratedRef.current = false;
            for ( const timerId of newBadgeTimersRef.current.values() ) {
                window.clearTimeout( timerId );
            }
            newBadgeTimersRef.current.clear();
        };
    }, [ limit, driverId ] );

    useEffect( () => {
        let ws: WebSocket | null = null;
        let heartbeatTimer: number | null = null;
        let reconnectTimer: number | null = null;
        let fallbackPollTimer: number | null = null;
        let manuallyClosed = false;
        let isTearingDown = false;

        const connect = () => {
            if ( isTearingDown ) {
                return;
            }

            ws = new WebSocket( env.wsAlertsUrl );

            ws.onopen = () => {
                if ( isTearingDown || manuallyClosed ) {
                    ws?.close( 1000, "component teardown" );
                    return;
                }

                // Clear stale stream errors when the socket is healthy again.
                setErrorMessage( ( previous: string | null ) =>
                    previous === "WebSocket connection error for alerts stream" ? null : previous,
                );

                // Re-sync once the socket is healthy to avoid needing a manual reload.
                void refreshFromApi( true );

                heartbeatTimer = window.setInterval( () => {
                    if ( ws?.readyState === WebSocket.OPEN ) {
                        ws.send( "ping" );
                    }
                }, 10_000 );
            };

            ws.onmessage = ( event ) => {
                if ( isTearingDown || manuallyClosed ) {
                    return;
                }

                try {
                    const payload = JSON.parse( event.data ) as AlertCreatedEvent | AlertDeletedEvent | AlertEnvelopePayload;

                    if ( "event" in payload && payload.event === "alert.created" ) {
                        const incoming = mapAlertApiDto( payload.data );
                        knownAlertIdsRef.current.add( incoming.id );
                        markAlertAsNew( incoming.id );
                        setAlerts( ( current: Alert[] ) => mergeLatestAlert( current, incoming, limit ) );
                        return;
                    }

                    if ( "event" in payload && payload.event === "alert.deleted" ) {
                        const incoming = mapAlertApiDto( payload.data );
                        removeAlertFromState( incoming.id );
                        return;
                    }

                    // Support envelope-style websocket payloads if backend wraps them in success/data.
                    if ( "success" in payload && payload.success && payload.data ) {
                        const incoming = mapAlertApiDto( payload.data );
                        knownAlertIdsRef.current.add( incoming.id );
                        markAlertAsNew( incoming.id );
                        setAlerts( ( current: Alert[] ) => mergeLatestAlert( current, incoming, limit ) );
                    }
                } catch {
                    setErrorMessage( "Received malformed WebSocket payload" );
                }
            };

            ws.onerror = () => {
                // Keep this quiet and let onclose decide whether to show a connection error.
            };

            ws.onclose = ( event ) => {
                if ( heartbeatTimer != null ) {
                    window.clearInterval( heartbeatTimer );
                    heartbeatTimer = null;
                }

                if ( manuallyClosed || isTearingDown ) {
                    return;
                }

                if ( !event.wasClean ) {
                    setErrorMessage( "WebSocket connection error for alerts stream" );
                }

                reconnectTimer = window.setTimeout( connect, 1_500 );
            };
        };

        connect();

        // Fallback sync in case websocket is dropped by network/proxy without visible UI error.
        fallbackPollTimer = window.setInterval( () => {
            void refreshFromApi( true ).catch( () => {
                // Keep silent, websocket/error state already handles user-facing feedback.
            } );
        }, ALERTS_FALLBACK_POLL_MS );

        return () => {
            manuallyClosed = true;
            isTearingDown = true;

            if ( heartbeatTimer != null ) {
                window.clearInterval( heartbeatTimer );
            }

            if ( reconnectTimer != null ) {
                window.clearTimeout( reconnectTimer );
            }

            if ( fallbackPollTimer != null ) {
                window.clearInterval( fallbackPollTimer );
            }

            if ( ws ) {
                ws.onopen = null;
                ws.onmessage = null;
                ws.onerror = null;
                ws.onclose = null;

                if ( ws.readyState === WebSocket.OPEN ) {
                    ws.close( 1000, "component teardown" );
                }
            }
        };
    }, [ limit, driverId ] );

    return useMemo(
        () => ( {
            alerts,
            newAlertIds,
            isLoading,
            errorMessage,
            deleteAlert,
        } ),
        [ alerts, newAlertIds, isLoading, errorMessage ],
    );
}
