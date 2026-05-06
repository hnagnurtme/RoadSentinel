import { useEffect, useState, useMemo } from "react";
import { Clock, ChevronDown, ChevronUp } from "lucide-react";
import { useAuth } from "@/auth/AuthContext";
import { DriverHeader } from "@/components/DriverHeader";
import { getDrivingSessions, DrivingSession } from "@/api/users";

export function DriverSessions () {
    const { user } = useAuth();
    const [ sessions, setSessions ] = useState<DrivingSession[]>( [] );
    const [ loading, setLoading ] = useState( true );
    const [ expandedDates, setExpandedDates ] = useState<Record<string, boolean>>( {} );

    useEffect( () => {
        if ( !user ) return;
        getDrivingSessions( user.id )
            .then( setSessions )
            .catch( console.error )
            .finally( () => setLoading( false ) );
    }, [ user ] );

    const groupedSessions = useMemo( () => {
        const groups: Record<string, { date: string, sessions: DrivingSession[], totalMs: number }> = {};

        sessions.forEach( s => {
            const d = new Date( s.started_at );
            const dateStr = d.toLocaleDateString( 'en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' } );
            if ( !groups[ dateStr ] ) {
                groups[ dateStr ] = { date: dateStr, sessions: [], totalMs: 0 };
            }

            groups[ dateStr ].sessions.push( s );

            if ( s.ended_at ) {
                const start = new Date( s.started_at ).getTime();
                const end = new Date( s.ended_at ).getTime();
                groups[ dateStr ].totalMs += ( end - start );
            }
        } );

        return Object.values( groups ).sort( ( a, b ) => {
            const [ d1, m1, y1 ] = a.date.split( '/' );
            const [ d2, m2, y2 ] = b.date.split( '/' );
            const date1 = new Date( Number( y1 ), Number( m1 ) - 1, Number( d1 ) ).getTime();
            const date2 = new Date( Number( y2 ), Number( m2 ) - 1, Number( d2 ) ).getTime();
            return date2 - date1;
        } );
    }, [ sessions ] );

    const toggleExpand = ( date: string ) => {
        setExpandedDates( prev => ( { ...prev, [ date ]: !prev[ date ] } ) );
    };

    const formatDuration = ( ms: number ) => {
        if ( ms === 0 ) return "—";
        const hours = Math.floor( ms / ( 1000 * 60 * 60 ) );
        const minutes = Math.floor( ( ms % ( 1000 * 60 * 60 ) ) / ( 1000 * 60 ) );
        return `${ hours }h ${ minutes }m`;
    };

    return (
        <>
            <DriverHeader />
            <div className="p-10 max-w-[1200px] space-y-8">
                <div>
                    <span className="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-on-surface-variant block mb-2">
                        Timekeeping
                    </span>
                    <h2 className="text-3xl font-black text-primary tracking-tight">Driving Sessions</h2>
                    <p className="text-secondary text-sm mt-1 font-medium">Your historical driving records, grouped by date.</p>
                </div>

                { loading ? (
                    <p className="text-secondary text-sm">Loading sessions...</p>
                ) : groupedSessions.length === 0 ? (
                    <div className="bg-surface-container-lowest p-8 rounded-xl ring-1 ring-outline-variant/15 text-center shadow-sm">
                        <Clock className="w-12 h-12 text-outline mx-auto mb-3" />
                        <p className="text-secondary font-medium">No driving sessions found.</p>
                    </div>
                ) : (
                    <div className="bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/15 shadow-sm overflow-hidden flex flex-col divide-y divide-surface-container-high">
                        { groupedSessions.map( group => {
                            const isExpanded = expandedDates[ group.date ];
                            return (
                                <div key={ group.date } className="flex flex-col">
                                    <div
                                        onClick={ () => toggleExpand( group.date ) }
                                        className="p-6 flex items-center justify-between hover:bg-surface-container-low/50 cursor-pointer transition-colors"
                                    >
                                        <div className="flex items-center gap-6">
                                            <div className="flex flex-col">
                                                <span className="text-sm font-bold text-secondary uppercase tracking-widest mb-1">Date</span>
                                                <span className="text-xl font-black text-primary">{ group.date }</span>
                                            </div>
                                            <div className="h-10 w-px bg-surface-container-highest mx-2 hidden sm:block" />
                                            <div className="flex flex-col hidden sm:flex">
                                                <span className="text-xs font-bold text-secondary uppercase tracking-widest mb-1">Check-ins</span>
                                                <span className="text-lg font-semibold text-on-surface">{ group.sessions.length } sessions</span>
                                            </div>
                                            <div className="h-10 w-px bg-surface-container-highest mx-2 hidden md:block" />
                                            <div className="flex flex-col hidden md:flex">
                                                <span className="text-xs font-bold text-secondary uppercase tracking-widest mb-1">Total Time</span>
                                                <span className="text-lg font-semibold text-emerald-600">{ formatDuration( group.totalMs ) }</span>
                                            </div>
                                        </div>
                                        <button className="p-2 hover:bg-surface-container-high rounded-full transition-colors">
                                            { isExpanded ? <ChevronUp className="w-5 h-5 text-secondary" /> : <ChevronDown className="w-5 h-5 text-secondary" /> }
                                        </button>
                                    </div>

                                    { isExpanded && (
                                        <div className="bg-surface-container-low/30 border-t border-surface-container-high p-4 flex flex-col gap-2">
                                            { group.sessions.map( ( session, idx ) => (
                                                <div key={ session.id } className="flex items-center justify-between p-4 bg-surface-container-lowest rounded-lg border border-surface-container-high shadow-sm">
                                                    <div className="flex items-center gap-4">
                                                        <div className="w-8 h-8 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center text-xs">
                                                            { group.sessions.length - idx }
                                                        </div>
                                                        <div className="flex flex-col">
                                                            <span className="text-sm font-bold text-on-surface">
                                                                { new Date( session.started_at ).toLocaleTimeString( 'en-GB', { hour: '2-digit', minute: '2-digit' } ) }
                                                                { " " }—{ " " }
                                                                { session.ended_at ? new Date( session.ended_at ).toLocaleTimeString( 'en-GB', { hour: '2-digit', minute: '2-digit' } ) : "Active" }
                                                            </span>
                                                            <span className="font-mono text-[10px] text-secondary mt-1">ID: { session.id }</span>
                                                        </div>
                                                    </div>
                                                    { session.status === "ACTIVE" ? (
                                                        <span className="text-[10px] font-black text-emerald-600 bg-emerald-500/20 px-2 py-1 rounded tracking-widest uppercase">ACTIVE</span>
                                                    ) : (
                                                        <span className="text-[10px] font-black text-secondary bg-surface-container-highest px-2 py-1 rounded tracking-widest uppercase">COMPLETED</span>
                                                    ) }
                                                </div>
                                            ) ) }
                                        </div>
                                    ) }
                                </div>
                            );
                        } ) }
                    </div>
                ) }
            </div>
        </>
    );
}
