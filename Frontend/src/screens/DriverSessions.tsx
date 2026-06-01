import { useEffect, useState, useMemo } from "react";
import { Clock, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, AlertTriangle, LayoutList, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/auth/AuthContext";
import { DriverHeader } from "@/components/DriverHeader";
import { getDrivingSessions, DrivingSession } from "@/api/users";
import { useLanguage } from "@/i18n/LanguageContext";
import { listAlerts } from "@/api/alerts";
import type { Alert } from "@/types/alert";


export function DriverSessions () {
    const { user } = useAuth();
    const { t, language } = useLanguage();
    const [ sessions, setSessions ] = useState<DrivingSession[]>( [] );
    const [ alerts, setAlerts ] = useState<Alert[]>( [] );
    const [ loading, setLoading ] = useState( true );
    const [ expandedDates, setExpandedDates ] = useState<Record<string, boolean>>( {} );
    const [ viewMode, setViewMode ] = useState<"list" | "calendar">( "list" );
    const [ currentDate, setCurrentDate ] = useState( new Date() );

    useEffect( () => {
        if ( !user ) return;
        setLoading( true );
        Promise.all([
            getDrivingSessions( user.id ),
            listAlerts( 100 )
        ])
            .then( ([ sessionRows, alertRows ]) => {
                setSessions( sessionRows );
                setAlerts( alertRows );
            } )
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

    const sessionsByDate = useMemo(() => {
        const map: Record<string, { sessions: DrivingSession[]; totalMs: number }> = {};
        groupedSessions.forEach((group) => {
            map[group.date] = {
                sessions: group.sessions,
                totalMs: group.totalMs,
            };
        });
        return map;
    }, [groupedSessions]);

    const alertsByDate = useMemo(() => {
        const map: Record<string, Alert[]> = {};
        alerts.forEach((alert) => {
            if (!alert.createdAt) return;
            const d = new Date(alert.createdAt);
            const dateStr = d.toLocaleDateString("en-GB", { day: "2-digit", month: "2-digit", year: "numeric" });
            if (!map[dateStr]) {
                map[dateStr] = [];
            }
            map[dateStr].push(alert);
        });
        return map;
    }, [alerts]);

    const daysOfWeek = language === "en" 
        ? ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        : ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

    const handlePrevMonth = () => {
        setCurrentDate((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
    };

    const handleNextMonth = () => {
        setCurrentDate((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
    };

    const monthLabel = useMemo(() => {
        const monthNamesEn = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ];
        const monthNamesVi = [
            "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
            "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
        ];
        const name = language === "en" ? monthNamesEn[currentDate.getMonth()] : monthNamesVi[currentDate.getMonth()];
        return `${name}, ${currentDate.getFullYear()}`;
    }, [currentDate, language]);

    const calendarCells = useMemo(() => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();

        const firstDayOfMonth = new Date(year, month, 1);
        let startDayOfWeek = firstDayOfMonth.getDay();
        startDayOfWeek = startDayOfWeek === 0 ? 6 : startDayOfWeek - 1;

        const totalDaysInMonth = new Date(year, month + 1, 0).getDate();

        const cells: Array<{ day: number | null; dateStr: string | null; isCurrentMonth: boolean }> = [];

        for (let i = 0; i < startDayOfWeek; i++) {
            cells.push({ day: null, dateStr: null, isCurrentMonth: false });
        }

        for (let day = 1; day <= totalDaysInMonth; day++) {
            const dateStr = `${String(day).padStart(2, "0")}/${String(month + 1).padStart(2, "0")}/${year}`;
            cells.push({ day, dateStr, isCurrentMonth: true });
        }

        return cells;
    }, [currentDate]);

    return (
        <>
            <DriverHeader />
            <div className="p-10 max-w-[1200px] space-y-8">
                <div className="flex justify-between items-end">
                    <div>
                        <span className="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-on-surface-variant block mb-2">
                            {t("sidebar.timekeeping")}
                        </span>
                        <h2 className="text-3xl font-black text-primary tracking-tight">{t("drivers.timekeepingHistory")}</h2>
                        <p className="text-secondary text-sm mt-1 font-medium">{t("drivers.timekeepingSubtitle")}</p>
                    </div>

                    <div className="flex gap-1 bg-surface-container rounded-lg p-0.5 border border-outline-variant/10">
                        <button
                            onClick={() => setViewMode("list")}
                            className={cn(
                                "p-1.5 rounded text-[10px] font-bold uppercase transition-all cursor-pointer flex items-center gap-1.5",
                                viewMode === "list" ? "bg-primary text-on-primary shadow-sm" : "text-secondary hover:text-primary"
                            )}
                            title={language === "en" ? "List View" : "Dạng danh sách"}
                        >
                            <LayoutList className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">{language === "en" ? "List" : "Danh sách"}</span>
                        </button>
                        <button
                            onClick={() => setViewMode("calendar")}
                            className={cn(
                                "p-1.5 rounded text-[10px] font-bold uppercase transition-all cursor-pointer flex items-center gap-1.5",
                                viewMode === "calendar" ? "bg-primary text-on-primary shadow-sm" : "text-secondary hover:text-primary"
                            )}
                            title={language === "en" ? "Calendar View" : "Dạng lịch"}
                        >
                            <Calendar className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">{language === "en" ? "Calendar" : "Lịch"}</span>
                        </button>
                    </div>
                </div>

                { loading ? (
                    <p className="text-secondary text-sm">{language === "en" ? "Loading sessions..." : "Đang tải ca làm việc..."}</p>
                ) : viewMode === "calendar" ? (
                    /* Calendar View */
                    <div className="bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/15 shadow-sm p-6 space-y-6 animate-in fade-in duration-300">
                        {/* Calendar Selector Header */}
                        <div className="flex items-center justify-between border-b border-surface-container-high pb-4">
                            <h3 className="text-base font-bold text-primary">{monthLabel}</h3>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={handlePrevMonth}
                                    className="p-1.5 rounded-lg border border-surface-container-high hover:bg-surface-container-low transition-colors cursor-pointer text-secondary hover:text-primary"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={handleNextMonth}
                                    className="p-1.5 rounded-lg border border-surface-container-high hover:bg-surface-container-low transition-colors cursor-pointer text-secondary hover:text-primary"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {/* Calendar Grid */}
                        <div className="grid grid-cols-7 gap-2">
                            {/* Day Headers */}
                            {daysOfWeek.map((day) => (
                                <div key={day} className="text-center text-[10px] font-bold uppercase tracking-wider text-secondary py-1 border-b border-surface-container-high mb-1">
                                    {day}
                                </div>
                            ))}

                            {/* Day Cells */}
                            {calendarCells.map((cell, idx) => {
                                if (!cell.isCurrentMonth || !cell.dateStr) {
                                    return (
                                        <div
                                            key={`empty-${idx}`}
                                            className="bg-surface-container-low/30 aspect-square rounded-lg border border-surface-container-high/50 opacity-20"
                                        />
                                    );
                                }

                                const dayData = sessionsByDate[cell.dateStr];
                                const dayAlerts = alertsByDate[cell.dateStr];
                                const hasSessions = !!dayData;
                                const hasAlerts = !!dayAlerts && dayAlerts.length > 0;

                                return (
                                    <div
                                        key={cell.dateStr}
                                        className={`aspect-square rounded-lg border p-2 flex flex-col justify-between transition-all relative ${
                                            hasSessions
                                                ? "bg-surface-container/60 border-primary/20 hover:border-primary/50"
                                                : "bg-surface-container-lowest border-surface-container-high hover:border-surface-container-highest"
                                        }`}
                                    >
                                        {/* Top Row: Day Number and Warning Icon */}
                                        <div className="flex items-start justify-between">
                                            <span className={`text-[11px] font-bold ${hasSessions ? "text-primary" : "text-secondary"}`}>
                                                {cell.day}
                                            </span>
                                            {hasAlerts && (
                                                <div 
                                                    className="bg-error/10 text-error p-0.5 rounded-full cursor-help" 
                                                    title={language === "en" ? `${dayAlerts.length} violation(s)` : `${dayAlerts.length} vi phạm`}
                                                >
                                                    <AlertTriangle className="w-3.5 h-3.5 animate-pulse" />
                                                </div>
                                            )}
                                        </div>

                                        {/* Bottom Row: Working Hours */}
                                        {hasSessions && (
                                            <div className="text-[10px] font-black text-emerald-600 bg-emerald-500/10 px-1.5 py-0.5 rounded self-start truncate max-w-full">
                                                {formatDuration(dayData.totalMs)}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ) : groupedSessions.length === 0 ? (
                    <div className="bg-surface-container-lowest p-8 rounded-xl ring-1 ring-outline-variant/15 text-center shadow-sm">
                        <Clock className="w-12 h-12 text-outline mx-auto mb-3" />
                        <p className="text-secondary font-medium">{t("drivers.noSessions")}</p>
                    </div>
                ) : (
                    /* List View */
                    <div className="bg-surface-container-lowest rounded-xl ring-1 ring-outline-variant/15 shadow-sm overflow-hidden flex flex-col divide-y divide-surface-container-high animate-in fade-in duration-300">
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
                                                <span className="text-sm font-bold text-secondary uppercase tracking-widest mb-1">
                                                    {language === "en" ? "Date" : "Ngày"}
                                                </span>
                                                <span className="text-xl font-black text-primary">{ group.date }</span>
                                            </div>
                                            <div className="h-10 w-px bg-surface-container-highest mx-2 hidden sm:block" />
                                            <div className="flex flex-col hidden sm:flex">
                                                <span className="text-xs font-bold text-secondary uppercase tracking-widest mb-1">
                                                    {language === "en" ? "Check-ins" : "Lượt chạy"}
                                                </span>
                                                <span className="text-lg font-semibold text-on-surface">
                                                    { group.sessions.length } {language === "en" ? "sessions" : "ca làm việc"}
                                                </span>
                                            </div>
                                            <div className="h-10 w-px bg-surface-container-highest mx-2 hidden md:block" />
                                            <div className="flex flex-col hidden md:flex">
                                                <span className="text-xs font-bold text-secondary uppercase tracking-widest mb-1">
                                                    {language === "en" ? "Total Time" : "Tổng thời gian"}
                                                </span>
                                                <span className="text-lg font-semibold text-emerald-600">{ formatDuration( group.totalMs ) }</span>
                                            </div>
                                        </div>
                                        <button className="p-2 hover:bg-surface-container-high rounded-full transition-colors cursor-pointer">
                                            { isExpanded ? <ChevronUp className="w-5 h-5 text-secondary" /> : <ChevronDown className="w-5 h-5 text-secondary" /> }
                                        </button>
                                    </div>

                                    { isExpanded && (
                                        <div className="bg-surface-container-low/30 border-t border-surface-container-high p-4 flex flex-col gap-2 animate-in fade-in duration-200">
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
                                                                { session.ended_at ? new Date( session.ended_at ).toLocaleTimeString( 'en-GB', { hour: '2-digit', minute: '2-digit' } ) : (language === "en" ? "Active" : "Đang chạy") }
                                                            </span>
                                                            <span className="font-mono text-[10px] text-secondary mt-1">ID: { session.id }</span>
                                                        </div>
                                                    </div>
                                                    { session.status === "ACTIVE" ? (
                                                        <span className="text-[10px] font-black text-emerald-600 bg-emerald-500/20 px-2 py-1 rounded tracking-widest uppercase animate-pulse">
                                                            {language === "en" ? "ACTIVE" : "ĐANG CHẠY"}
                                                        </span>
                                                    ) : (
                                                        <span className="text-[10px] font-black text-secondary bg-surface-container-highest px-2 py-1 rounded tracking-widest uppercase">
                                                            {language === "en" ? "COMPLETED" : "HOÀN THÀNH"}
                                                        </span>
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
